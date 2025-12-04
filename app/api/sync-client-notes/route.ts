/**
 * API Endpoint: Sync Client Notes
 *
 * POST /api/sync-client-notes
 *
 * Synchronizuje TYLKO pole `note` klientów z Fakturowni do Supabase.
 * Używane jednorazowo do naprawy brakujących notatek.
 */

import { NextRequest, NextResponse } from 'next/server';
import { fakturowniaApi } from '@/lib/fakturownia';
import { supabaseAdmin } from '@/lib/supabase';

// Force dynamic rendering - don't evaluate at build time
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  try {
    console.log('[SyncClientNotes] Starting sync...');

    // Pobierz wszystkich klientów z Fakturowni
    console.log('[SyncClientNotes] Fetching all clients from Fakturownia...');
    const fakturowniaClients = await fakturowniaApi.fetchAllClients();
    console.log(`[SyncClientNotes] Fetched ${fakturowniaClients.length} clients from Fakturownia`);

    // Pobierz WSZYSTKICH klientów z Supabase (z paginacją - limit domyślny to 1000)
    const supabaseClients: Array<{ id: number; note: string | null }> = [];
    const pageSize = 1000;
    let offset = 0;
    let hasMore = true;

    while (hasMore) {
      const { data: clientPage, error: pageError } = await supabaseAdmin()
        .from('clients')
        .select('id, note')
        .range(offset, offset + pageSize - 1)
        .order('id', { ascending: true });

      if (pageError) {
        console.error('[SyncClientNotes] Error fetching clients page:', pageError);
        return NextResponse.json(
          { success: false, error: 'Error fetching clients from Supabase' },
          { status: 500 }
        );
      }

      if (clientPage && clientPage.length > 0) {
        supabaseClients.push(...clientPage);
        offset += pageSize;
        hasMore = clientPage.length === pageSize;
      } else {
        hasMore = false;
      }
    }

    console.log(`[SyncClientNotes] Fetched ${supabaseClients.length} clients from Supabase (paginated)`);

    // Stwórz mapę: clientId → note (z Fakturowni)
    const clientNotesMap = new Map<number, string>();
    for (const fc of fakturowniaClients) {
      if (fc.note) {
        clientNotesMap.set(fc.id, fc.note);
      }
    }

    // Zaktualizuj notatki w Supabase dla klientów, którzy mają notatki w Fakturowni
    let updatedCount = 0;
    let skippedCount = 0;

    for (const client of supabaseClients) {
      const fakturowniaNote = clientNotesMap.get(client.id);

      // Pomiń jeśli brak notatki w Fakturowni lub jest taka sama jak w Supabase
      if (!fakturowniaNote || fakturowniaNote === client.note) {
        skippedCount++;
        continue;
      }

      // Zaktualizuj notatkę w Supabase
      const { error: updateError } = await supabaseAdmin()
        .from('clients')
        .update({ note: fakturowniaNote })
        .eq('id', client.id);

      if (updateError) {
        console.error(`[SyncClientNotes] Error updating client ${client.id}:`, updateError);
      } else {
        updatedCount++;
        console.log(`[SyncClientNotes] ✓ Updated client ${client.id}`);
      }
    }

    console.log(`[SyncClientNotes] Sync complete: ${updatedCount} updated, ${skippedCount} skipped`);

    return NextResponse.json({
      success: true,
      data: {
        total_fakturownia_clients: fakturowniaClients.length,
        total_supabase_clients: supabaseClients.length,
        clients_with_notes: clientNotesMap.size,
        updated: updatedCount,
        skipped: skippedCount,
      },
    });
  } catch (error: any) {
    console.error('[SyncClientNotes] Error:', error);
    return NextResponse.json(
      {
        success: false,
        error: 'Sync failed',
        details: error.message,
      },
      { status: 500 }
    );
  }
}
