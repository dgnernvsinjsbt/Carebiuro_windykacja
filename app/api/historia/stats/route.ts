import { NextRequest, NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';
import { parseFiscalSync } from '@/lib/fiscal-sync-parser';

/**
 * GET /api/historia/stats
 * Get statistics summary for message history from FISCAL_SYNC flags
 *
 * Query params:
 * - startDate: ISO date string (e.g., 2025-10-01)
 * - endDate: ISO date string
 * - days: number of days to look back (default 30)
 */
// Force dynamic rendering - don't evaluate at build time
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);

    const startDate = searchParams.get('startDate') || undefined;
    const endDate = searchParams.get('endDate') || undefined;
    const days = searchParams.get('days') ? Number(searchParams.get('days')) : 30;

    console.log('[Historia Stats] Fetching stats with filters:', { startDate, endDate, days });

    // Fetch invoices with internal_note (contains FISCAL_SYNC from Fakturownia)
    let query = supabaseAdmin()
      .from('invoices')
      .select('id, internal_note')
      .not('internal_note', 'is', null);

    const { data: invoices, error } = await query;

    if (error) throw error;

    console.log(`[Historia Stats] Found ${invoices?.length || 0} invoices with internal_note`);

    // Extract all messages from FISCAL_SYNC flags
    const allMessages: any[] = [];
    const dailyMap: Record<string, any> = {};

    for (const invoice of invoices || []) {
      const fiscalSync = parseFiscalSync(invoice.internal_note);
      if (!fiscalSync) continue;

      // Check each message type and level
      const messageTypes = [
        { type: 'email', levels: [1, 2, 3] },
        { type: 'sms', levels: [1, 2, 3] },
        { type: 'whatsapp', levels: [1, 2, 3] },
      ];

      for (const { type, levels } of messageTypes) {
        for (const level of levels) {
          const flagKey = `${type.toUpperCase()}_${level}`;
          const dateKey = `${type.toUpperCase()}_${level}_DATE`;

          const wasSent = (fiscalSync as any)[flagKey];
          const sentDate = (fiscalSync as any)[dateKey];

          if (wasSent && sentDate) {
            // Extract date part from ISO timestamp
            const sentDateOnly = sentDate.split('T')[0]; // YYYY-MM-DD

            // Filter by date range if specified
            if (startDate && sentDateOnly < startDate) continue;
            if (endDate && sentDateOnly > endDate) continue;

            // Add to all messages for summary stats
            allMessages.push({
              type,
              level,
              sent_at: sentDate,
              date: sentDateOnly,
            });

            // Add to daily stats
            if (!dailyMap[sentDateOnly]) {
              dailyMap[sentDateOnly] = {
                date: sentDateOnly,
                total: 0,
                email: 0,
                sms: 0,
                whatsapp: 0,
                sent: 0,
                failed: 0,
              };
            }

            dailyMap[sentDateOnly].total++;
            dailyMap[sentDateOnly][type]++;
            dailyMap[sentDateOnly].sent++; // All messages from FISCAL_SYNC are sent
          }
        }
      }
    }

    // Calculate summary stats
    const stats = {
      total: allMessages.length,
      byType: {
        email: allMessages.filter((m) => m.type === 'email').length,
        sms: allMessages.filter((m) => m.type === 'sms').length,
        whatsapp: allMessages.filter((m) => m.type === 'whatsapp').length,
      },
      byStatus: {
        sent: allMessages.length, // All from FISCAL_SYNC are sent
        failed: 0,
        pending: 0,
      },
    };

    // Convert daily map to array and sort by date
    const dailyStats = Object.values(dailyMap).sort((a: any, b: any) =>
      a.date.localeCompare(b.date)
    );

    console.log('[Historia Stats] Summary:', stats);
    console.log('[Historia Stats] Daily entries:', dailyStats.length);

    return NextResponse.json({
      success: true,
      data: {
        summary: stats,
        daily: dailyStats,
      },
    });
  } catch (error: any) {
    console.error('[Historia Stats] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to fetch stats' },
      { status: 500 }
    );
  }
}
