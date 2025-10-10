import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';
import { parseInvoiceFlags } from '@/lib/invoice-flags';

export async function GET() {
  try {
    const supabase = supabaseAdmin;

    // Pobierz WSZYSTKICH klientów
    const { data: allClients, error: clientsError } = await supabase()
      .from('clients')
      .select('*');

    if (clientsError) {
      return NextResponse.json({ error: 'clients error', details: clientsError }, { status: 500 });
    }

    // Pobierz WSZYSTKIE faktury z [LIST_POLECONY_STATUS]sent
    const { data: clientInvoices, error: invoicesError } = await supabase()
      .from('invoices')
      .select('*')
      .like('internal_note', '%[LIST_POLECONY_STATUS]sent%');

    if (invoicesError) {
      return NextResponse.json({ error: 'invoices error', details: invoicesError }, { status: 500 });
    }

    // Grupuj faktury po client_id
    const clientInvoicesMap = new Map<number, any[]>();
    for (const invoice of clientInvoices || []) {
      if (!invoice.client_id) continue;

      if (!clientInvoicesMap.has(invoice.client_id)) {
        clientInvoicesMap.set(invoice.client_id, []);
      }
      clientInvoicesMap.get(invoice.client_id)!.push(invoice);
    }

    // Filtruj klientów
    const clientIdsWithInvoices = Array.from(clientInvoicesMap.keys());
    const wyslaneClientsData = allClients?.filter(c => clientIdsWithInvoices.includes(c.id)) || [];

    // Oblicz statystyki
    const wyslaneClients = wyslaneClientsData.map((client) => {
      const invoices = clientInvoicesMap.get(client.id) || [];

      const totalDebt = invoices.reduce((sum, inv) => {
        const outstanding = (inv.total || 0) - (inv.paid || 0);
        return sum + outstanding;
      }, 0);

      const earliestSentDate = invoices.reduce((earliest, inv) => {
        const flags = parseInvoiceFlags(inv.internal_note);
        if (!flags.listPoleconyStatusDate) return earliest;
        const invDate = new Date(flags.listPoleconyStatusDate);
        return !earliest || invDate < earliest ? invDate : earliest;
      }, null as Date | null);

      const daysOverdue = earliestSentDate
        ? Math.floor((Date.now() - earliestSentDate.getTime()) / (1000 * 60 * 60 * 24))
        : 0;

      return {
        id: client.id,
        name: client.name,
        invoice_count: invoices.length,
        total_debt: totalDebt,
        earliest_sent_date: earliestSentDate?.toISOString() || null,
        days_overdue: daysOverdue,
      };
    });

    return NextResponse.json({
      allClientsCount: allClients?.length || 0,
      invoicesWithSentCount: clientInvoices?.length || 0,
      clientIdsWithInvoices: clientIdsWithInvoices,
      wyslaneClientsCount: wyslaneClients.length,
      wyslaneClients: wyslaneClients,
    });
  } catch (error: any) {
    return NextResponse.json({ error: error.message, stack: error.stack }, { status: 500 });
  }
}
