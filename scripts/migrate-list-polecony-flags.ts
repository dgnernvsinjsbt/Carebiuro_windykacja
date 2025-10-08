/**
 * Migration Script: Convert old LIST_POLECONY flags to new STATUS format
 *
 * Old format:
 * - [LIST_POLECONY]sent[/LIST_POLECONY]
 * - [LIST_POLECONY_IGNORED]true[/LIST_POLECONY_IGNORED]
 *
 * New format:
 * - [LIST_POLECONY_STATUS]sent[/LIST_POLECONY_STATUS]
 * - [LIST_POLECONY_STATUS]ignore[/LIST_POLECONY_STATUS]
 */

import { supabaseAdmin } from '../lib/supabase';

async function migrateListPoleconyFlags() {
  console.log('🔄 Starting LIST_POLECONY flag migration...\n');

  // MIGRATION 1: [LIST_POLECONY]sent → [LIST_POLECONY_STATUS]sent
  console.log('1️⃣ Migrating [LIST_POLECONY]sent to [LIST_POLECONY_STATUS]sent...');
  const { data: sentInvoices, error: sentError } = await supabaseAdmin()
    .from('invoices')
    .select('id, internal_note')
    .like('internal_note', '%[LIST_POLECONY]sent[/LIST_POLECONY]%');

  if (sentError) {
    console.error('❌ Error fetching sent invoices:', sentError);
    return;
  }

  console.log(`   Found ${sentInvoices?.length || 0} invoices with old sent format`);

  for (const invoice of sentInvoices || []) {
    let updatedNote = invoice.internal_note || '';

    // Replace old sent flag with new format
    updatedNote = updatedNote.replace(
      /\[LIST_POLECONY\]sent\[\/LIST_POLECONY\]/g,
      '[LIST_POLECONY_STATUS]sent[/LIST_POLECONY_STATUS]'
    );

    // Migrate date tag
    updatedNote = updatedNote.replace(
      /\[LIST_POLECONY_SENT_DATE\](.*?)\[\/LIST_POLECONY_SENT_DATE\]/g,
      '[LIST_POLECONY_STATUS_DATE]$1[/LIST_POLECONY_STATUS_DATE]'
    );

    const { error: updateError } = await supabaseAdmin()
      .from('invoices')
      .update({ internal_note: updatedNote })
      .eq('id', invoice.id);

    if (updateError) {
      console.error(`   ❌ Error updating invoice ${invoice.id}:`, updateError);
    } else {
      console.log(`   ✅ Migrated invoice ${invoice.id}`);
    }
  }

  // MIGRATION 2: [LIST_POLECONY_IGNORED]true → [LIST_POLECONY_STATUS]ignore
  console.log('\n2️⃣ Migrating [LIST_POLECONY_IGNORED]true to [LIST_POLECONY_STATUS]ignore...');
  const { data: ignoredInvoices, error: ignoredError } = await supabaseAdmin()
    .from('invoices')
    .select('id, internal_note')
    .like('internal_note', '%[LIST_POLECONY_IGNORED]true[/LIST_POLECONY_IGNORED]%');

  if (ignoredError) {
    console.error('❌ Error fetching ignored invoices:', ignoredError);
    return;
  }

  console.log(`   Found ${ignoredInvoices?.length || 0} invoices with old ignored format`);

  for (const invoice of ignoredInvoices || []) {
    let updatedNote = invoice.internal_note || '';

    // Remove old ignored flag
    updatedNote = updatedNote.replace(
      /\[LIST_POLECONY_IGNORED\]true\[\/LIST_POLECONY_IGNORED\]\n?/g,
      ''
    );

    // Add new ignore status
    updatedNote = `[LIST_POLECONY_STATUS]ignore[/LIST_POLECONY_STATUS]\n${updatedNote}`;

    // Migrate date tag
    updatedNote = updatedNote.replace(
      /\[LIST_POLECONY_IGNORED_DATE\](.*?)\[\/LIST_POLECONY_IGNORED_DATE\]/g,
      '[LIST_POLECONY_STATUS_DATE]$1[/LIST_POLECONY_STATUS_DATE]'
    );

    const { error: updateError } = await supabaseAdmin()
      .from('invoices')
      .update({ internal_note: updatedNote })
      .eq('id', invoice.id);

    if (updateError) {
      console.error(`   ❌ Error updating invoice ${invoice.id}:`, updateError);
    } else {
      console.log(`   ✅ Migrated invoice ${invoice.id}`);
    }
  }

  // MIGRATION 3: Also migrate client notes
  console.log('\n3️⃣ Migrating client notes...');
  const { data: clientsWithOldFlags, error: clientsError } = await supabaseAdmin()
    .from('clients')
    .select('id, note')
    .or('note.like.%[LIST_POLECONY]sent[/LIST_POLECONY]%,note.like.%[LIST_POLECONY_IGNORED]true[/LIST_POLECONY_IGNORED]%');

  if (clientsError) {
    console.error('❌ Error fetching clients:', clientsError);
    return;
  }

  console.log(`   Found ${clientsWithOldFlags?.length || 0} clients with old format`);

  for (const client of clientsWithOldFlags || []) {
    let updatedNote = client.note || '';

    // Replace sent flag
    updatedNote = updatedNote.replace(
      /\[LIST_POLECONY\]sent\[\/LIST_POLECONY\]/g,
      '[LIST_POLECONY_STATUS]sent[/LIST_POLECONY_STATUS]'
    );

    // Replace ignored flag
    updatedNote = updatedNote.replace(
      /\[LIST_POLECONY_IGNORED\]true\[\/LIST_POLECONY_IGNORED\]/g,
      '[LIST_POLECONY_STATUS]ignore[/LIST_POLECONY_STATUS]'
    );

    const { error: updateError } = await supabaseAdmin()
      .from('clients')
      .update({ note: updatedNote })
      .eq('id', client.id);

    if (updateError) {
      console.error(`   ❌ Error updating client ${client.id}:`, updateError);
    } else {
      console.log(`   ✅ Migrated client ${client.id}`);
    }
  }

  console.log('\n✅ Migration complete!');
}

migrateListPoleconyFlags().catch(console.error);
