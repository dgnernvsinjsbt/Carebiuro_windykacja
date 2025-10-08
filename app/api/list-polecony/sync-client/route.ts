/**
 * API Route: Sync Single Client + Invoices from Fakturownia to Supabase
 *
 * POST /api/list-polecony/sync-client
 * Body: { clientId: number }
 */

import { NextRequest, NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';
import { fakturowniaApi } from '@/lib/fakturownia';
import { parseInvoiceFlags } from '@/lib/invoice-flags';

// Force dynamic rendering - don't evaluate at build time
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  try {
    const { clientId } = await request.json();

    if (!clientId) {
      return NextResponse.json(
        { error: 'Brak clientId w żądaniu' },
        { status: 400 }
      );
    }

    console.log(`[Sync Client] Syncing client ${clientId} from Fakturownia to Supabase...`);

    // 1. Pobierz klienta z Fakturowni
    const fakturowniaClient = await fakturowniaApi.getClient(clientId);

    if (!fakturowniaClient) {
      return NextResponse.json(
        { error: 'Klient nie znaleziony w Fakturowni' },
        { status: 404 }
      );
    }

    console.log(`[Sync Client] Client ${clientId} note from Fakturownia:`, fakturowniaClient.note);

    // 2. Aktualizuj klienta w Supabase
    const { error: updateError } = await supabaseAdmin()
      .from('clients')
      .update({
        note: fakturowniaClient.note || '',
        name: fakturowniaClient.name || '',
        email: fakturowniaClient.email || '',
        updated_at: new Date().toISOString(),
      })
      .eq('id', clientId);

    if (updateError) {
      console.error(`[Sync Client] Error updating client ${clientId} in Supabase:`, updateError);
      return NextResponse.json(
        { error: 'Błąd aktualizacji klienta w bazie danych' },
        { status: 500 }
      );
    }

    console.log(`[Sync Client] ✓ Client ${clientId} synced successfully`);

    // 3. Pobierz faktury klienta z Fakturowni
    const fakturowniaInvoices = await fakturowniaApi.getInvoicesByClientId(clientId);
    console.log(`[Sync Client] Fetched ${fakturowniaInvoices.length} invoices for client ${clientId}`);

    let invoicesSynced = 0;

    // 4. Aktualizuj faktury w Supabase
    for (const invoice of fakturowniaInvoices) {
      // Parsuj flagi z internal_note
      const flags = parseInvoiceFlags(invoice.internal_note);

      console.log(`[Sync Client] Invoice ${invoice.id} flags:`, flags);

      // Aktualizuj fakturę w Supabase
      const { error: invoiceError } = await supabaseAdmin()
        .from('invoices')
        .update({
          comment: invoice.internal_note || '',
          list_polecony: flags.listPoleconyStatus === 'sent', // boolean flag (stary format)
          list_polecony_sent_date: flags.listPoleconyStatus === 'sent' ? flags.listPoleconyStatusDate : null,
          list_polecony_ignored: flags.listPoleconyStatus === 'ignore', // boolean flag (stary format)
          list_polecony_ignored_date: flags.listPoleconyStatus === 'ignore' ? flags.listPoleconyStatusDate : null,
          updated_at: new Date().toISOString(),
        })
        .eq('id', invoice.id);

      if (invoiceError) {
        console.error(`[Sync Client] Error updating invoice ${invoice.id}:`, invoiceError);
      } else {
        invoicesSynced++;
      }
    }

    console.log(`[Sync Client] ✓ Synced ${invoicesSynced}/${fakturowniaInvoices.length} invoices`);

    return NextResponse.json({
      success: true,
      message: `Klient ${clientId} + ${invoicesSynced} faktur zsynchronizowanych`,
      note: fakturowniaClient.note,
      invoices_synced: invoicesSynced,
    });
  } catch (error: any) {
    console.error('[Sync Client] Error:', error);
    return NextResponse.json(
      { error: error.message || 'Błąd synchronizacji' },
      { status: 500 }
    );
  }
}
