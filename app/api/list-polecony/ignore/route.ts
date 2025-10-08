/**
 * API Endpoint: Ignore List Polecony Clients
 *
 * POST /api/list-polecony/ignore
 * Body: { clientIds: number[] }
 *
 * Ustawia flagę IGNORED dla klientów i ich faktur z trzecim upomnieniem
 */

import { NextRequest, NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';
import { fakturowniaApi } from '@/lib/fakturownia';
import { setListPoleconyStatusIgnore, parseInvoiceFlags } from '@/lib/invoice-flags';

// Force dynamic rendering - don't evaluate at build time
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  try {
    let clientIds: number[] = [];

    const contentType = request.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      const body = await request.json();
      clientIds = body.clientIds;
    }

    console.log('[ListPolecony Ignore] Otrzymano request z clientIds:', clientIds);

    if (!clientIds || !Array.isArray(clientIds) || clientIds.length === 0) {
      return NextResponse.json(
        { success: false, error: 'Brak wybranych klientów' },
        { status: 400 }
      );
    }

    console.log(`[ListPolecony Ignore] Ignorowanie ${clientIds.length} klientów...`);

    // Pobierz klientów z Supabase
    const { data: clients, error: clientsError } = await supabaseAdmin()
      .from('clients')
      .select('*')
      .in('id', clientIds);

    if (clientsError) {
      console.error('[ListPolecony Ignore] Error fetching clients:', clientsError);
      return NextResponse.json(
        { success: false, error: 'Błąd pobierania klientów' },
        { status: 500 }
      );
    }

    if (!clients || clients.length === 0) {
      return NextResponse.json(
        { success: false, error: 'Nie znaleziono klientów' },
        { status: 404 }
      );
    }

    // Pobierz faktury z [LIST_POLECONY_STATUS]sent w internal_note dla tych klientów (czyli te które były wysłane)
    const { data: invoices, error: invoicesError } = await supabaseAdmin()
      .from('invoices')
      .select('*')
      .in('client_id', clientIds)
      .like('internal_note', '%[LIST_POLECONY_STATUS]sent%');

    if (invoicesError) {
      console.error('[ListPolecony Ignore] Error fetching invoices:', invoicesError);
    }

    console.log(`[ListPolecony Ignore] Znaleziono ${invoices?.length || 0} faktur z [LIST_POLECONY_STATUS]sent`);

    if (invoices && invoices.length > 0) {
      console.log('[ListPolecony Ignore] Przykładowa faktura przed aktualizacją:', {
        id: invoices[0].id,
        internal_note_preview: invoices[0].internal_note?.substring(0, 200)
      });
    } else {
      console.log('[ListPolecony Ignore] NIE ZNALEZIONO ŻADNYCH FAKTUR - sprawdzam czy faktury istnieją dla tych klientów...');
      const { data: allInvoices } = await supabaseAdmin()
        .from('invoices')
        .select('id, client_id, internal_note')
        .in('client_id', clientIds)
        .limit(5);
      console.log('[ListPolecony Ignore] Wszystkie faktury dla tych klientów (max 5):', allInvoices?.map(i => ({
        id: i.id,
        client_id: i.client_id,
        has_internal_note: !!i.internal_note,
        internal_note_preview: i.internal_note?.substring(0, 100)
      })));
    }

    // Zaktualizuj flagę [LIST_POLECONY_STATUS]ignore dla klientów
    console.log('[ListPolecony Ignore] Aktualizowanie flag klientów...');
    const today = new Date();

    const updateClientPromises = clients.map(async (client) => {
      try {
        // Parsuj obecną datę (zachowaj oryginalną datę wysłania)
        const clientFlags = parseInvoiceFlags(client.note);
        const originalDate = clientFlags.listPoleconyStatusDate || today.toISOString().split('T')[0];

        // Użyj nowego formatu [LIST_POLECONY_STATUS]ignore (zachowaj datę)
        console.log(`[Update Client] ${client.id} - current note:`, client.note);
        const updatedNote = setListPoleconyStatusIgnore(client.note || '', originalDate);
        console.log(`[Update Client] ${client.id} - updated note:`, updatedNote);

        // 1. Zaktualizuj w Supabase
        const { error: supabaseError } = await supabaseAdmin()
          .from('clients')
          .update({ note: updatedNote })
          .eq('id', client.id);

        if (supabaseError) {
          console.error(`✗ BŁĄD Supabase dla klienta ${client.id}:`, supabaseError);
          throw supabaseError;
        }
        console.log(`✓ Supabase zaktualizowany: client ${client.id}`);

        // 2. Zaktualizuj w Fakturowni
        await fakturowniaApi.updateClient(client.id, {
          note: updatedNote
        });
        console.log(`✓ Fakturownia zaktualizowana: client ${client.id}`);
      } catch (err) {
        console.error(`✗ Błąd aktualizacji klienta ${client.id}:`, err);
      }
    });

    await Promise.all(updateClientPromises);
    console.log('Zakończono aktualizację flag klientów');

    // Zaktualizuj status=ignore na fakturach
    console.log('[ListPolecony Ignore] Aktualizowanie status=ignore na fakturach...');

    const invoiceUpdatePromises = (invoices || []).map(async (invoice) => {
      try {
        // Parsuj oryginalną datę (zachowaj datę wysłania)
        const flags = parseInvoiceFlags(invoice.internal_note);
        const originalDate = flags.listPoleconyStatusDate || today.toISOString().split('T')[0];

        // Ustaw status=ignore (zachowaj oryginalną datę)
        const updatedInternalNote = setListPoleconyStatusIgnore(invoice.internal_note || '', originalDate);

        console.log(`[Update Invoice] ${invoice.id} - new internal_note:`, updatedInternalNote);
        console.log(`[Update Invoice] ${invoice.id} - original_date (preserved):`, originalDate);

        // 1. Zaktualizuj w Supabase
        const { error: supabaseError } = await supabaseAdmin()
          .from('invoices')
          .update({
            internal_note: updatedInternalNote,
            list_polecony_ignored: true, // boolean flag (stary format dla kompatybilności)
            list_polecony_ignored_date: today.toISOString(), // data ignorowania (do historii)
            list_polecony_sent_date: originalDate // data wysłania (ZACHOWANA)
          })
          .eq('id', invoice.id);

        if (supabaseError) {
          console.error(`✗ BŁĄD Supabase dla faktury ${invoice.id}:`, supabaseError);
          throw supabaseError;
        }
        console.log(`✓ Supabase zaktualizowany: invoice ${invoice.id}`);

        // 2. Zaktualizuj w Fakturowni
        await fakturowniaApi.updateInvoice(invoice.id, {
          internal_note: updatedInternalNote
        });
        console.log(`✓ Fakturownia zaktualizowana: invoice ${invoice.id}`);
      } catch (err) {
        console.error(`✗ Błąd aktualizacji faktury ${invoice.id}:`, err);
      }
    });

    await Promise.all(invoiceUpdatePromises);
    console.log('Zakończono aktualizację flag na fakturach');

    return NextResponse.json({
      success: true,
      message: `Zignorowano ${clientIds.length} klientów i ${invoices?.length || 0} faktur`,
      data: {
        clients_count: clientIds.length,
        invoices_count: invoices?.length || 0
      }
    });
  } catch (error: any) {
    console.error('[ListPolecony Ignore] Error:', error);
    return NextResponse.json(
      {
        success: false,
        error: 'Błąd ignorowania klientów',
        details: error.message
      },
      { status: 500 }
    );
  }
}
