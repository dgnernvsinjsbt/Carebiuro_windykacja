import { NextRequest, NextResponse } from 'next/server';
import { messageHistoryDb } from '@/lib/supabase';

/**
 * GET /api/historia/stats
 * Get statistics summary for message history
 *
 * Query params:
 * - startDate: ISO date string (e.g., 2025-10-01)
 * - endDate: ISO date string
 * - days: number of days to look back (default 30)
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);

    const startDate = searchParams.get('startDate') || undefined;
    const endDate = searchParams.get('endDate') || undefined;
    const days = searchParams.get('days') ? Number(searchParams.get('days')) : 30;

    console.log('[Historia Stats] Fetching stats with filters:', { startDate, endDate, days });

    // Get overall stats
    const stats = await messageHistoryDb.getStats({ startDate, endDate });

    // Get daily stats
    const dailyStats = await messageHistoryDb.getDailyStats(days);

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
