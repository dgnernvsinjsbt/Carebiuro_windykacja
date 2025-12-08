import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
dotenv.config();

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

console.log('🔍 ANALIZA DUPLIKATÓW FAKTUR\n');
console.log('='.repeat(80));

// Znajdź faktury z tym samym numerem
const { data: allInvoices, error } = await supabase
  .from('invoices')
  .select('id, number, client_id, total, status, issue_date, sent_time, created_at')
  .order('number');

if (error) {
  console.error('Błąd:', error);
  process.exit(1);
}

// Grupuj po numerze
const byNumber = new Map();
for (const inv of allInvoices) {
  if (!inv.number) continue;

  if (!byNumber.has(inv.number)) {
    byNumber.set(inv.number, []);
  }
  byNumber.get(inv.number).push(inv);
}

// Znajdź duplikaty (więcej niż 1 faktura z tym samym numerem)
const duplicates = Array.from(byNumber.entries())
  .filter(([number, invoices]) => invoices.length > 1)
  .sort((a, b) => b[1].length - a[1].length);

const totalDuplicateInvoices = duplicates.reduce((sum, pair) => sum + pair[1].length, 0);

console.log(`\n📊 STATYSTYKI:`);
console.log(`Wszystkie faktury: ${allInvoices.length}`);
console.log(`Unikalne numery: ${byNumber.size}`);
console.log(`Duplikaty: ${duplicates.length} numerów (${totalDuplicateInvoices} faktur)\n`);

// Analizuj duplikaty
let windykacjaRelated = 0;
let totalDuplicates = 0;

console.log('\n🔎 TOP 20 DUPLIKATY:\n');

for (const [number, invoices] of duplicates.slice(0, 20)) {
  totalDuplicates += invoices.length - 1; // -1 bo jedna jest oryginalna

  console.log(`📄 ${number} (${invoices.length}x)`);

  // Sprawdź czy któryś z klientów ma windykacja
  const clientIds = [...new Set(invoices.map(i => i.client_id))];

  for (const inv of invoices) {
    const sentStatus = inv.sent_time ? '✅' : '❌';
    const createdDate = new Date(inv.created_at).toISOString().split('T')[0];
    console.log(`   ${sentStatus} ID:${inv.id} | ${inv.issue_date} | ${inv.total} PLN | Created: ${createdDate}`);
  }

  // Check if windykacja
  const { data: clients } = await supabase
    .from('clients')
    .select('id, name, note')
    .in('id', clientIds);

  const hasWindykacja = clients?.some(c => c.note && c.note.includes('[WINDYKACJA]true'));
  if (hasWindykacja) {
    windykacjaRelated++;
    const windykacjaClient = clients.find(c => c.note?.includes('[WINDYKACJA]true'));
    console.log(`   ⚠️  WINDYKACJA: ${windykacjaClient?.name}`);
  }

  console.log('');
}

console.log('\n🎯 PODSUMOWANIE:');
console.log('='.repeat(80));
console.log(`Duplikaty ogółem: ${totalDuplicates} nadmiarowych faktur`);
console.log(`Duplikaty z windykacja: ${windykacjaRelated}`);

// Sprawdź invoice_hash_registry
const { data: registry, error: regError } = await supabase
  .from('invoice_hash_registry')
  .select('*')
  .limit(10);

if (registry && registry.length > 0) {
  console.log(`\n✅ invoice_hash_registry istnieje (${registry.length} przykładowych wpisów)`);
} else {
  console.log(`\n❌ invoice_hash_registry PUSTA lub nie istnieje!`);
}

console.log('\n');
