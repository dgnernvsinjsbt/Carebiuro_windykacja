import { NextRequest, NextResponse } from 'next/server';
import { invoicesDb, messageHistoryDb, prepareMessageHistoryEntry } from '@/lib/supabase';
import { parseFiscalSync } from '@/lib/fiscal-sync-parser';
import { supabase, supabaseAdmin } from '@/lib/supabase';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

/**
 * POST /api/historia/backfill
 * Backfill message_history from FISCAL_SYNC flags in invoice comments
 *
 * Reads all invoices with FISCAL_SYNC data and creates message_history entries
 * for SMS/Email/WhatsApp that were already sent (based on flags and dates)
 *
 * Query params:
 * - dryRun: boolean (default: true) - if true, only count what would be added
 * - clientId: number (optional) - only backfill for specific client
 */
export async function POST(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const dryRun = searchParams.get('dryRun') !== 'false'; // default true for safety
    const clientId = searchParams.get('clientId') ? Number(searchParams.get('clientId')) : undefined;

    console.log('[HistoriaBackfill] Starting backfill...', { dryRun, clientId });

    // Get all invoices (or for specific client)
    let invoices;
    if (clientId) {
      invoices = await invoicesDb.getByClientId(clientId);
    } else {
      // Get all invoices with comments
      const { data, error } = await supabase()
        .from('invoices')
        .select('*')
        .not('comment', 'is', null)
        .order('id', { ascending: true });

      if (error) throw error;
      invoices = data || [];
    }

    console.log(`[HistoriaBackfill] Found ${invoices.length} invoices to process`);

    const toInsert: any[] = [];
    let processedCount = 0;
    let skippedCount = 0;

    for (const invoice of invoices) {
      // Skip if no client_id
      if (!invoice.client_id) {
        skippedCount++;
        continue;
      }

      // Parse FISCAL_SYNC from comment
      const fiscalSync = parseFiscalSync(invoice.comment);
      if (!fiscalSync) {
        skippedCount++;
        continue;
      }

      // Check each message type and level
      const messageTypes = [
        { type: 'email' as const, levels: [1, 2, 3] },
        { type: 'sms' as const, levels: [1, 2, 3] },
        { type: 'whatsapp' as const, levels: [1, 2, 3] },
      ];

      for (const { type, levels } of messageTypes) {
        for (const level of levels) {
          const flagKey = `${type.toUpperCase()}_${level}` as keyof typeof fiscalSync;
          const dateKey = `${type.toUpperCase()}_${level}_DATE` as keyof typeof fiscalSync;

          const wasSent = fiscalSync[flagKey];
          const sentDate = fiscalSync[dateKey];

          // If message was sent and we have a date, create history entry
          if (wasSent && sentDate) {
            try {
              const entry = prepareMessageHistoryEntry(
                invoice,
                type,
                level as 1 | 2 | 3,
                { sent_by: 'system', is_auto_initial: level === 1 }
              );

              // Override sent_at with the actual date from FISCAL_SYNC
              const entryWithDate = {
                ...entry,
                sent_at: sentDate,
              };

              toInsert.push(entryWithDate);
              processedCount++;
            } catch (err) {
              console.error(`[HistoriaBackfill] Error preparing entry for invoice ${invoice.id}:`, err);
            }
          }
        }
      }
    }

    console.log(`[HistoriaBackfill] Processed ${processedCount} messages, skipped ${skippedCount} invoices`);

    if (dryRun) {
      return NextResponse.json({
        success: true,
        dryRun: true,
        message: 'Dry run complete - no data was inserted',
        stats: {
          total_invoices: invoices.length,
          processed_messages: processedCount,
          skipped_invoices: skippedCount,
          sample: toInsert.slice(0, 5), // Show first 5 as preview
        },
      });
    }

    // Actually insert the data
    if (toInsert.length === 0) {
      return NextResponse.json({
        success: true,
        message: 'No messages to backfill',
        stats: { total_invoices: invoices.length, processed_messages: 0 },
      });
    }

    // Insert in batches of 100
    let insertedCount = 0;
    const batchSize = 100;
    for (let i = 0; i < toInsert.length; i += batchSize) {
      const batch = toInsert.slice(i, i + batchSize);
      const { error } = await supabaseAdmin()
        .from('message_history')
        .insert(batch);

      if (error) {
        console.error(`[HistoriaBackfill] Error inserting batch ${i / batchSize + 1}:`, error);
        throw error;
      }
      insertedCount += batch.length;
      console.log(`[HistoriaBackfill] Inserted batch ${i / batchSize + 1}: ${batch.length} messages`);
    }

    console.log(`[HistoriaBackfill] Complete! Inserted ${insertedCount} messages`);

    return NextResponse.json({
      success: true,
      dryRun: false,
      message: `Successfully backfilled ${insertedCount} messages`,
      stats: {
        total_invoices: invoices.length,
        processed_messages: processedCount,
        inserted_messages: insertedCount,
        skipped_invoices: skippedCount,
      },
    });
  } catch (error: any) {
    console.error('[HistoriaBackfill] Error:', error);
    return NextResponse.json(
      {
        success: false,
        error: error.message || 'Backfill failed',
        details: error.stack,
      },
      { status: 500 }
    );
  }
}
