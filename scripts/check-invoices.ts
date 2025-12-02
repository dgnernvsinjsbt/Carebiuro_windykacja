import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

async function main() {
  // Check Adam Olkowicz invoices (ID: 148631882) - we sent him email today
  const clientId = 148631882;
  
  const { data: invoices, error } = await supabase
    .from('invoices')
    .select('id, number, client_id, status, price_gross, paid, payment_to')
    .eq('client_id', clientId);

  console.log('Faktury dla Adam Olkowicz (ID: ' + clientId + ') w Supabase:');
  console.log('Znaleziono: ' + (invoices?.length || 0));
  
  if (invoices && invoices.length > 0) {
    for (const inv of invoices) {
      console.log('- ' + inv.number + ' | status=' + inv.status + ' | ' + inv.price_gross + ' EUR');
    }
  } else {
    console.log('BRAK FAKTUR W SUPABASE!');
  }

  // Check total invoices in Supabase
  const { count } = await supabase
    .from('invoices')
    .select('*', { count: 'exact', head: true });
  
  console.log('\nLaczna liczba faktur w Supabase: ' + count);

  // Check total clients in Supabase
  const { count: clientCount } = await supabase
    .from('clients')
    .select('*', { count: 'exact', head: true });
  
  console.log('Laczna liczba klientow w Supabase: ' + clientCount);
}

main().catch(console.error);
