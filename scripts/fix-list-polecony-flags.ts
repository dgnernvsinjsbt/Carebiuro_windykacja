/**
 * Fix Script: Reset LIST_POLECONY flags to sent status
 *
 * Ustawia status=sent dla klienta 211779362 i jego faktur
 */

import { supabaseAdmin } from '../lib/supabase';

async function fixFlags() {
  console.log('🔧 Fixing LIST_POLECONY flags...\n');

  const clientId = 211779362;
  const invoiceIds = [423246698, 423246738, 423569184];
  const sentDate = '2025-09-01';

  const correctNote = `[LIST_POLECONY_STATUS]sent[/LIST_POLECONY_STATUS]
[LIST_POLECONY_STATUS_DATE]${sentDate}[/LIST_POLECONY_STATUS_DATE]`;

  // 1. Fix client
  console.log(`1️⃣ Updating client ${clientId}...`);
  const { error: clientError } = await supabaseAdmin()
    .from('clients')
    .update({ note: correctNote })
    .eq('id', clientId);

  if (clientError) {
    console.error('❌ Error updating client:', clientError);
  } else {
    console.log('✅ Client updated');
  }

  // 2. Fix invoices
  console.log(`\n2️⃣ Updating ${invoiceIds.length} invoices...`);
  for (const invoiceId of invoiceIds) {
    // Pobierz obecny internal_note
    const { data: invoice } = await supabaseAdmin()
      .from('invoices')
      .select('internal_note')
      .eq('id', invoiceId)
      .single();

    if (!invoice) {
      console.log(`⚠️  Invoice ${invoiceId} not found`);
      continue;
    }

    // Usuń stare flagi LIST_POLECONY i zostaw resztę (FISCAL_SYNC itd.)
    let cleanedNote = invoice.internal_note || '';

    // Usuń wszystkie stare i nowe flagi LIST_POLECONY
    cleanedNote = cleanedNote.replace(/\[LIST_POLECONY\](true|false|sent|ignore)\[\/LIST_POLECONY\]\n?/g, '');
    cleanedNote = cleanedNote.replace(/\[LIST_POLECONY_IGNORED\](true|false)\[\/LIST_POLECONY_IGNORED\]\n?/g, '');
    cleanedNote = cleanedNote.replace(/\[LIST_POLECONY_STATUS\](sent|ignore)\[\/LIST_POLECONY_STATUS\]\n?/g, '');
    cleanedNote = cleanedNote.replace(/\[LIST_POLECONY_SENT_DATE\].*?\[\/LIST_POLECONY_SENT_DATE\]\n?/g, '');
    cleanedNote = cleanedNote.replace(/\[LIST_POLECONY_IGNORED_DATE\].*?\[\/LIST_POLECONY_IGNORED_DATE\]\n?/g, '');
    cleanedNote = cleanedNote.replace(/\[LIST_POLECONY_STATUS_DATE\].*?\[\/LIST_POLECONY_STATUS_DATE\]\n?/g, '');

    // Dodaj nowe flagi na początku
    const updatedNote = `[LIST_POLECONY_STATUS]sent[/LIST_POLECONY_STATUS]
[LIST_POLECONY_STATUS_DATE]${sentDate}[/LIST_POLECONY_STATUS_DATE]
${cleanedNote}`;

    const { error: invoiceError } = await supabaseAdmin()
      .from('invoices')
      .update({
        internal_note: updatedNote,
        list_polecony: true,
        list_polecony_sent_date: sentDate,
        list_polecony_ignored: false,
        list_polecony_ignored_date: null
      })
      .eq('id', invoiceId);

    if (invoiceError) {
      console.error(`❌ Error updating invoice ${invoiceId}:`, invoiceError);
    } else {
      console.log(`✅ Invoice ${invoiceId} updated`);
    }
  }

  console.log('\n✅ All flags fixed!');
}

fixFlags().catch(console.error);
