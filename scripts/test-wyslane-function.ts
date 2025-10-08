import { supabaseAdmin } from '../lib/supabase';
import { parseInvoiceFlags } from '../lib/invoice-flags';

async function testWyslaneFunction() {
  console.log('Testing getWyslaneClients function...\n');

  const supabase = supabaseAdmin;

  // Pobierz WSZYSTKICH klientów
  const { data: allClients, error: clientsError } = await supabase()
    .from('clients')
    .select('*');

  if (clientsError) {
    console.error('Error fetching clients:', clientsError);
    return;
  }

  console.log(`✅ Fetched ${allClients?.length || 0} total clients`);

  // Pobierz WSZYSTKIE faktury z [LIST_POLECONY_STATUS]sent
  const { data: clientInvoices, error: invoicesError } = await supabase()
    .from('invoices')
    .select('*')
    .like('internal_note', '%[LIST_POLECONY_STATUS]sent%');

  if (invoicesError) {
    console.error('Error fetching invoices:', invoicesError);
    return;
  }

  console.log(`✅ Fetched ${clientInvoices?.length || 0} invoices with sent list polecony`);

  // Grupuj faktury po client_id
  const clientInvoicesMap = new Map<number, any[]>();
  for (const invoice of clientInvoices || []) {
    if (!invoice.client_id) {
      console.log(`⚠️  Invoice ${invoice.id} has no client_id`);
      continue;
    }

    if (!clientInvoicesMap.has(invoice.client_id)) {
      clientInvoicesMap.set(invoice.client_id, []);
    }
    clientInvoicesMap.get(invoice.client_id)!.push(invoice);
  }

  console.log(`✅ Grouped invoices by client_id. Found ${clientInvoicesMap.size} unique clients`);
  console.log('   Client IDs:', Array.from(clientInvoicesMap.keys()));

  // Filtruj klientów - tylko ci którzy mają faktury
  const clientIdsWithInvoices = Array.from(clientInvoicesMap.keys());
  const wyslaneClientsData = allClients?.filter(c => clientIdsWithInvoices.includes(c.id)) || [];

  console.log(`\n✅ ${wyslaneClientsData.length} clients have invoices with STATUS=sent`);

  // Oblicz statystyki dla każdego klienta
  const wyslaneClients = wyslaneClientsData.map((client) => {
    const invoices = clientInvoicesMap.get(client.id) || [];

    console.log(`\n📋 Client ${client.id} (${client.name}):`);
    console.log(`   - ${invoices.length} invoices with sent status`);

    // Oblicz zadłużenie
    const totalDebt = invoices.reduce((sum, inv) => {
      console.log(`     Invoice ${inv.id}: outstanding=${inv.outstanding}`);
      return sum + (inv.outstanding || 0);
    }, 0);

    console.log(`   - Total debt: €${totalDebt}`);

    // Znajdź najwcześniejszą datę wysłania
    const earliestSentDate = invoices.reduce((earliest, inv) => {
      const flags = parseInvoiceFlags(inv.internal_note);
      console.log(`     Invoice ${inv.id}: statusDate=${flags.listPoleconyStatusDate}`);
      if (!flags.listPoleconyStatusDate) return earliest;
      const invDate = new Date(flags.listPoleconyStatusDate);
      return !earliest || invDate < earliest ? invDate : earliest;
    }, null as Date | null);

    const daysOverdue = earliestSentDate
      ? Math.floor((Date.now() - earliestSentDate.getTime()) / (1000 * 60 * 60 * 24))
      : 0;

    console.log(`   - Earliest sent: ${earliestSentDate?.toISOString()}`);
    console.log(`   - Days overdue: ${daysOverdue}`);

    return {
      ...client,
      invoice_count: invoices.length,
      total_debt: totalDebt,
      earliest_sent_date: earliestSentDate?.toISOString() || null,
      days_overdue: daysOverdue,
    };
  });

  console.log(`\n\n🎉 FINAL RESULT: ${wyslaneClients.length} clients to display`);
  wyslaneClients.forEach(c => {
    console.log(`   - ${c.name} (ID: ${c.id}): ${c.invoice_count} invoices, €${c.total_debt} debt`);
  });
}

testWyslaneFunction().catch(console.error);
