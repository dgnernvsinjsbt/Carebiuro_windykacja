import { NextResponse } from 'next/server';
import { fakturowniaApi } from '@/lib/fakturownia';
import { supabaseAdmin } from '@/lib/supabase';

export async function POST() {
  try {
    const clientId = 211779362;
    const newNote = '[WINDYKACJA]false[/WINDYKACJA] [LIST_POLECONY]true[/LIST_POLECONY] [LIST_POLECONY_IGNORED]true[/LIST_POLECONY_IGNORED]';

    console.log('[TEST] Aktualizuję klienta w Fakturowni...');
    console.log('[TEST] Note (jedna linia):', newNote);
    console.log('[TEST] Zawiera \\n?', newNote.includes('\n'));

    // 1. Aktualizuj w Fakturowni
    await fakturowniaApi.updateClient(clientId, { note: newNote });
    console.log('[TEST] ✓ Zaktualizowano w Fakturowni');

    // 2. Aktualizuj w Supabase
    const { error } = await supabaseAdmin
      .from('clients')
      .update({ note: newNote })
      .eq('id', clientId);

    if (error) {
      console.error('[TEST] ✗ Błąd Supabase:', error);
      throw error;
    }
    console.log('[TEST] ✓ Zaktualizowano w Supabase');

    return NextResponse.json({ success: true, note: newNote });
  } catch (error: any) {
    console.error('[TEST] Error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
