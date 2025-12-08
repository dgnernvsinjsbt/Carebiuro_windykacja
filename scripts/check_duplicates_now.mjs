import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
dotenv.config();

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

console.log('Checking for duplicate invoice numbers in Supabase RIGHT NOW...\n');

// Get all windykacja clients
const { data: windykacjaClients } = await supabase
  .from('clients')
  .select('id')
  .ilike('note', '%[WINDYKACJA]true%');

const clientIds = windykacjaClients.map(c => c.id);
console.log(`Found ${clientIds.length} windykacja clients`);

// Get ALL invoices for these clients (with pagination)
let allInvoices = [];
let offset = 0;
const limit = 1000;

while (true) {
  const { data, error } = await supabase
    .from('invoices')
    .select('id, number, issue_date, created_at, client_id, sent_time, internal_note')
    .in('client_id', clientIds)
    .order('id')
    .range(offset, offset + limit - 1);

  if (error) {
    console.error('Error:', error);
    break;
  }

  if (!data || data.length === 0) break;

  allInvoices.push(...data);
  console.log(`Fetched ${data.length} invoices (offset ${offset})...`);

  if (data.length < limit) break;
  offset += limit;
}

console.log(`\nTotal invoices: ${allInvoices.length}`);

// Check for duplicates
const numberCounts = {};
allInvoices.forEach(inv => {
  if (!inv.number) return;
  numberCounts[inv.number] = (numberCounts[inv.number] || 0) + 1;
});

const duplicates = Object.entries(numberCounts).filter(([num, count]) => count > 1);

console.log(`\n🔍 DUPLICATES FOUND: ${duplicates.length}\n`);

if (duplicates.length > 0) {
  console.log('Details:');
  for (const [dupNumber, count] of duplicates.slice(0, 10)) {
    const dups = allInvoices.filter(inv => inv.number === dupNumber);
    console.log(`\n=== ${dupNumber} (x${count}) ===`);
    dups.forEach(d => {
      console.log(`  ID: ${d.id}, Issue: ${d.issue_date}, Created: ${d.created_at}, Sent: ${d.sent_time}`);
    });
  }
} else {
  console.log('✅ NO DUPLICATES - All invoice numbers are unique!');
}
