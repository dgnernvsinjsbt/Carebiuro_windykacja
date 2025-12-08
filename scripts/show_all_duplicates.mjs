import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
dotenv.config();

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

console.log('Fetching ALL duplicate invoices for windykacja clients...\n');

// Get all windykacja clients
const { data: windykacjaClients } = await supabase
  .from('clients')
  .select('id, name')
  .ilike('note', '%[WINDYKACJA]true%');

const clientIds = windykacjaClients.map(c => c.id);
const clientMap = new Map(windykacjaClients.map(c => [c.id, c.name]));

console.log(`Found ${clientIds.length} windykacja clients\n`);

// Get ALL invoices for these clients (with pagination)
let allInvoices = [];
let offset = 0;
const limit = 1000;

while (true) {
  const { data, error } = await supabase
    .from('invoices')
    .select('id, number, issue_date, created_at, client_id, sent_time, status, total, outstanding')
    .in('client_id', clientIds)
    .order('id')
    .range(offset, offset + limit - 1);

  if (error) {
    console.error('Error:', error);
    break;
  }

  if (!data || data.length === 0) break;
  allInvoices.push(...data);

  if (data.length < limit) break;
  offset += limit;
}

console.log(`Total invoices: ${allInvoices.length}\n`);

// Group by invoice number
const numberGroups = {};
allInvoices.forEach(inv => {
  if (!inv.number) return;
  if (!numberGroups[inv.number]) {
    numberGroups[inv.number] = [];
  }
  numberGroups[inv.number].push(inv);
});

// Find duplicates
const duplicates = Object.entries(numberGroups)
  .filter(([num, invoices]) => invoices.length > 1)
  .sort((a, b) => a[0].localeCompare(b[0]));

console.log(`🔍 FOUND ${duplicates.length} DUPLICATE INVOICE NUMBERS\n`);
console.log('='.repeat(120));

duplicates.forEach(([invoiceNumber, invoices], idx) => {
  console.log(`\n${idx + 1}. ${invoiceNumber} (${invoices.length} copies)`);
  console.log('-'.repeat(120));

  invoices.forEach((inv, i) => {
    const clientName = clientMap.get(inv.client_id) || 'Unknown';
    const shortName = clientName.length > 40 ? clientName.substring(0, 40) + '...' : clientName;

    console.log(`   ${i === 0 ? 'A' : 'B'}. ID: ${inv.id}`);
    console.log(`      Client: ${shortName} (${inv.client_id})`);
    console.log(`      Created: ${inv.created_at} | Issue: ${inv.issue_date}`);
    console.log(`      Status: ${inv.status} | Sent: ${inv.sent_time || 'NOT SENT'}`);
    console.log(`      Total: ${inv.total} PLN | Outstanding: ${inv.outstanding} PLN`);
  });
});

console.log('\n' + '='.repeat(120));
console.log(`\nSUMMARY: ${duplicates.length} duplicate invoice numbers found`);
