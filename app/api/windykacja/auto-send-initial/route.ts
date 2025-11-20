import { NextRequest, NextResponse } from 'next/server';
import { parseFiscalSync } from '@/lib/fiscal-sync-parser';
import { supabase } from '@/lib/supabase';

/**
 * Auto-send E1, S1 (initial informational messages) for newly issued invoices
 *
 * These are NOT debt collection messages - they are informational notifications
 * about invoice issuance, so they bypass STOP and WINDYKACJA flags.
 *
 * WhatsApp (W1) is disabled - not configured in system.
 *
 * Eligible invoices:
 * - Issued in last 3 days (based on issue_date)
 * - Not paid (status != 'paid')
 * - Not canceled (kind != 'canceled')
 * - E1 or S1 not sent yet (respective flag is false in [FISCAL_SYNC])
 * - Has unpaid balance (total - paid > 0)
 *
 * Data source: Supabase (already synced by /api/sync full sync at midnight)
 * This endpoint is called by Vercel Cron at 8:00 AM daily (vercel.json)
 */
// Force dynamic rendering - don't evaluate at build time
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  try {
    // Security: Verify cron secret
    const cronSecret = request.headers.get('X-Cron-Secret');
    const expectedSecret = process.env.CRON_SECRET;

    if (!expectedSecret) {
      console.warn('[AutoSendInitial] CRON_SECRET not configured - endpoint is unprotected!');
    } else if (cronSecret !== expectedSecret) {
      console.error('[AutoSendInitial] Unauthorized request - invalid cron secret');
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    console.log('[AutoSendInitial] Starting auto-send for E1/S1/W1...');

    // Calculate date 3 days ago
    const threeDaysAgo = new Date();
    threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);
    threeDaysAgo.setHours(0, 0, 0, 0);
    const threeDaysAgoIso = threeDaysAgo.toISOString();

    console.log(`[AutoSendInitial] Looking for invoices issued after ${threeDaysAgoIso}`);

    // Fetch recent invoices from Supabase (already synced by full sync at midnight)
    console.log('[AutoSendInitial] Fetching invoices from Supabase...');

    const { data: allInvoices, error } = await supabase()
      .from('invoices')
      .select('*')
      .gte('issue_date', threeDaysAgoIso)
      .order('issue_date', { ascending: false });

    if (error) {
      console.error('[AutoSendInitial] Error fetching invoices:', error);
      return NextResponse.json(
        { success: false, error: 'Failed to fetch invoices from database' },
        { status: 500 }
      );
    }

    if (!allInvoices || allInvoices.length === 0) {
      console.log('[AutoSendInitial] No invoices found');
      return NextResponse.json({
        success: true,
        message: 'No invoices to process',
        sent: { email: 0, sms: 0, whatsapp: 0 },
      });
    }

    console.log(`[AutoSendInitial] Found ${allInvoices.length} total invoices from last 3 days, filtering...`);

    // Filter invoices eligible for E1/S1/W1 auto-send
    const eligibleInvoices = allInvoices.filter((invoice) => {
      // Skip paid invoices
      if (invoice.status === 'paid') {
        return false;
      }

      // Skip canceled invoices
      if (invoice.kind === 'canceled') {
        return false;
      }

      // Skip if no unpaid balance (using 'total' and 'paid' from Supabase schema)
      const total = invoice.total || 0;
      const paid = invoice.paid || 0;
      const balance = total - paid;
      if (balance <= 0) {
        return false;
      }

      // Issue date already filtered by SQL query (.gte('issue_date', threeDaysAgoIso))
      // But we keep this check for safety
      if (!invoice.issue_date) {
        return false;
      }

      // Parse fiscal sync data from internal_note
      const fiscalSync = parseFiscalSync(invoice.internal_note);

      // Check if any of E1, S1 need to be sent
      // We'll send them if they haven't been sent yet
      // W1 (WhatsApp) disabled - not configured in system
      const needsE1 = !fiscalSync?.EMAIL_1;
      const needsS1 = !fiscalSync?.SMS_1;

      if (!needsE1 && !needsS1) {
        return false; // All initial messages already sent
      }

      return true;
    });

    console.log(`[AutoSendInitial] Found ${eligibleInvoices.length} eligible invoices out of ${allInvoices.length}`);

    if (eligibleInvoices.length === 0) {
      return NextResponse.json({
        success: true,
        message: 'No eligible invoices for initial messages',
        sent: { email: 0, sms: 0, whatsapp: 0 },
      });
    }

    // Send E1/S1/W1 for each eligible invoice
    const results: any[] = [];
    let emailCount = 0;
    let smsCount = 0;
    let whatsappCount = 0;
    let failureCount = 0;

    for (const invoice of eligibleInvoices) {
      const fiscalSync = parseFiscalSync(invoice.internal_note);
      const invoiceResults: any = {
        invoice_id: invoice.id,
        invoice_number: invoice.number || `INV-${invoice.id}`,
        sent: [],
        failed: [],
      };

      // Send E1 if needed
      if (!fiscalSync?.EMAIL_1) {
        try {
          console.log(`[AutoSendInitial] Sending E1 for invoice ${invoice.id} (${invoice.number || 'N/A'})`);

          const apiUrl = process.env.NODE_ENV === 'development'
            ? 'http://localhost:3000/api/reminder'
            : `${request.nextUrl.origin}/api/reminder`;

          const response = await fetch(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              invoice_id: invoice.id,
              type: 'email',
              level: '1',
            }),
          });

          const data = await response.json();

          if (data.success) {
            emailCount++;
            invoiceResults.sent.push('E1');
            console.log(`[AutoSendInitial] ✓ E1 sent for invoice ${invoice.id}`);
          } else {
            failureCount++;
            invoiceResults.failed.push({ type: 'E1', error: data.error });
            console.log(`[AutoSendInitial] ✗ Failed to send E1: ${data.error}`);
          }

          // Small delay between requests
          await new Promise(resolve => setTimeout(resolve, 500));
        } catch (error: any) {
          failureCount++;
          invoiceResults.failed.push({ type: 'E1', error: error.message });
          console.error(`[AutoSendInitial] Error sending E1:`, error);
        }
      }

      // Send S1 if needed
      if (!fiscalSync?.SMS_1) {
        try {
          console.log(`[AutoSendInitial] Sending S1 for invoice ${invoice.id} (${invoice.number || 'N/A'})`);

          const apiUrl = process.env.NODE_ENV === 'development'
            ? 'http://localhost:3000/api/reminder'
            : `${request.nextUrl.origin}/api/reminder`;

          const response = await fetch(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              invoice_id: invoice.id,
              type: 'sms',
              level: '1',
            }),
          });

          const data = await response.json();

          if (data.success) {
            smsCount++;
            invoiceResults.sent.push('S1');
            console.log(`[AutoSendInitial] ✓ S1 sent for invoice ${invoice.id}`);
          } else {
            failureCount++;
            invoiceResults.failed.push({ type: 'S1', error: data.error });
            console.log(`[AutoSendInitial] ✗ Failed to send S1: ${data.error}`);
          }

          // Small delay between requests
          await new Promise(resolve => setTimeout(resolve, 500));
        } catch (error: any) {
          failureCount++;
          invoiceResults.failed.push({ type: 'S1', error: error.message });
          console.error(`[AutoSendInitial] Error sending S1:`, error);
        }
      }

      // W1 (WhatsApp) disabled - not configured in system
      // Skip WhatsApp sending entirely

      results.push(invoiceResults);
    }

    const totalSent = emailCount + smsCount;
    console.log(`[AutoSendInitial] Completed: ${totalSent} total sent (E1: ${emailCount}, S1: ${smsCount}), ${failureCount} failed`);

    return NextResponse.json({
      success: true,
      message: `Auto-send completed: ${totalSent} messages sent, ${failureCount} failed`,
      sent: {
        email: emailCount,
        sms: smsCount,
        whatsapp: whatsappCount,
        total: totalSent,
      },
      failed: failureCount,
      results,
    });

  } catch (error: any) {
    console.error('[AutoSendInitial] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}
