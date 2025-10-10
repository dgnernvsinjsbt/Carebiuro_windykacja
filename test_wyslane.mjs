import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

async function testWyslane() {
  console.log('\n=== Symulacja getWyslaneClients() ===\n');

  // 1. Pobierz wszystkich klientów
  const { data: allClients } = await supabase
    .from('clients')
    .select('*');
  console.log(`1. Pobranych klientów: ${allClients ? allClients.length : 0}`);

  // 2. Pobierz faktury z flagą sent
  const { data: clientInvoices } = await supabase
    .from('invoices')
    .select('*')
    .ilike('internal_note', '%\\[LIST\\_POLECONY\\_STATUS\\]sent%');
  console.log(`2. Faktur z flagą sent: ${clientInvoices ? clientInvoices.length : 0}`);

  // 3. Grupuj po client_id
  const clientInvoicesMap = new Map();
  for (const invoice of clientInvoices || []) {
    if (!invoice.client_id) continue;
    if (!clientInvoicesMap.has(invoice.client_id)) {
      clientInvoicesMap.set(invoice.client_id, []);
    }
    clientInvoicesMap.get(invoice.client_id).push(invoice);
  }
  console.log(`3. Unikalnych klientów z flagą sent: ${clientInvoicesMap.size}`);

  // 4. Sprawdź czy jest klient 211779362
  if (clientInvoicesMap.has(211779362)) {
    const invoices = clientInvoicesMap.get(211779362);
    console.log(`4. Klient 211779362 MA ${invoices.length} faktur z flagą sent`);
    invoices.forEach(inv => console.log(`   - Faktura ${inv.id}: ${inv.number}`));
  } else {
    console.log(`4. Klient 211779362 NIE MA faktur z flagą sent`);
  }

  // 5. Filtruj klientów
  const clientIdsWithInvoices = Array.from(clientInvoicesMap.keys());
  const wyslaneClientsData = allClients ? allClients.filter(c => clientIdsWithInvoices.includes(c.id)) : [];
  console.log(`5. Klientów do wyświetlenia: ${wyslaneClientsData.length}`);

  // 6. Sprawdź czy 211779362 jest na liście
  const hasTestClient = wyslaneClientsData.some(c => c.id === 211779362);
  console.log(`6. Czy klient 211779362 jest na finalnej liście: ${hasTestClient ? 'TAK' : 'NIE'}`);

  if (hasTestClient) {
    const client = wyslaneClientsData.find(c => c.id === 211779362);
    console.log(`   Dane klienta:`, client);
  }
}

testWyslane();
