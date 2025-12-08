import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
dotenv.config();

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

console.log('🔍 ANALIZA DUPLIKATÓW - KLIENCI WINDYKACJA\n');
console.log('='.repeat(80));

// 1. Pobierz klientów windykacja
const { data: windykacjaClients } = await supabase
  .from('clients')
  .select('id, name')
  .ilike('note', '%[WINDYKACJA]true%');

console.log(`Klienci windykacja: ${windykacjaClients.length}\n`);

const clientIds = windykacjaClients.map(c => c.id);

// 2. Pobierz WSZYSTKIE faktury dla tych klientów (z paginacją)
let allInvoices = [];
let offset = 0;
const pageSize = 1000;
let hasMore = true;

while (hasMore) {
  const { data: invoicePage, error } = await supabase
    .from('invoices')
    .select('id, number, client_id, total, status, issue_date, sent_time, created_at')
    .in('client_id', clientIds)
    .range(offset, offset + pageSize - 1)
    .order('id');

  if (error || !invoicePage || invoicePage.length === 0) {
    hasMore = false;
  } else {
    allInvoices.push(...invoicePage);
    offset += pageSize;
    hasMore = invoicePage.length === pageSize;
  }
}

console.log(`Faktury windykacja: ${allInvoices.length}\n`);

// 3. Grupuj po numerze
const byNumber = new Map();
for (const inv of allInvoices) {
  if (!inv.number) continue;

  if (!byNumber.has(inv.number)) {
    byNumber.set(inv.number, []);
  }
  byNumber.get(inv.number).push(inv);
}

// 4. Znajdź duplikaty
const duplicates = Array.from(byNumber.entries())
  .filter(([number, invoices]) => invoices.length > 1)
  .sort((a, b) => b[1].length - a[1].length);

console.log(`\n📊 DUPLIKATY:\n`);
console.log(`Znaleziono: ${duplicates.length} numerów z duplikatami\n`);

const clientMap = new Map(windykacjaClients.map(c => [c.id, c.name]));

for (const [number, invoices] of duplicates) {
  console.log(`📄 ${number} (${invoices.length}x) - ${clientMap.get(invoices[0].client_id)}`);

  for (const inv of invoices) {
    const sentStatus = inv.sent_time ? '✅ Wysłana' : '❌ NIE wysłana';
    const createdDate = new Date(inv.created_at).toISOString().split('T')[0];
    const createdTime = new Date(inv.created_at).toISOString().split('T')[1].split('.')[0];
    console.log(`   ${sentStatus} | ID:${inv.id} | ${inv.total} PLN | Created: ${createdDate} ${createdTime}`);
  }
  console.log('');
}

console.log(`\n🎯 PODSUMOWANIE:`);
console.log('='.repeat(80));
console.log(`Duplikaty: ${duplicates.length} numerów faktur`);
console.log(`Nadmiarowe faktury: ${duplicates.reduce((sum, pair) => sum + pair[1].length - 1, 0)}`);

console.log('\n');
