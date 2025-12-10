import { NextRequest, NextResponse } from 'next/server';
import { parseFiscalSync, updateFiscalSync } from '@/lib/fiscal-sync-parser';
import { supabase, invoicesDb, commentsDb, messageHistoryDb, prepareMessageHistoryEntry } from '@/lib/supabase';
import { sendEmailReminder } from '@/lib/mailgun';
import { sendSmsReminder } from '@/lib/sms';
import { fakturowniaApi } from '@/lib/fakturownia';

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

      // Skip VAT invoices - they are always paid (issued only after proforma payment)
      if (invoice.kind === 'vat') {
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

    // BATCH PROCESSING: Limit to 10 invoices per execution to avoid Vercel timeout
    const BATCH_SIZE = 10;
    const invoicesToProcess = eligibleInvoices.slice(0, BATCH_SIZE);
    const remaining = eligibleInvoices.length - invoicesToProcess.length;

    if (remaining > 0) {
      console.log(`[AutoSendInitial] Processing first ${BATCH_SIZE} invoices, ${remaining} remaining for next run`);
    }

    // Send E1/S1/W1 for each eligible invoice
    const results: any[] = [];
    let emailCount = 0;
    let smsCount = 0;
    let whatsappCount = 0;
    let failureCount = 0;

    for (const invoice of invoicesToProcess) {
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

          // Prepare email data
          const emailData = {
            nazwa_klienta: invoice.buyer_name || 'Klient',
            numer_faktury: invoice.number || `#${invoice.id}`,
            kwota: ((invoice.total || 0) - (invoice.paid || 0)).toFixed(2),
            waluta: invoice.currency || 'EUR',
            termin: invoice.payment_to
              ? new Date(invoice.payment_to).toLocaleDateString('pl-PL')
              : 'brak',
          };

          // Send email directly
          const result = await sendEmailReminder(
            'EMAIL_1',
            invoice.buyer_email || 'brak@email.com',
            emailData,
            invoice.id
          );

          if (result.success) {
            // Update Fiscal Sync in Fakturownia
            const currentDate = new Date().toISOString();
            const updatedInternalNote = updateFiscalSync(
              invoice.internal_note,
              'EMAIL_1',
              true,
              currentDate
            );

            await fakturowniaApi.updateInvoiceComment(invoice.id, updatedInternalNote);
            await invoicesDb.updateComment(invoice.id, updatedInternalNote);

            // Log to comments
            await commentsDb.logAction(
              invoice.id,
              'Sent EMAIL reminder (level 1)',
              'local'
            );

            // Log to message history
            try {
              const historyEntry = prepareMessageHistoryEntry(
                invoice,
                'email',
                1,
                { sent_by: 'auto', is_auto_initial: true }
              );
              await messageHistoryDb.logMessage(historyEntry);
            } catch (historyErr) {
              console.error(`[AutoSendInitial] Failed to log E1 to history:`, historyErr);
              // Don't fail the whole operation
            }

            emailCount++;
            invoiceResults.sent.push('E1');
            console.log(`[AutoSendInitial] ✓ E1 sent for invoice ${invoice.id}`);
          } else {
            failureCount++;
            invoiceResults.failed.push({ type: 'E1', error: result.error });
            console.log(`[AutoSendInitial] ✗ Failed to send E1: ${result.error}`);
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

          if (!invoice.buyer_phone) {
            console.error(`[AutoSendInitial] ✗ No phone number for invoice ${invoice.id}`);
            failureCount++;
            invoiceResults.failed.push({ type: 'S1', error: 'Brak numeru telefonu' });
            continue;
          }

          // Prepare SMS data
          const smsData = {
            nazwa_klienta: invoice.buyer_name || 'Klient',
            numer_faktury: invoice.number || `#${invoice.id}`,
            kwota: ((invoice.total || 0) - (invoice.paid || 0)).toFixed(2),
            waluta: invoice.currency || 'EUR',
            termin: invoice.payment_to
              ? new Date(invoice.payment_to).toLocaleDateString('pl-PL')
              : 'brak',
          };

          // Send SMS directly
          const result = await sendSmsReminder(
            'REMINDER_1',
            invoice.buyer_phone,
            smsData
          );

          if (result.success) {
            // Update Fiscal Sync in Fakturownia
            const currentDate = new Date().toISOString();
            const updatedInternalNote = updateFiscalSync(
              invoice.internal_note,
              'SMS_1',
              true,
              currentDate
            );

            await fakturowniaApi.updateInvoiceComment(invoice.id, updatedInternalNote);
            await invoicesDb.updateComment(invoice.id, updatedInternalNote);

            // Log to comments
            await commentsDb.logAction(
              invoice.id,
              'Sent SMS reminder (level 1)',
              'local'
            );

            // Log to message history
            try {
              const historyEntry = prepareMessageHistoryEntry(
                invoice,
                'sms',
                1,
                { sent_by: 'auto', is_auto_initial: true }
              );
              await messageHistoryDb.logMessage(historyEntry);
            } catch (historyErr) {
              console.error(`[AutoSendInitial] Failed to log S1 to history:`, historyErr);
              // Don't fail the whole operation
            }

            smsCount++;
            invoiceResults.sent.push('S1');
            console.log(`[AutoSendInitial] ✓ S1 sent for invoice ${invoice.id}`);
          } else {
            failureCount++;
            invoiceResults.failed.push({ type: 'S1', error: result.error });
            console.log(`[AutoSendInitial] ✗ Failed to send S1: ${result.error}`);
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
    const summaryMessage = remaining > 0
      ? `Batch completed: ${totalSent} messages sent, ${failureCount} failed. ${remaining} invoices remaining for next run.`
      : `Auto-send completed: ${totalSent} messages sent, ${failureCount} failed`;

    console.log(`[AutoSendInitial] ${summaryMessage}`);

    return NextResponse.json({
      success: true,
      message: summaryMessage,
      sent: {
        email: emailCount,
        sms: smsCount,
        whatsapp: whatsappCount,
        total: totalSent,
      },
      failed: failureCount,
      processed: invoicesToProcess.length,
      remaining: remaining,
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

// Vercel Cron sends GET requests by default, so we need to handle them
export async function GET(request: NextRequest) {
  console.log('[AutoSendInitial] GET request received, forwarding to POST handler');
  return POST(request);
}
