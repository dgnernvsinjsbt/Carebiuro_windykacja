import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

async function testQuery() {
  console.log('\n=== TEST 1: LIKE bez escape ===');
  const { data: r1 } = await supabase
    .from('invoices')
    .select('id')
    .eq('client_id', 211779362)
    .like('internal_note', '%[LIST_POLECONY_STATUS]sent%');
  console.log('Wynik:', r1 ? r1.length : 0, 'faktur');

  console.log('\n=== TEST 2: ILIKE z escape ===');
  const { data: r2 } = await supabase
    .from('invoices')
    .select('id')
    .eq('client_id', 211779362)
    .ilike('internal_note', '%\\[LIST\\_POLECONY\\_STATUS\\]sent%');
  console.log('Wynik:', r2 ? r2.length : 0, 'faktur');

  console.log('\n=== TEST 3: Client-side filter ===');
  const { data: all } = await supabase
    .from('invoices')
    .select('id, internal_note')
    .eq('client_id', 211779362);

  const filtered = all ? all.filter(inv =>
    inv.internal_note && inv.internal_note.includes('[LIST_POLECONY_STATUS]sent')
  ) : [];
  console.log('Wszystkie faktury:', all ? all.length : 0);
  console.log('Z flagą sent:', filtered.length);
}

testQuery();
