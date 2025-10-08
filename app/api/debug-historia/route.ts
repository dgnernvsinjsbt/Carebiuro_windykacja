import { NextRequest, NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';
import { parseFiscalSync } from '@/lib/fiscal-sync-parser';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

/**
 * Debug endpoint to check FISCAL_SYNC flags in invoices
 */
export async function GET(request: NextRequest) {
  try {
    console.log('[Debug Historia] Fetching invoices...');

    // Fetch all invoices with comment (Fakturownia internal_note → Supabase comment)
    const { data: invoices, error } = await supabase()
      .from('invoices')
      .select('id, number, client_id, comment, buyer_name')
      .not('comment', 'is', null)
      .limit(10);

    if (error) {
      console.error('[Debug Historia] Error fetching invoices:', error);
      throw error;
    }

    console.log(`[Debug Historia] Found ${invoices?.length || 0} invoices with comment`);

    // Parse FISCAL_SYNC from each invoice
    const results = (invoices || []).map((invoice) => {
      const fiscalSync = parseFiscalSync(invoice.comment);

      // Extract SMS messages
      const smsMessages = [];
      for (let level = 1; level <= 3; level++) {
        const flagKey = `SMS_${level}`;
        const dateKey = `SMS_${level}_DATE`;

        if (fiscalSync && (fiscalSync as any)[flagKey]) {
          smsMessages.push({
            level,
            sent: (fiscalSync as any)[flagKey],
            date: (fiscalSync as any)[dateKey],
          });
        }
      }

      return {
        invoice_id: invoice.id,
        invoice_number: invoice.number,
        client_name: invoice.buyer_name,
        has_fiscal_sync: !!fiscalSync,
        fiscal_sync: fiscalSync,
        sms_messages: smsMessages,
        comment_preview: invoice.comment?.substring(0, 200),
      };
    });

    return NextResponse.json({
      success: true,
      total_invoices: invoices?.length || 0,
      invoices: results,
    });
  } catch (error: any) {
    console.error('[Debug Historia] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to debug historia' },
      { status: 500 }
    );
  }
}
