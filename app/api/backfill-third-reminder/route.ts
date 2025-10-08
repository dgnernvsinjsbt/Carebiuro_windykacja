/**
 * API Endpoint: Backfill has_third_reminder
 *
 * POST /api/backfill-third-reminder
 *
 * Wypełnia kolumnę has_third_reminder dla wszystkich istniejących faktur.
 * Używane jednorazowo po dodaniu kolumny do bazy.
 */

import { NextRequest, NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';
import { hasThirdReminder } from '@/lib/list-polecony-logic';

// Force dynamic rendering - don't evaluate at build time
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  try {
    console.log('[BackfillThirdReminder] Starting backfill...');

    // Pobierz wszystkie faktury
    let allInvoices: any[] = [];
    let page = 0;
    const pageSize = 1000;

    while (true) {
      const { data, error } = await supabaseAdmin
        .from('invoices')
        .select('id, comment')
        .range(page * pageSize, (page + 1) * pageSize - 1);

      if (error || !data || data.length === 0) break;
      allInvoices = allInvoices.concat(data);
      console.log(`[BackfillThirdReminder] Fetched page ${page + 1}: ${data.length} invoices (total: ${allInvoices.length})`);

      if (data.length < pageSize) break;
      page++;
    }

    console.log(`[BackfillThirdReminder] Total invoices to process: ${allInvoices.length}`);

    // Przetworz w batch'ach po 100
    const batchSize = 100;
    let updated = 0;
    let skipped = 0;

    for (let i = 0; i < allInvoices.length; i += batchSize) {
      const batch = allInvoices.slice(i, i + batchSize);

      // Oblicz has_third_reminder dla każdej faktury
      const updates = batch.map((invoice) => {
        const hasThird = hasThirdReminder(invoice);

        return {
          id: invoice.id,
          has_third_reminder: hasThird,
        };
      });

      // Aktualizuj batch
      for (const update of updates) {
        const { error: updateError } = await supabaseAdmin
          .from('invoices')
          .update({ has_third_reminder: update.has_third_reminder })
          .eq('id', update.id);

        if (updateError) {
          console.error(`[BackfillThirdReminder] Error updating invoice ${update.id}:`, updateError);
        } else {
          if (update.has_third_reminder) {
            updated++;
          } else {
            skipped++;
          }
        }
      }

      console.log(`[BackfillThirdReminder] Processed batch ${Math.floor(i / batchSize) + 1}: ${updated} with third reminder, ${skipped} without`);
    }

    console.log(`[BackfillThirdReminder] Backfill complete: ${updated} invoices with third reminder, ${skipped} without`);

    return NextResponse.json({
      success: true,
      data: {
        total_processed: allInvoices.length,
        with_third_reminder: updated,
        without_third_reminder: skipped,
      },
    });
  } catch (error: any) {
    console.error('[BackfillThirdReminder] Error:', error);
    return NextResponse.json(
      {
        success: false,
        error: 'Backfill failed',
        details: error.message,
      },
      { status: 500 }
    );
  }
}
