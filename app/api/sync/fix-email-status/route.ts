import { NextRequest, NextResponse } from 'next/server';
import { parseFiscalSync, updateFiscalSync } from '@/lib/fiscal-sync-parser';
import { supabase, invoicesDb } from '@/lib/supabase';
import { fakturowniaApi } from '@/lib/fakturownia';

/**
 * Post-sync consistency check: Fix EMAIL_1 flag for invoices sent by Fakturownia
 *
 * This endpoint finds invoices where:
 * - email_status = 'sent' (Fakturownia already sent the email)
 * - EMAIL_1 is NOT set in [FISCAL_SYNC]
 *
 * And sets EMAIL_1=TRUE with the sent_time date from Fakturownia.
 *
 * This ensures our system doesn't send duplicate E1 emails for invoices
 * that were already sent through Fakturownia.
 *
 * Called by nightly-sync workflow after full-sync completes.
 */
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  try {
    // Security: Only allow from GitHub Actions or with valid cron secret
    const isGitHubAction = request.headers.get('x-github-action') === 'true';
    const cronSecret = request.headers.get('X-Cron-Secret');
    const expectedSecret = process.env.CRON_SECRET;

    if (!isGitHubAction && cronSecret !== expectedSecret) {
      console.error('[FixEmailStatus] Unauthorized request');
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    console.log('[FixEmailStatus] Starting post-sync email status consistency check...');

    // Find all invoices with email_status='sent'
    const { data: sentInvoices, error } = await supabase()
      .from('invoices')
      .select('id, number, internal_note, email_status, sent_time')
      .eq('email_status', 'sent');

    if (error) {
      console.error('[FixEmailStatus] Error fetching invoices:', error);
      return NextResponse.json({ error: 'Failed to fetch invoices' }, { status: 500 });
    }

    if (!sentInvoices || sentInvoices.length === 0) {
      console.log('[FixEmailStatus] No invoices with email_status=sent found');
      return NextResponse.json({
        success: true,
        message: 'No invoices to fix',
        fixed: 0,
      });
    }

    console.log(`[FixEmailStatus] Found ${sentInvoices.length} invoices with email_status=sent`);

    let fixedCount = 0;
    let skippedCount = 0;
    let errorCount = 0;
    const results: any[] = [];

    for (const invoice of sentInvoices) {
      const fiscalSync = parseFiscalSync(invoice.internal_note);

      // Check if EMAIL_1 is already set
      if (fiscalSync?.EMAIL_1 === true) {
        skippedCount++;
        continue; // Already marked, skip
      }

      // EMAIL_1 not set but email was sent by Fakturownia - need to fix!
      console.log(`[FixEmailStatus] Fixing invoice ${invoice.id} (${invoice.number}) - EMAIL_1 not set but email_status=sent`);

      try {
        // Use sent_time from Fakturownia as the EMAIL_1_DATE
        const emailDate = invoice.sent_time || new Date().toISOString();

        // Update using our standard updateFiscalSync function
        // This ensures the [FISCAL_SYNC] block is properly formatted
        const updatedInternalNote = updateFiscalSync(
          invoice.internal_note,
          'EMAIL_1',
          true,
          emailDate
        );

        // Update in Fakturownia first
        await fakturowniaApi.updateInvoiceComment(invoice.id, updatedInternalNote);

        // Update in Supabase
        await invoicesDb.updateComment(invoice.id, updatedInternalNote);

        fixedCount++;
        results.push({
          invoice_id: invoice.id,
          invoice_number: invoice.number,
          email_date: emailDate,
          status: 'fixed',
        });

        console.log(`[FixEmailStatus] ✓ Fixed invoice ${invoice.id} - set EMAIL_1=TRUE with date ${emailDate}`);

        // Small delay to avoid rate limiting
        await new Promise(resolve => setTimeout(resolve, 200));

      } catch (err: any) {
        errorCount++;
        results.push({
          invoice_id: invoice.id,
          invoice_number: invoice.number,
          status: 'error',
          error: err.message,
        });
        console.error(`[FixEmailStatus] ✗ Failed to fix invoice ${invoice.id}:`, err.message);
      }
    }

    const summary = `Fixed ${fixedCount} invoices, skipped ${skippedCount} (already set), ${errorCount} errors`;
    console.log(`[FixEmailStatus] ${summary}`);

    return NextResponse.json({
      success: true,
      message: summary,
      fixed: fixedCount,
      skipped: skippedCount,
      errors: errorCount,
      total_checked: sentInvoices.length,
      results: results.length <= 50 ? results : results.slice(0, 50), // Limit response size
    });

  } catch (error: any) {
    console.error('[FixEmailStatus] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}

// Also support GET for manual testing
export async function GET(request: NextRequest) {
  return POST(request);
}
