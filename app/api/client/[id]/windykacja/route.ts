import { NextRequest, NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';
import { setWindykacja } from '@/lib/client-flags';

/**
 * PATCH /api/client/[id]/windykacja
 * Toggle WINDYKACJA (auto-reminders) for a client
 *
 * Aktualizuje pole "note" klienta w Fakturowni dodając/zmieniając tag [WINDYKACJA]true/false[/WINDYKACJA]
 */
// Force dynamic rendering - don't evaluate at build time
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function PATCH(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const clientId = parseInt(params.id, 10);
    const body = await request.json();
    const { windykacja_enabled } = body;

    if (typeof windykacja_enabled !== 'boolean') {
      return NextResponse.json(
        { success: false, error: 'windykacja_enabled must be a boolean' },
        { status: 400 }
      );
    }

    console.log(`[Windykacja] Updating client ${clientId}: windykacja_enabled=${windykacja_enabled}`);

    // 1. Pobierz aktualny note klienta z Supabase
    const { data: client, error: fetchError } = await supabase()
      .from('clients')
      .select('note')
      .eq('id', clientId)
      .single();

    if (fetchError || !client) {
      console.error('[Windykacja] Client not found:', fetchError);
      return NextResponse.json(
        { success: false, error: 'Client not found' },
        { status: 404 }
      );
    }

    // 2. Zaktualizuj tag [WINDYKACJA] w note (wszystkie 3 flagi w jednej linii)
    const updatedNote = setWindykacja(client.note, windykacja_enabled);

    console.log(`[Windykacja] Updating note in Fakturownia:`, {
      oldNote: client.note?.substring(0, 100),
      newNote: updatedNote.substring(0, 100),
    });

    // 3. Aktualizuj note w Fakturowni
    const fakturowniaToken = process.env.FAKTUROWNIA_API_TOKEN;
    const fakturowniaAccount = process.env.FAKTUROWNIA_ACCOUNT;

    if (!fakturowniaToken || !fakturowniaAccount) {
      return NextResponse.json(
        { success: false, error: 'Fakturownia API not configured' },
        { status: 500 }
      );
    }

    const fakturowniaUrl = `https://${fakturowniaAccount}.fakturownia.pl/clients/${clientId}.json?api_token=${fakturowniaToken}`;

    const fakturowniaResponse = await fetch(fakturowniaUrl, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        client: {
          note: updatedNote,
        },
      }),
    });

    if (!fakturowniaResponse.ok) {
      const errorText = await fakturowniaResponse.text();
      console.error('[Windykacja] Fakturownia API error:', errorText);
      return NextResponse.json(
        { success: false, error: 'Failed to update Fakturownia' },
        { status: 500 }
      );
    }

    console.log(`[Windykacja] ✓ Fakturownia updated`);

    // 4. Zaktualizuj note w Supabase
    const { error: updateError } = await supabase()
      .from('clients')
      .update({
        note: updatedNote,
        updated_at: new Date().toISOString(),
      })
      .eq('id', clientId);

    if (updateError) {
      console.error('[Windykacja] Error updating Supabase:', updateError);
      return NextResponse.json(
        { success: false, error: 'Failed to update database' },
        { status: 500 }
      );
    }

    console.log(`[Windykacja] ✓ Client ${clientId} updated: windykacja_enabled=${windykacja_enabled}`);

    return NextResponse.json({
      success: true,
      data: {
        client_id: clientId,
        windykacja_enabled,
        note: updatedNote,
      },
    });
  } catch (error: any) {
    console.error('[Windykacja] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to update windykacja' },
      { status: 500 }
    );
  }
}
