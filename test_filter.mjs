import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

async function testFilter() {
  const { data: allClients } = await supabase
    .from('clients')
    .select('*');

  console.log('Wszystkich klientów:', allClients ? allClients.length : 0);

  const testClient = allClients ? allClients.find(c => c.id === 211779362) : null;
  console.log('Czy klient 211779362 istnieje w allClients:', testClient ? 'TAK' : 'NIE');

  if (testClient) {
    console.log('Dane klienta:', JSON.stringify(testClient, null, 2).substring(0, 300));
  }

  const clientIdsWithInvoices = [211779362];
  const filtered = allClients ? allClients.filter(c => clientIdsWithInvoices.includes(c.id)) : [];

  console.log('\nPo filtrze .includes():');
  console.log('Liczba klientów:', filtered.length);

  if (filtered.length > 0) {
    console.log('Pierwszy klient ID:', filtered[0].id);
  }
}

testFilter();
