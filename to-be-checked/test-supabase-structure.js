// Test script to check Supabase structure for client 211779362
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

async function checkStructure() {
  const clientId = 211779362;

  console.log('=== Sprawdzanie struktury w Supabase ===\n');

  // Pobierz klienta
  const { data: client } = await supabase
    .from('clients')
    .select('id, name, note')
    .eq('id', clientId)
    .single();

  console.log('KLIENT:', client.id, '-', client.name);
  console.log('Note:', client.note);
  console.log('');

  // Pobierz faktury
  const { data: invoices, error: invError } = await supabase
    .from('invoices')
    .select('id, number, total, paid, list_polecony, list_polecony_sent_date, list_polecony_ignored, list_polecony_ignored_date')
    .eq('client_id', clientId);

  if (invError) {
    console.error('Error fetching invoices:', invError);
    return;
  }

  console.log('FAKTURY (', invoices?.length || 0, '):\n');

  invoices.forEach(inv => {
    const balance = (inv.total || 0) - (inv.paid || 0);
    console.log(`Invoice ${inv.id} (${inv.number}):`);
    console.log(`  total: €${inv.total}`);
    console.log(`  paid: €${inv.paid}`);
    console.log(`  balance (outstanding): €${balance.toFixed(2)}`);
    console.log(`  list_polecony: ${inv.list_polecony}`);
    console.log(`  list_polecony_sent_date: ${inv.list_polecony_sent_date}`);
    console.log(`  list_polecony_ignored: ${inv.list_polecony_ignored}`);
    console.log(`  list_polecony_ignored_date: ${inv.list_polecony_ignored_date}`);
    console.log('');
  });

  // Podsumowanie
  const withListPolecony = invoices.filter(i => i.list_polecony === true);
  const withIgnored = invoices.filter(i => i.list_polecony_ignored === true);

  console.log('=== PODSUMOWANIE ===');
  console.log(`Faktur z list_polecony = true: ${withListPolecony.length}`);
  console.log(`Faktur z list_polecony_ignored = true: ${withIgnored.length}`);
  console.log(`Suma TOTAL (list_polecony=true): €${withListPolecony.reduce((s, i) => s + (i.total || 0), 0)}`);
  console.log(`Suma BALANCE (list_polecony=true): €${withListPolecony.reduce((s, i) => s + ((i.total || 0) - (i.paid || 0)), 0).toFixed(2)}`);
  console.log(`Suma TOTAL (ignored=true): €${withIgnored.reduce((s, i) => s + (i.total || 0), 0)}`);
  console.log(`Suma BALANCE (ignored=true): €${withIgnored.reduce((s, i) => s + ((i.total || 0) - (i.paid || 0)), 0).toFixed(2)}`);
}

checkStructure().catch(console.error);
