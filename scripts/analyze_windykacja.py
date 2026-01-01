#!/usr/bin/env python3
"""
Analyze windykacja qualifying invoices from Supabase dump
"""
import re
from datetime import datetime, timedelta
from collections import defaultdict

# Read the dump file
with open('/tmp/windykacja_dump.sql', 'r') as f:
    content = f.read()

# Parse clients
clients_section = re.search(r'-- Data for Name: clients.*?(?=-- Data for Name:|\Z)', content, re.DOTALL)
clients_data = {}
if clients_section:
    # Extract INSERT statements
    insert_pattern = r"INSERT INTO \"public\".\"clients\".*?VALUES\s*\n(.*?)(?=\nINSERT INTO|\n--|\Z)"
    for match in re.finditer(insert_pattern, clients_section.group(0), re.DOTALL):
        rows = match.group(1)
        # Parse each row - format: (id, name, email, phone, total_unpaid, updated_at, note, ...)
        row_pattern = r"\((\d+),\s*'([^']*)',\s*(?:'([^']*)'|NULL),\s*(?:'([^']*)'|NULL),\s*(\d+),\s*'([^']*)',\s*(?:'([^']*)'|NULL)"
        for row in re.finditer(row_pattern, rows):
            client_id = int(row.group(1))
            name = row.group(2)
            note = row.group(7) if row.group(7) else ''
            windykacja = '[WINDYKACJA]true[/WINDYKACJA]' in note
            clients_data[client_id] = {
                'name': name,
                'windykacja': windykacja,
                'note': note
            }

print(f"Parsed {len(clients_data)} clients")
windykacja_clients = {k: v for k, v in clients_data.items() if v['windykacja']}
print(f"Clients with windykacja=true: {len(windykacja_clients)}")
print()

# Parse invoices
invoices_section = re.search(r'-- Data for Name: invoices.*?(?=-- Data for Name:|\Z)', content, re.DOTALL)
invoices_data = []

if invoices_section:
    # Find all INSERT statements and their column order
    lines = invoices_section.group(0).split('\n')
    in_insert = False
    current_columns = []

    for line in lines:
        if 'INSERT INTO "public"."invoices"' in line:
            # Parse column names
            cols_match = re.search(r'\(([^)]+)\)', line)
            if cols_match:
                current_columns = [c.strip().strip('"') for c in cols_match.group(1).split(',')]
            in_insert = True
            continue

        if in_insert and line.strip().startswith('('):
            # Parse values - this is complex due to escaping
            # Simplified: just look for key fields
            pass

# Alternative approach: use a more targeted extraction
print("Extracting invoice data...")

# Find the invoices INSERT block
invoices_match = re.search(r'INSERT INTO "public"."invoices" \(([^)]+)\) VALUES\s*\n(.+?)(?=\n\n|\n--)', content, re.DOTALL)
if invoices_match:
    columns_str = invoices_match.group(1)
    columns = [c.strip().strip('"') for c in columns_str.split(',')]
    print(f"Invoice columns: {len(columns)} columns")

    # Build column index
    col_idx = {name: i for i, name in enumerate(columns)}

    values_str = invoices_match.group(2)

    # Parse each row
    # Rows are separated by ),\n\t(
    rows = re.split(r'\),\s*\n\s*\(', values_str)

    for i, row in enumerate(rows):
        # Clean up first/last rows
        row = row.strip()
        if row.startswith('('):
            row = row[1:]
        if row.endswith(');'):
            row = row[:-2]
        elif row.endswith(','):
            row = row[:-1]

        # Parse values - handle quoted strings and NULLs
        values = []
        current = ''
        in_quote = False
        escape_next = False

        for char in row + ',':
            if escape_next:
                current += char
                escape_next = False
                continue
            if char == '\\' or (char == "'" and in_quote and len(current) > 0 and current[-1] == "'"):
                escape_next = True
                current += char
                continue
            if char == "'" and not in_quote:
                in_quote = True
                continue
            if char == "'" and in_quote:
                in_quote = False
                continue
            if char == ',' and not in_quote:
                val = current.strip()
                if val == 'NULL':
                    val = None
                values.append(val)
                current = ''
                continue
            current += char

        if len(values) >= len(columns):
            try:
                invoice = {columns[j]: values[j] for j in range(len(columns))}
                invoices_data.append(invoice)
            except:
                pass

print(f"Parsed {len(invoices_data)} invoices")

# Now analyze
today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
three_days_ago = today - timedelta(days=3)
thirty_days_ago = today - timedelta(days=30)
fourteen_days_ago = today - timedelta(days=14)

def parse_fiscal_sync(internal_note):
    if not internal_note:
        return {}

    result = {}
    match = re.search(r'\[FISCAL_SYNC\](.*?)\[/FISCAL_SYNC\]', internal_note, re.DOTALL)
    if not match:
        return result

    content = match.group(1)
    for line in content.strip().split('\n'):
        if '=' in line:
            key, val = line.split('=', 1)
            key = key.strip()
            val = val.strip()
            if val == 'TRUE':
                result[key] = True
            elif val == 'FALSE':
                result[key] = False
            elif val == 'NULL':
                result[key] = None
            else:
                result[key] = val
    return result

def parse_date(date_str):
    if not date_str:
        return None
    try:
        # Try different formats
        for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
            try:
                return datetime.strptime(date_str[:19], fmt)
            except:
                continue
    except:
        pass
    return None

# Categories
qualifying_e1s1_initial = []
qualifying_e1s1_overdue = []
qualifying_e2s2 = []
qualifying_e3s3 = []

for inv in invoices_data:
    # Skip paid/canceled/vat
    status = inv.get('status', '')
    kind = inv.get('kind', '')
    if status == 'paid' or kind == 'canceled' or kind == 'vat':
        continue

    # Check balance
    try:
        total = float(inv.get('total', 0) or 0)
        paid = float(inv.get('paid', 0) or 0)
        balance = total - paid
    except:
        balance = 0

    if balance <= 0:
        continue

    # Parse dates
    issue_date = parse_date(inv.get('issue_date'))
    if not issue_date:
        continue

    # Get client info
    client_id = inv.get('client_id')
    try:
        client_id = int(client_id)
    except:
        client_id = None

    client = clients_data.get(client_id, {})
    client_windykacja = client.get('windykacja', False)

    # Parse fiscal sync
    internal_note = inv.get('internal_note', '') or ''
    fiscal_sync = parse_fiscal_sync(internal_note)

    stopped = fiscal_sync.get('STOP', False)

    # E1 sent check
    e1_sent = fiscal_sync.get('EMAIL_1', False) or inv.get('email_status') == 'sent'
    s1_sent = fiscal_sync.get('SMS_1', False)
    e2_sent = fiscal_sync.get('EMAIL_2', False)
    s2_sent = fiscal_sync.get('SMS_2', False)
    e3_sent = fiscal_sync.get('EMAIL_3', False)
    s3_sent = fiscal_sync.get('SMS_3', False)

    # Get dates
    e1_date = None
    if e1_sent:
        if inv.get('email_status') == 'sent' and inv.get('sent_time'):
            e1_date = parse_date(inv.get('sent_time'))
        elif fiscal_sync.get('EMAIL_1_DATE'):
            e1_date = parse_date(fiscal_sync.get('EMAIL_1_DATE'))

    s1_date = parse_date(fiscal_sync.get('SMS_1_DATE')) if s1_sent else None
    e2_date = parse_date(fiscal_sync.get('EMAIL_2_DATE')) if e2_sent else None
    s2_date = parse_date(fiscal_sync.get('SMS_2_DATE')) if s2_sent else None

    invoice_info = {
        'id': inv.get('id'),
        'number': inv.get('number'),
        'buyer': inv.get('buyer_name', '')[:40] if inv.get('buyer_name') else '',
        'balance': f"{balance:.2f}",
        'currency': inv.get('currency', 'EUR'),
        'issue_date': inv.get('issue_date', '')[:10] if inv.get('issue_date') else '',
        'payment_to': inv.get('payment_to', '')[:10] if inv.get('payment_to') else '',
        'client_windykacja': client_windykacja,
        'stopped': stopped,
        'e1_sent': e1_sent,
        's1_sent': s1_sent,
        'e2_sent': e2_sent,
        's2_sent': s2_sent,
        'e3_sent': e3_sent,
        's3_sent': s3_sent,
        'e1_date': e1_date.strftime('%Y-%m-%d') if e1_date else None,
        's1_date': s1_date.strftime('%Y-%m-%d') if s1_date else None,
    }

    # 1. E1/S1 Initial (new invoices within 3 days)
    if issue_date >= three_days_ago:
        if not e1_sent or not s1_sent:
            needs = []
            if not e1_sent:
                needs.append('E1')
            if not s1_sent:
                needs.append('S1')
            qualifying_e1s1_initial.append({
                **invoice_info,
                'needs': ' '.join(needs),
                'reason': 'Nowa faktura (< 3 dni)'
            })

    # 2. E1/S1 Overdue (30+ days, windykacja enabled)
    if client_windykacja and not stopped and issue_date <= thirty_days_ago:
        if not e1_sent or not s1_sent:
            needs = []
            if not e1_sent:
                needs.append('E1')
            if not s1_sent:
                needs.append('S1')
            qualifying_e1s1_overdue.append({
                **invoice_info,
                'needs': ' '.join(needs),
                'reason': 'Przeterminowana > 30 dni'
            })

    # 3. E2/S2 (14 days after E1/S1)
    if client_windykacja and not stopped:
        needs_e2 = e1_sent and not e2_sent and e1_date and e1_date <= fourteen_days_ago
        needs_s2 = s1_sent and not s2_sent and s1_date and s1_date <= fourteen_days_ago

        if needs_e2 or needs_s2:
            needs = []
            if needs_e2:
                needs.append('E2')
            if needs_s2:
                needs.append('S2')

            e1_days = (today - e1_date).days if e1_date else 0
            s1_days = (today - s1_date).days if s1_date else 0

            qualifying_e2s2.append({
                **invoice_info,
                'needs': ' '.join(needs),
                'reason': f'E1: {e1_days}d ago, S1: {s1_days}d ago'
            })

    # 4. E3/S3 (14 days after E2/S2)
    if client_windykacja and not stopped:
        needs_e3 = e2_sent and not e3_sent and e2_date and e2_date <= fourteen_days_ago
        needs_s3 = s2_sent and not s3_sent and s2_date and s2_date <= fourteen_days_ago

        if needs_e3 or needs_s3:
            needs = []
            if needs_e3:
                needs.append('E3')
            if needs_s3:
                needs.append('S3')

            e2_days = (today - e2_date).days if e2_date else 0
            s2_days = (today - s2_date).days if s2_date else 0

            qualifying_e3s3.append({
                **invoice_info,
                'needs': ' '.join(needs),
                'reason': f'E2: {e2_days}d ago, S2: {s2_days}d ago'
            })

# Print results
print('=' * 100)
print('ANALIZA WINDYKACJI - Kwalifikujące się faktury')
print(f'Data analizy: {today.strftime("%Y-%m-%d")}')
print('=' * 100)
print()

print('=' * 100)
print('1. E1/S1 INITIAL - Nowe faktury (< 3 dni)')
print('   (Informacyjne - wysyłane bez względu na WINDYKACJA)')
print('=' * 100)
if not qualifying_e1s1_initial:
    print('   Brak kwalifikujących się faktur')
else:
    for inv in qualifying_e1s1_initial[:20]:
        print(f"   {inv['number']} | {inv['buyer'][:30]} | {inv['balance']} {inv['currency']} | Issue: {inv['issue_date']} | Needs: {inv['needs']}")
    if len(qualifying_e1s1_initial) > 20:
        print(f"   ... i {len(qualifying_e1s1_initial) - 20} więcej")
print(f"   RAZEM: {len(qualifying_e1s1_initial)} faktur")
print()

print('=' * 100)
print('2. E1/S1 OVERDUE - Przeterminowane > 30 dni (z włączonym WINDYKACJA)')
print('=' * 100)
if not qualifying_e1s1_overdue:
    print('   Brak kwalifikujących się faktur')
else:
    for inv in qualifying_e1s1_overdue[:20]:
        print(f"   {inv['number']} | {inv['buyer'][:30]} | {inv['balance']} {inv['currency']} | Issue: {inv['issue_date']} | Needs: {inv['needs']}")
    if len(qualifying_e1s1_overdue) > 20:
        print(f"   ... i {len(qualifying_e1s1_overdue) - 20} więcej")
print(f"   RAZEM: {len(qualifying_e1s1_overdue)} faktur")
print()

print('=' * 100)
print('3. E2/S2 - 14 dni po E1/S1 (z włączonym WINDYKACJA)')
print('=' * 100)
if not qualifying_e2s2:
    print('   Brak kwalifikujących się faktur')
else:
    for inv in qualifying_e2s2[:20]:
        print(f"   {inv['number']} | {inv['buyer'][:30]} | {inv['balance']} {inv['currency']} | {inv['reason']} | Needs: {inv['needs']}")
    if len(qualifying_e2s2) > 20:
        print(f"   ... i {len(qualifying_e2s2) - 20} więcej")
print(f"   RAZEM: {len(qualifying_e2s2)} faktur")
print()

print('=' * 100)
print('4. E3/S3 - 14 dni po E2/S2 (z włączonym WINDYKACJA)')
print('=' * 100)
if not qualifying_e3s3:
    print('   Brak kwalifikujących się faktur')
else:
    for inv in qualifying_e3s3[:20]:
        print(f"   {inv['number']} | {inv['buyer'][:30]} | {inv['balance']} {inv['currency']} | {inv['reason']} | Needs: {inv['needs']}")
    if len(qualifying_e3s3) > 20:
        print(f"   ... i {len(qualifying_e3s3) - 20} więcej")
print(f"   RAZEM: {len(qualifying_e3s3)} faktur")
print()

print('=' * 100)
print('PODSUMOWANIE')
print('=' * 100)
print(f"   E1/S1 Initial (nowe):           {len(qualifying_e1s1_initial)} faktur")
print(f"   E1/S1 Overdue (30+ dni):        {len(qualifying_e1s1_overdue)} faktur")
print(f"   E2/S2 (14 dni po E1/S1):        {len(qualifying_e2s2)} faktur")
print(f"   E3/S3 (14 dni po E2/S2):        {len(qualifying_e3s3)} faktur")
print()
total = len(qualifying_e1s1_initial) + len(qualifying_e1s1_overdue) + len(qualifying_e2s2) + len(qualifying_e3s3)
print(f"   ŁĄCZNIE DO WYSŁANIA:            {total} faktur")
print()

# Show clients with windykacja
print('=' * 100)
print('KLIENCI Z WŁĄCZONĄ WINDYKACJĄ')
print('=' * 100)
for cid, cdata in sorted(windykacja_clients.items(), key=lambda x: x[1]['name']):
    print(f"   {cid}: {cdata['name']}")
print(f"   RAZEM: {len(windykacja_clients)} klientów")
