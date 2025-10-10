import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

async function testTypes() {
  const { data: clients } = await supabase
    .from('clients')
    .select('id')
    .eq('id', 211779362)
    .limit(1);

  const { data: invoices } = await supabase
    .from('invoices')
    .select('client_id')
    .eq('client_id', 211779362)
    .limit(1);

  console.log('Client ID type:', typeof clients[0].id, '=', clients[0].id);
  console.log('Invoice client_id type:', typeof invoices[0].client_id, '=', invoices[0].client_id);

  const map = new Map();
  map.set(invoices[0].client_id, []);

  const ids = Array.from(map.keys());
  console.log('Map keys type:', typeof ids[0], '=', ids[0]);

  console.log('\nTest includes():');
  console.log('ids.includes(211779362):', ids.includes(211779362));
  console.log('ids.includes(clients[0].id):', ids.includes(clients[0].id));

  console.log('\nComparison:');
  console.log('ids[0] === 211779362:', ids[0] === 211779362);
  console.log('ids[0] === clients[0].id:', ids[0] === clients[0].id);
  console.log('ids[0] == clients[0].id:', ids[0] == clients[0].id);
}

testTypes();
