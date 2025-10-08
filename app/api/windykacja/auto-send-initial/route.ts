import { NextRequest, NextResponse } from 'next/server';
import { fakturowniaApi } from '@/lib/fakturownia';
import { parseFiscalSync } from '@/lib/fiscal-sync-parser';
import { messageHistoryDb } from '@/lib/supabase';

/**
 * Auto-send E1, S1, W1 (initial informational messages) for newly issued invoices
 *
 * These are NOT debt collection messages - they are informational notifications
 * about invoice issuance, so they bypass STOP and WINDYKACJA flags.
 *
 * Eligible invoices:
 * - Issued in last 3 days (based on issue_date)
 * - Not paid (status != 'paid')
 * - Not canceled (kind != 'canceled')
 * - E1, S1, or W1 not sent yet (respective flag is false)
 * - Has unpaid balance (total - paid > 0)
 *
 * This endpoint should be called by a cron job at 8:00 AM daily
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

    console.log(`[AutoSendInitial] Looking for invoices issued after ${threeDaysAgo.toISOString()}`);

    // Fetch recent invoices from Fakturownia (last 7 days to be safe)
    // We'll filter down to 3 days in code
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    const dateFilter = sevenDaysAgo.toISOString().split('T')[0]; // YYYY-MM-DD

    console.log('[AutoSendInitial] Fetching invoices from Fakturownia...');

    // Fetch all invoices (we'll filter by date in code since Fakturownia API is limited)
    const allInvoices = await fakturowniaApi.getAllInvoices(500);

    if (!allInvoices || allInvoices.length === 0) {
      console.log('[AutoSendInitial] No invoices found');
      return NextResponse.json({
        success: true,
        message: 'No invoices to process',
        sent: { email: 0, sms: 0, whatsapp: 0 },
      });
    }

    console.log(`[AutoSendInitial] Found ${allInvoices.length} total invoices, filtering...`);

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

      // Skip if no unpaid balance
      const balance = parseFloat(invoice.price_gross || '0') - parseFloat(invoice.paid || '0');
      if (balance <= 0) {
        return false;
      }

      // Check if invoice was issued in last 3 days
      if (!invoice.issue_date) {
        return false;
      }

      const issueDate = new Date(invoice.issue_date);
      if (issueDate < threeDaysAgo) {
        return false;
      }

      // Parse fiscal sync data
      const fiscalSync = parseFiscalSync(invoice.internal_note);

      // Check if any of E1, S1, W1 need to be sent
      // We'll send them if they haven't been sent yet
      const needsE1 = !fiscalSync?.EMAIL_1;
      const needsS1 = !fiscalSync?.SMS_1;
      const needsW1 = !fiscalSync?.WHATSAPP_1;

      if (!needsE1 && !needsS1 && !needsW1) {
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
        invoice_number: invoice.number,
        sent: [],
        failed: [],
      };

      // Send E1 if needed
      if (!fiscalSync?.EMAIL_1) {
        try {
          console.log(`[AutoSendInitial] Sending E1 for invoice ${invoice.id} (${invoice.number})`);

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
          console.log(`[AutoSendInitial] Sending S1 for invoice ${invoice.id} (${invoice.number})`);

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

      // Send W1 if needed
      if (!fiscalSync?.WHATSAPP_1) {
        try {
          console.log(`[AutoSendInitial] Sending W1 for invoice ${invoice.id} (${invoice.number})`);

          const apiUrl = process.env.NODE_ENV === 'development'
            ? 'http://localhost:3000/api/reminder'
            : `${request.nextUrl.origin}/api/reminder`;

          const response = await fetch(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              invoice_id: invoice.id,
              type: 'whatsapp',
              level: '1',
            }),
          });

          const data = await response.json();

          if (data.success) {
            whatsappCount++;
            invoiceResults.sent.push('W1');
            console.log(`[AutoSendInitial] ✓ W1 sent for invoice ${invoice.id}`);
          } else {
            failureCount++;
            invoiceResults.failed.push({ type: 'W1', error: data.error });
            console.log(`[AutoSendInitial] ✗ Failed to send W1: ${data.error}`);
          }

          // Small delay between requests
          await new Promise(resolve => setTimeout(resolve, 500));
        } catch (error: any) {
          failureCount++;
          invoiceResults.failed.push({ type: 'W1', error: error.message });
          console.error(`[AutoSendInitial] Error sending W1:`, error);
        }
      }

      results.push(invoiceResults);
    }

    const totalSent = emailCount + smsCount + whatsappCount;
    console.log(`[AutoSendInitial] Completed: ${totalSent} total sent (E1: ${emailCount}, S1: ${smsCount}, W1: ${whatsappCount}), ${failureCount} failed`);

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
