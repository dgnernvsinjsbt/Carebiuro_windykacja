import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { parseFiscalSync } from '@/lib/fiscal-sync-parser';

/**
 * POST /api/historia/backfill
 * Backfill message_history from invoices' internal_note (FISCAL_SYNC)
 * This migrates historical data from the old system to the new message_history table
 */
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';
export const maxDuration = 300; // 5 minutes max

function getSupabaseAdmin() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}

/**
 * Parse legacy format internal_note (e.g., "email1, sms1" or ", sms1")
 */
function parseLegacyFormat(note: string | null): Record<string, boolean> | null {
  if (!note) return null;
  if (note.includes('[FISCAL_SYNC]')) return null;

  const noteLower = note.toLowerCase();
  const flags: Record<string, boolean> = {};

  if (noteLower.includes('email1') || noteLower.includes('e1')) flags.EMAIL_1 = true;
  if (noteLower.includes('email2') || noteLower.includes('e2')) flags.EMAIL_2 = true;
  if (noteLower.includes('email3') || noteLower.includes('e3')) flags.EMAIL_3 = true;
  if (noteLower.includes('sms1') || noteLower.includes('s1')) flags.SMS_1 = true;
  if (noteLower.includes('sms2') || noteLower.includes('s2')) flags.SMS_2 = true;
  if (noteLower.includes('sms3') || noteLower.includes('s3')) flags.SMS_3 = true;

  return Object.keys(flags).length > 0 ? flags : null;
}

export async function POST(request: NextRequest) {
  try {
    const supabase = getSupabaseAdmin();

    console.log('[Backfill] Starting backfill from internal_note to message_history...');

    // Get all invoices with internal_note
    const { data: invoices, error: fetchError } = await supabase
      .from('invoices')
      .select('id, number, client_id, buyer_name, internal_note, total, currency, updated_at, issue_date')
      .not('internal_note', 'is', null)
      .order('id', { ascending: false });

    if (fetchError) throw fetchError;

    console.log(`[Backfill] Found ${invoices?.length || 0} invoices with internal_note`);

    const messagesToInsert: any[] = [];
    let fiscalSyncCount = 0;
    let legacyCount = 0;
    let skippedCount = 0;

    for (const invoice of invoices || []) {
      if (!invoice.client_id) {
        skippedCount++;
        continue;
      }

      // Try FISCAL_SYNC format first
      const fiscalSync = parseFiscalSync(invoice.internal_note);

      // Try legacy format if no FISCAL_SYNC
      const legacyFlags = !fiscalSync ? parseLegacyFormat(invoice.internal_note) : null;

      if (!fiscalSync && !legacyFlags) {
        skippedCount++;
        continue;
      }

      // Fallback date for legacy format
      const fallbackDate = invoice.updated_at || invoice.issue_date || new Date().toISOString();

      if (fiscalSync) {
        fiscalSyncCount++;
      } else {
        legacyCount++;
      }

      // Extract messages from flags
      const messageTypes = [
        { type: 'email', levels: [1, 2, 3] },
        { type: 'sms', levels: [1, 2, 3] },
        { type: 'whatsapp', levels: [1, 2, 3] },
      ];

      for (const { type, levels } of messageTypes) {
        for (const level of levels) {
          const flagKey = `${type.toUpperCase()}_${level}`;
          const dateKey = `${type.toUpperCase()}_${level}_DATE`;

          let wasSent = false;
          let sentDate: string | null = null;

          if (fiscalSync) {
            wasSent = (fiscalSync as any)[flagKey] === true;
            sentDate = (fiscalSync as any)[dateKey] || null;
          } else if (legacyFlags) {
            wasSent = (legacyFlags as any)[flagKey] === true;
            sentDate = null;
          }

          if (wasSent) {
            const effectiveDate = sentDate || fallbackDate;

            messagesToInsert.push({
              client_id: invoice.client_id,
              invoice_id: invoice.id,
              invoice_number: invoice.number || `INV-${invoice.id}`,
              client_name: invoice.buyer_name || 'Unknown',
              message_type: type,
              level: level,
              status: 'sent',
              sent_at: effectiveDate,
              sent_by: level === 1 ? 'system' : 'manual',
              is_auto_initial: level === 1,
              invoice_total: invoice.total,
              invoice_currency: invoice.currency || 'EUR',
            });
          }
        }
      }
    }

    console.log(`[Backfill] Prepared ${messagesToInsert.length} messages to insert`);
    console.log(`[Backfill] Sources: ${fiscalSyncCount} FISCAL_SYNC, ${legacyCount} legacy, ${skippedCount} skipped`);

    if (messagesToInsert.length === 0) {
      return NextResponse.json({
        success: true,
        message: 'No messages to backfill',
        stats: {
          invoices_processed: invoices?.length || 0,
          fiscal_sync_count: fiscalSyncCount,
          legacy_count: legacyCount,
          skipped_count: skippedCount,
          messages_inserted: 0,
        },
      });
    }

    // Check for existing messages to avoid duplicates
    const { data: existingMessages } = await supabase
      .from('message_history')
      .select('invoice_id, message_type, level');

    const existingSet = new Set(
      (existingMessages || []).map(m => `${m.invoice_id}-${m.message_type}-${m.level}`)
    );

    // Filter out duplicates
    const newMessages = messagesToInsert.filter(m =>
      !existingSet.has(`${m.invoice_id}-${m.message_type}-${m.level}`)
    );

    console.log(`[Backfill] After dedup: ${newMessages.length} new messages (${messagesToInsert.length - newMessages.length} duplicates skipped)`);

    if (newMessages.length === 0) {
      return NextResponse.json({
        success: true,
        message: 'All messages already exist in message_history',
        stats: {
          invoices_processed: invoices?.length || 0,
          fiscal_sync_count: fiscalSyncCount,
          legacy_count: legacyCount,
          skipped_count: skippedCount,
          messages_prepared: messagesToInsert.length,
          duplicates_skipped: messagesToInsert.length,
          messages_inserted: 0,
        },
      });
    }

    // Insert in batches of 100
    const batchSize = 100;
    let insertedCount = 0;
    let errorCount = 0;

    for (let i = 0; i < newMessages.length; i += batchSize) {
      const batch = newMessages.slice(i, i + batchSize);

      const { error: insertError } = await supabase
        .from('message_history')
        .insert(batch);

      if (insertError) {
        console.error(`[Backfill] Batch ${i / batchSize + 1} error:`, insertError);
        errorCount += batch.length;
      } else {
        insertedCount += batch.length;
      }
    }

    console.log(`[Backfill] Completed: ${insertedCount} inserted, ${errorCount} errors`);

    return NextResponse.json({
      success: true,
      message: `Backfill completed: ${insertedCount} messages inserted`,
      stats: {
        invoices_processed: invoices?.length || 0,
        fiscal_sync_count: fiscalSyncCount,
        legacy_count: legacyCount,
        skipped_count: skippedCount,
        messages_prepared: messagesToInsert.length,
        duplicates_skipped: messagesToInsert.length - newMessages.length,
        messages_inserted: insertedCount,
        errors: errorCount,
      },
    });

  } catch (error: any) {
    console.error('[Backfill] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Backfill failed' },
      { status: 500 }
    );
  }
}

// GET handler for checking status
export async function GET() {
  try {
    const supabase = getSupabaseAdmin();

    const [invoicesResult, messagesResult] = await Promise.all([
      supabase.from('invoices').select('id', { count: 'exact' }).not('internal_note', 'is', null),
      supabase.from('message_history').select('id', { count: 'exact' }),
    ]);

    return NextResponse.json({
      success: true,
      status: {
        invoices_with_notes: invoicesResult.count || 0,
        messages_in_history: messagesResult.count || 0,
      },
      action: 'POST to this endpoint to run backfill',
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
