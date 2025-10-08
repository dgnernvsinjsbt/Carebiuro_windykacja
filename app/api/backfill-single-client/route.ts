/**
 * API Endpoint: Backfill has_third_reminder for single client
 *
 * POST /api/backfill-single-client
 * Body: { clientId: number }
 *
 * Wypełnia has_third_reminder tylko dla faktur jednego klienta (szybki test).
 */

import { NextRequest, NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';
import { hasThirdReminder } from '@/lib/list-polecony-logic';

export async function POST(request: NextRequest) {
  try {
    const { clientId } = await request.json();

    if (!clientId) {
      return NextResponse.json(
        { success: false, error: 'clientId is required' },
        { status: 400 }
      );
    }

    console.log(`[BackfillSingleClient] Starting backfill for client ${clientId}...`);

    // Pobierz faktury klienta
    const { data: invoices, error: fetchError } = await supabaseAdmin
      .from('invoices')
      .select('id, comment')
      .eq('client_id', clientId);

    if (fetchError) {
      console.error(`[BackfillSingleClient] Error fetching invoices:`, fetchError);
      return NextResponse.json(
        { success: false, error: 'Error fetching invoices' },
        { status: 500 }
      );
    }

    console.log(`[BackfillSingleClient] Found ${invoices?.length || 0} invoices`);

    let updated = 0;
    let withThirdReminder = 0;

    // Aktualizuj każdą fakturę
    for (const invoice of invoices || []) {
      const hasThird = hasThirdReminder(invoice as any);

      const { error: updateError } = await supabaseAdmin
        .from('invoices')
        .update({ has_third_reminder: hasThird })
        .eq('id', invoice.id);

      if (updateError) {
        console.error(`[BackfillSingleClient] Error updating invoice ${invoice.id}:`, updateError);
      } else {
        updated++;
        if (hasThird) {
          withThirdReminder++;
          console.log(`[BackfillSingleClient] ✓ Invoice ${invoice.id} has third reminder`);
        }
      }
    }

    console.log(`[BackfillSingleClient] Complete: ${updated} invoices updated, ${withThirdReminder} with third reminder`);

    return NextResponse.json({
      success: true,
      data: {
        client_id: clientId,
        total_invoices: invoices?.length || 0,
        updated: updated,
        with_third_reminder: withThirdReminder,
      },
    });
  } catch (error: any) {
    console.error('[BackfillSingleClient] Error:', error);
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
