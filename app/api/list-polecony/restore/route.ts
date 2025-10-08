/**
 * API Route: Restore Ignored Clients
 *
 * Usuwa flagi [LIST_POLECONY_IGNORED] z klientów i faktur,
 * przywracając ich do zakładki "Do wysłania"
 */

import { NextRequest, NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';
import { setListPoleconyIgnored } from '@/lib/client-flags';
import { removeListPoleconyIgnoredFromInvoice, parseInvoiceFlags } from '@/lib/invoice-flags';
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

    let totalInvoicesSynced = 0;

    // 3. Aktualizuj klientów + zsynchronizuj wszystkie faktury z Fakturowni
    for (const client of clients || []) {
      console.log(`[ListPolecony Restore] Client ${client.id} before:`, client.note);
      const updatedNote = setListPoleconyIgnored(client.note, false);
      console.log(`[ListPolecony Restore] Client ${client.id} after:`, updatedNote);

      // Aktualizuj w Supabase
      const { error: updateError } = await supabaseAdmin()
        .from('clients')
        .update({ note: updatedNote })
        .eq('id', client.id);

      if (updateError) {
        console.error(`[ListPolecony Restore] Error updating client ${client.id} in Supabase:`, updateError);
        continue;
      }

      // Aktualizuj w Fakturowni
      try {
        await fakturowniaApi.updateClient(client.id, { note: updatedNote });
        console.log(`[ListPolecony Restore] ✓ Restored client ${client.id}`);
      } catch (apiError) {
        console.error(`[ListPolecony Restore] Error updating client ${client.id} in Fakturownia:`, apiError);
      }

      // PEŁNA SYNCHRONIZACJA FAKTUR z Fakturowni
      // KROK 1: Najpierw ustaw IGNORED=false w Fakturowni dla faktur z flagą
      try {
        console.log(`[ListPolecony Restore] Restoring invoices with IGNORED flag for client ${client.id}...`);

        // Pobierz faktury z Supabase które mają IGNORED=true
        const { data: ignoredInvoices } = await supabaseAdmin()
          .from('invoices')
          .select('*')
          .eq('client_id', client.id)
          .eq('list_polecony_ignored', true);

        for (const invoice of ignoredInvoices || []) {
          const updatedComment = removeListPoleconyIgnoredFromInvoice(invoice.internal_note);

          // Aktualizuj w Fakturowni NAJPIERW
          try {
            await fakturowniaApi.updateInvoice(invoice.id, {
              internal_note: updatedComment,
            });
            console.log(`[ListPolecony Restore] ✓ Restored invoice ${invoice.id} in Fakturownia`);
          } catch (apiError) {
            console.error(`[ListPolecony Restore] Error updating invoice ${invoice.id} in Fakturownia:`, apiError);
          }
        }
      } catch (error) {
        console.error(`[ListPolecony Restore] Error restoring invoices in Fakturownia:`, error);
      }

      // KROK 2: Teraz zsynchronizuj wszystkie faktury z Fakturowni do Supabase
      try {
        console.log(`[ListPolecony Restore] Syncing all invoices for client ${client.id}...`);
        const fakturowniaInvoices = await fakturowniaApi.getInvoicesByClientId(client.id);
        console.log(`[ListPolecony Restore] Fetched ${fakturowniaInvoices.length} invoices for client ${client.id}`);

        for (const invoice of fakturowniaInvoices) {
          // Parsuj flagi z internal_note (teraz już zaktualizowane w Fakturowni)
          const flags = parseInvoiceFlags(invoice.internal_note);

          // Aktualizuj fakturę w Supabase
          const { error: invoiceError } = await supabaseAdmin()
            .from('invoices')
            .update({
              internal_note: invoice.internal_note || '',
              list_polecony: flags.listPolecony,
              list_polecony_sent_date: flags.listPoleconySentDate,
              list_polecony_ignored: flags.listPoleconyIgnored,
              list_polecony_ignored_date: flags.listPoleconyIgnoredDate,
              updated_at: new Date().toISOString(),
            })
            .eq('id', invoice.id);

          if (invoiceError) {
            console.error(`[ListPolecony Restore] Error updating invoice ${invoice.id}:`, invoiceError);
          } else {
            totalInvoicesSynced++;
          }
        }

        console.log(`[ListPolecony Restore] ✓ Synced ${fakturowniaInvoices.length} invoices for client ${client.id}`);
      } catch (syncError) {
        console.error(`[ListPolecony Restore] Error syncing invoices for client ${client.id}:`, syncError);
      }
    }

    console.log(`[ListPolecony Restore] ✓ Restoration complete - ${clients?.length || 0} clients, ${totalInvoicesSynced} invoices synced`);

    return NextResponse.json({
      success: true,
      message: `Przywrócono ${clients?.length || 0} klientów`,
      clients_restored: clients?.length || 0,
      invoices_synced: totalInvoicesSynced,
    });
  } catch (error: any) {
    console.error('[ListPolecony Restore] Error:', error);
    return NextResponse.json(
      { error: error.message || 'Błąd przywracania klientów' },
      { status: 500 }
    );
  }
}
