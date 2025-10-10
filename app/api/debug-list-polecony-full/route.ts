import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';
import { hasThirdReminder, qualifiesForListPolecony, getInvoicesWithThirdReminder, calculateTotalDebt } from '@/lib/list-polecony-logic';
import { parseInvoiceFlags } from '@/lib/invoice-flags';

export const dynamic = 'force-dynamic';

export async function GET() {
  const supabase = supabaseAdmin;

  // Pobierz faktury z trzecim upomnieniem
  const { data: allInvoices, error: invoicesError } = await supabase()
    .from('invoices')
    .select('*')
    .or('internal_note.like.%EMAIL_3=TRUE%,internal_note.like.%SMS_3=TRUE%,internal_note.like.%WHATSAPP_3=TRUE%');

  if (invoicesError) {
    return NextResponse.json({ error: invoicesError.message }, { status: 500 });
  }

  console.log(`[Debug] Fetched ${allInvoices?.length || 0} invoices with EMAIL_3/SMS_3/WHATSAPP_3`);

  // Filtruj faktury z trzecim upomnieniem ORAZ które NIE mają statusu 'sent' lub 'ignore'
  const invoicesWithThirdReminder = (allInvoices || []).filter(inv => {
    if (!hasThirdReminder(inv)) return false;
    const flags = parseInvoiceFlags(inv.internal_note);
    if (flags.listPoleconyStatus === 'sent') return false;
    if (flags.listPoleconyStatus === 'ignore') return false;
    return true;
  });

  console.log(`[Debug] Found ${invoicesWithThirdReminder.length} invoices with third reminder AND status != sent/ignore`);

  // Grupuj faktury po client_id
  const clientInvoicesMap = new Map<number, any[]>();
  const clientIds = new Set<number>();

  for (const invoice of invoicesWithThirdReminder || []) {
    if (!invoice.client_id) continue;
    clientIds.add(invoice.client_id);
    if (!clientInvoicesMap.has(invoice.client_id)) {
      clientInvoicesMap.set(invoice.client_id, []);
    }
    clientInvoicesMap.get(invoice.client_id)!.push(invoice);
  }

  console.log(`[Debug] Found ${clientIds.size} unique clients with qualifying invoices`);

  // Pobierz klientów
  const { data: clients, error: clientsError } = await supabase()
    .from('clients')
    .select('*')
    .in('id', Array.from(clientIds));

  if (clientsError) {
    return NextResponse.json({ error: clientsError.message }, { status: 500 });
  }

  console.log(`[Debug] Fetched ${clients?.length || 0} clients`);

  // Mapuj klientów
  const qualifiedClients = (clients || [])
    .map((client) => {
      const clientInvoices = clientInvoicesMap.get(client.id) || [];
      const qualifies = qualifiesForListPolecony(client, clientInvoices);

      if (!qualifies) {
        console.log(`[Debug] Client ${client.id} (${client.name}) does NOT qualify - has ${clientInvoices.length} invoices`);
        return null;
      }

      const invoicesWithReminders = getInvoicesWithThirdReminder(clientInvoices);
      const totalDebt = calculateTotalDebt(clientInvoices);

      console.log(`[Debug] Client ${client.id} (${client.name}) QUALIFIES - ${invoicesWithReminders.length} invoices, €${totalDebt} debt`);

      return {
        id: client.id,
        name: client.name,
        email: client.email,
        invoice_count: invoicesWithReminders.length,
        total_debt: totalDebt,
      };
    })
    .filter(Boolean);

  console.log(`[Debug] Final count: ${qualifiedClients.length} clients qualify`);

  return NextResponse.json({
    stats: {
      total_invoices: allInvoices?.length || 0,
      invoices_with_third_reminder: invoicesWithThirdReminder.length,
      unique_clients_with_qualifying_invoices: clientIds.size,
      clients_fetched: clients?.length || 0,
      clients_qualifying: qualifiedClients.length,
    },
    qualified_clients: qualifiedClients,
    client_ids_with_invoices: Array.from(clientIds),
  });
}
