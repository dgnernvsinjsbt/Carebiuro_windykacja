import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

async function main() {
  // Search for invoice by number
  const { data: inv } = await supabase
    .from('invoices')
    .select('id, number, client_id, status, price_gross, paid, payment_to, internal_note')
    .eq('number', 'FP2025/06/000599')
    .single();

  console.log('Faktura FP2025/06/000599:');
  console.log(JSON.stringify(inv, null, 2));

  // Also check client_id type
  if (inv) {
    console.log('\nTyp client_id: ' + typeof inv.client_id);
    
    // Search client
    const { data: client } = await supabase
      .from('clients')
      .select('id, name')
      .eq('id', inv.client_id)
      .single();
    
    console.log('Klient: ' + JSON.stringify(client));
  }
}

main().catch(console.error);
