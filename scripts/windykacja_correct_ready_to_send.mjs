import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
dotenv.config();

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

// Parser z lib/fiscal-sync-parser.ts
function parseFiscalSync(comment) {
  if (!comment) return null;

  const fiscalSyncRegex = /\[FISCAL_SYNC\]([\s\S]*?)\[\/FISCAL_SYNC\]/;
  const match = comment.match(fiscalSyncRegex);

  if (!match) return null;

  const content = match[1].trim();
  const lines = content.split('\n');
  const data = {};

  for (const line of lines) {
    const [key, value] = line.split('=').map(s => s.trim());
    if (!key || !value) continue;

    if (key === 'UPDATED' || key === 'HASH') {
      data[key] = value === 'NULL' ? null : value;
    } else if (key.endsWith('_DATE')) {
      data[key] = value === 'NULL' ? null : value;
    } else {
      data[key] = value === 'TRUE';
    }
  }

  return data;
}

console.log('📧 KLIENCI WINDYKACJA - FAKTURY GOTOWE DO WYSYŁKI (2025-12-05)\n');
console.log('='.repeat(100));

// Get all windykacja clients
const { data: windykacjaClients } = await supabase
  .from('clients')
  .select('id, name, email')
  .ilike('note', '%[WINDYKACJA]true%')
  .order('name');

console.log(`\nZnaleziono ${windykacjaClients.length} klientów z flagą windykacja\n`);

let clientsWithUnsent = [];

for (const client of windykacjaClients) {
  // Get all invoices for this client
  let allInvoices = [];
  let offset = 0;
  const limit = 1000;

  while (true) {
    const { data } = await supabase
      .from('invoices')
      .select('id, number, issue_date, payment_to, total, paid, outstanding, status, kind, internal_note, sent_time')
      .eq('client_id', client.id)
      .order('issue_date', { ascending: false })
      .range(offset, offset + limit - 1);

    if (!data || data.length === 0) break;
    allInvoices.push(...data);
    if (data.length < limit) break;
    offset += limit;
  }

  // Filter invoices that qualify for sending
  const qualifyingInvoices = allInvoices.filter(inv => {
    // Skip canceled invoices
    if (inv.kind === 'canceled') return false;

    // Skip corrective invoices (FK prefix)
    if (inv.number && inv.number.startsWith('FK')) return false;

    // Skip paid invoices
    if (inv.status === 'paid') return false;

    // Must have outstanding balance
    const outstanding = inv.outstanding || (inv.total - (inv.paid || 0));
    if (outstanding <= 0) return false;

    // Parse FISCAL_SYNC properly
    const fiscalSync = parseFiscalSync(inv.internal_note);

    // Skip if STOP is enabled
    if (fiscalSync && fiscalSync.STOP === true) return false;

    // Check email status
    const hasEmail1 = fiscalSync && fiscalSync.EMAIL_1 === true;
    const hasEmail2 = fiscalSync && fiscalSync.EMAIL_2 === true;
    const hasEmail3 = fiscalSync && fiscalSync.EMAIL_3 === true;

    // If no emails sent at all - definitely qualifies
    if (!hasEmail1 && !hasEmail2 && !hasEmail3) {
      return true;
    }

    // If EMAIL_1 sent but not EMAIL_2 - check if enough time passed (7+ days)
    if (hasEmail1 && !hasEmail2 && fiscalSync.EMAIL_1_DATE) {
      const sentDate = new Date(fiscalSync.EMAIL_1_DATE);
      const daysSinceSent = Math.floor((Date.now() - sentDate.getTime()) / (1000 * 60 * 60 * 24));
      if (daysSinceSent >= 7) return true;
    }

    // If EMAIL_2 sent but not EMAIL_3 - check if enough time passed (7+ days)
    if (hasEmail2 && !hasEmail3 && fiscalSync.EMAIL_2_DATE) {
      const sentDate = new Date(fiscalSync.EMAIL_2_DATE);
      const daysSinceSent = Math.floor((Date.now() - sentDate.getTime()) / (1000 * 60 * 60 * 24));
      if (daysSinceSent >= 7) return true;
    }

    return false;
  });

  if (qualifyingInvoices.length > 0) {
    clientsWithUnsent.push({
      client,
      invoices: qualifyingInvoices
    });
  }
}

console.log(`\n🎯 KLIENCI Z FAKTURAMI DO WYSYŁKI: ${clientsWithUnsent.length}\n`);
console.log('='.repeat(100));

let totalInvoicesToSend = 0;
let totalAmount = 0;

clientsWithUnsent.forEach((item, idx) => {
  const { client, invoices } = item;
  const clientTotal = invoices.reduce((sum, inv) => sum + (inv.outstanding || 0), 0);
  totalAmount += clientTotal;
  totalInvoicesToSend += invoices.length;

  console.log(`\n${idx + 1}. ${client.name} (ID: ${client.id})`);
  console.log(`   Email: ${client.email || 'BRAK'}`);
  console.log(`   Faktury do wysłania: ${invoices.length} | Kwota: ${clientTotal.toFixed(2)} PLN`);
  console.log('-'.repeat(100));

  invoices.forEach((inv, i) => {
    const fiscalSync = parseFiscalSync(inv.internal_note);
    const hasEmail1 = fiscalSync && fiscalSync.EMAIL_1 === true;
    const hasEmail2 = fiscalSync && fiscalSync.EMAIL_2 === true;
    const hasEmail3 = fiscalSync && fiscalSync.EMAIL_3 === true;

    let emailStatus = 'NIE WYSŁANO';
    if (hasEmail3) emailStatus = 'EMAIL_3 ✅';
    else if (hasEmail2) emailStatus = 'EMAIL_2 ✅';
    else if (hasEmail1) emailStatus = 'EMAIL_1 ✅';

    let reason = '';
    if (!hasEmail1 && !hasEmail2 && !hasEmail3) {
      reason = '→ Gotowe do EMAIL_1 (pierwsze przypomnienie)';
    } else if (hasEmail1 && !hasEmail2 && fiscalSync.EMAIL_1_DATE) {
      const sentDate = new Date(fiscalSync.EMAIL_1_DATE);
      const daysSinceSent = Math.floor((Date.now() - sentDate.getTime()) / (1000 * 60 * 60 * 24));
      reason = `→ Gotowe do EMAIL_2 (${daysSinceSent} dni od EMAIL_1, wysłano: ${fiscalSync.EMAIL_1_DATE.substring(0, 10)})`;
    } else if (hasEmail2 && !hasEmail3 && fiscalSync.EMAIL_2_DATE) {
      const sentDate = new Date(fiscalSync.EMAIL_2_DATE);
      const daysSinceSent = Math.floor((Date.now() - sentDate.getTime()) / (1000 * 60 * 60 * 24));
      reason = `→ Gotowe do EMAIL_3 (${daysSinceSent} dni od EMAIL_2, wysłano: ${fiscalSync.EMAIL_2_DATE.substring(0, 10)})`;
    }

    console.log(`   ${i + 1}. ${inv.number} | ${inv.issue_date} | ${inv.outstanding.toFixed(2)} PLN`);
    console.log(`      Status: ${emailStatus}`);
    console.log(`      ${reason}`);
  });
});

console.log('\n' + '='.repeat(100));
console.log('\n📊 PODSUMOWANIE:');
console.log(`   Klientów z fakturami do wysłania: ${clientsWithUnsent.length}`);
console.log(`   Faktur do wysłania: ${totalInvoicesToSend}`);
console.log(`   Łączna kwota: ${totalAmount.toFixed(2)} PLN`);
console.log('\n' + '='.repeat(100));
