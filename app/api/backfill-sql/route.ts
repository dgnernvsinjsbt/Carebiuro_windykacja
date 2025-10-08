import { NextRequest, NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';

/**
 * POST /api/backfill-sql
 *
 * Fast backfill using SQL function instead of row-by-row updates
 * Parses [FISCAL_SYNC] tags and updates has_third_reminder for ALL invoices
 */
// Force dynamic rendering - don't evaluate at build time
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  try {
    console.log('[Backfill SQL] Starting SQL-based backfill...');
    const startTime = Date.now();

    // Use SQL to update all invoices at once
    // This parses the comment field and checks for EMAIL_3/SMS_3/WHATSAPP_3 = true
    const { error } = await supabaseAdmin().rpc('update_has_third_reminder');

    if (error) {
      console.error('[Backfill SQL] Error:', error);
      return NextResponse.json(
        {
          success: false,
          error: error.message || 'SQL backfill failed',
        },
        { status: 500 }
      );
    }

    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
    console.log(`[Backfill SQL] ✓ Complete in ${duration}s`);

    return NextResponse.json({
      success: true,
      data: {
        duration_seconds: parseFloat(duration),
      },
    });
  } catch (error: any) {
    console.error('[Backfill SQL] Error:', error);
    return NextResponse.json(
      {
        success: false,
        error: error.message || 'Backfill failed',
      },
      { status: 500 }
    );
  }
}
