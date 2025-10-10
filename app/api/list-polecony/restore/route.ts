/**
 * API Route: Restore Ignored Clients
 *
 * Zmienia status z [LIST_POLECONY_STATUS]ignore na [LIST_POLECONY_STATUS]false
 * Przywraca faktury do zakładki "Do wysłania" (nie do "Wysłane"!)
 */

import { NextRequest, NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';
import { setListPoleconyStatusFalse, parseInvoiceFlags } from '@/lib/invoice-flags';
import { fakturowniaApi } from '@/lib/fakturownia';

// Force dynamic rendering - don't evaluate at build time
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  try {
    const { clientIds } = await request.json();

    if (!clientIds || !Array.isArray(clientIds) || clientIds.length === 0) {
      return NextResponse.json(
        { error: 'Brak clientIds w żądaniu' },
        { status: 400 }
      );
    }

    console.log(`[ListPolecony Restore] Restoring ${clientIds.length} clients from ignored...`);

    // 1. Pobierz klientów
    const { data: clients, error: clientsError } = await supabaseAdmin()
      .from('clients')
      .select('*')
      .in('id', clientIds);

    if (clientsError) {
      console.error('[ListPolecony Restore] Error fetching clients:', clientsError);
      return NextResponse.json(
        { error: 'Błąd pobierania klientów z bazy danych' },
        { status: 500 }
      );
    }

    console.log(`[ListPolecony Restore] Found ${clients?.length || 0} clients to restore`);

    let totalInvoicesRestored = 0;

    // 2. Dla każdego klienta: zmień status ignore → false (przywróć do "Do wysłania")
    for (const client of clients || []) {
      console.log(`[ListPolecony Restore] Processing client ${client.id}...`);

      // Pobierz faktury ze status=ignore dla tego klienta
      const { data: ignoredInvoices } = await supabaseAdmin()
        .from('invoices')
        .select('*')
        .eq('client_id', client.id)
        .like('internal_note', '%[LIST_POLECONY_STATUS]ignore%');

      console.log(`[ListPolecony Restore] Found ${ignoredInvoices?.length || 0} ignored invoices for client ${client.id}`);

      // Zmień status ignore → false na każdej fakturze
      for (const invoice of ignoredInvoices || []) {
        // Ustaw status=false (przywrócenie do "Do wysłania")
        const updatedInternalNote = setListPoleconyStatusFalse(invoice.internal_note);

        // Aktualizuj w Supabase
        const { error: invoiceError } = await supabaseAdmin()
          .from('invoices')
          .update({ internal_note: updatedInternalNote })
          .eq('id', invoice.id);

        if (invoiceError) {
          console.error(`[ListPolecony Restore] Error updating invoice ${invoice.id} in Supabase:`, invoiceError);
          continue;
        }

        // Aktualizuj w Fakturowni
        try {
          await fakturowniaApi.updateInvoice(invoice.id, {
            internal_note: updatedInternalNote
          });
          console.log(`[ListPolecony Restore] ✓ Invoice ${invoice.id} restored (status=false) in Fakturownia`);
          totalInvoicesRestored++;
        } catch (apiError) {
          console.error(`[ListPolecony Restore] Error updating invoice ${invoice.id} in Fakturownia:`, apiError);
        }
      }
    }

    console.log(`[ListPolecony Restore] ✓ Restoration complete - ${clients?.length || 0} clients, ${totalInvoicesRestored} invoices`);

    return NextResponse.json({
      success: true,
      message: `Przywrócono ${clients?.length || 0} klientów`,
      clients_restored: clients?.length || 0,
      invoices_restored: totalInvoicesRestored,
    });
  } catch (error: any) {
    console.error('[ListPolecony Restore] Error:', error);
    return NextResponse.json(
      { error: error.message || 'Błąd przywracania klientów' },
      { status: 500 }
    );
  }
}
