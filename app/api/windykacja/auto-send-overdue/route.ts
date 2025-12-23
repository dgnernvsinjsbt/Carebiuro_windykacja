import { NextRequest, NextResponse } from 'next/server';
import { fakturowniaApi } from '@/lib/fakturownia';
import { parseFiscalSync, updateFiscalSync } from '@/lib/fiscal-sync-parser';
import { parseClientFlags } from '@/lib/client-flags-v2';
import { createClient } from '@supabase/supabase-js';
import { sendEmailReminder } from '@/lib/mailgun';
import { sendSmsReminder } from '@/lib/sms';
import { invoicesDb, commentsDb, messageHistoryDb, prepareMessageHistoryEntry } from '@/lib/supabase';

/**
 * Auto-send E1 + S1 for invoices 30+ days old for clients with windykacja enabled
 *
 * Runs daily at 7:15 AM via Vercel cron
 *
 * Logic:
 * 1. Find all clients with windykacja = true (from client note)
 * 2. For each client, fetch invoices from Fakturownia
 * 3. Filter qualifying invoices:
 *    - Open (not paid, not canceled)
 *    - Has unpaid balance
 *    - issue_date is 30+ days ago (NOT payment_to)
 *    - STOP flag is not set
 * 4. Send E1 if not already sent (check Fakturownia sent_time first, then our EMAIL_1)
 * 5. Send S1 if not already sent
 * 6. Update [FISCAL_SYNC] in Fakturownia
 */

// Force dynamic rendering
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

// Fetch all clients using pagination (Supabase has 1000 row limit per query)
async function fetchAllClients(supabase: any) {
  const allClients: any[] = [];
  const pageSize = 1000;
  let offset = 0;
  let hasMore = true;

  while (hasMore) {
    const { data, error } = await supabase
      .from('clients')
      .select('id, name, note')
      .range(offset, offset + pageSize - 1)
      .order('id', { ascending: true });

    if (error) throw error;

    if (data && data.length > 0) {
      allClients.push(...data);
      offset += pageSize;
      hasMore = data.length === pageSize;
    } else {
      hasMore = false;
    }
  }

  return allClients;
}

export async function POST(request: NextRequest) {
  try {
    console.log('[AutoSendOverdue] Starting daily windykacja run...');

    // Initialize Supabase
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );

    // 1. Get all clients from Supabase using pagination (Supabase has 1000 row limit)
    let allClients: any[];
    try {
      allClients = await fetchAllClients(supabase);
    } catch (error: any) {
      console.error('[AutoSendOverdue] Error fetching clients:', error);
      return NextResponse.json(
        { success: false, error: error.message },
        { status: 500 }
      );
    }

    if (allClients.length === 0) {
      console.log('[AutoSendOverdue] No clients found');
      return NextResponse.json({
        success: true,
        message: 'No clients found',
        sent: { email: 0, sms: 0, total: 0 },
        failed: 0,
      });
    }

    // Filter clients with windykacja enabled (from note field)
    const clients = allClients.filter(client => {
      const flags = parseClientFlags(client.note);
      return flags.windykacja === true;
    });

    if (clients.length === 0) {
      console.log('[AutoSendOverdue] No clients with windykacja enabled');
      return NextResponse.json({
        success: true,
        message: 'No clients with windykacja enabled',
        sent: { email: 0, sms: 0, total: 0 },
        failed: 0,
      });
    }

    console.log(`[AutoSendOverdue] Found ${clients.length} clients with windykacja enabled (out of ${allClients.length} total)`);

    // Calculate date threshold: 30 days ago
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    const thirtyDaysAgoIso = thirtyDaysAgo.toISOString().split('T')[0];

    // Get client IDs for windykacja clients
    const windykacjaClientIds = clients.map(c => c.id);

    // 2. Fetch ALL qualifying invoices from Supabase in ONE query (much faster than per-client Fakturownia calls)
    console.log(`[AutoSendOverdue] Fetching invoices from Supabase for ${windykacjaClientIds.length} clients...`);

    const { data: allInvoices, error: invoicesError } = await supabase
      .from('invoices')
      .select('*')
      .in('client_id', windykacjaClientIds)
      .neq('status', 'paid')
      .neq('kind', 'canceled')
      .neq('kind', 'vat')
      .lte('issue_date', thirtyDaysAgoIso)
      .order('issue_date', { ascending: false });

    if (invoicesError) {
      console.error('[AutoSendOverdue] Error fetching invoices:', invoicesError);
      return NextResponse.json(
        { success: false, error: invoicesError.message },
        { status: 500 }
      );
    }

    // Filter for unpaid balance and not STOP
    const qualifyingInvoices = (allInvoices || []).filter((invoice) => {
      const balance = (invoice.total || 0) - (invoice.paid || 0);
      if (balance <= 0) return false;

      const fiscalSync = parseFiscalSync(invoice.internal_note);
      if (fiscalSync?.STOP === true) {
        console.log(`[AutoSendOverdue] Skipping invoice ${invoice.id} - STOP enabled`);
        return false;
      }

      // Skip if E1 and S1 already sent
      const e1Sent = fiscalSync?.EMAIL_1 || invoice.email_status === 'sent';
      const s1Sent = fiscalSync?.SMS_1;
      if (e1Sent && s1Sent) return false;

      return true;
    });

    console.log(`[AutoSendOverdue] Found ${qualifyingInvoices.length} qualifying invoices (out of ${allInvoices?.length || 0} total for windykacja clients)`);

    if (qualifyingInvoices.length === 0) {
      return NextResponse.json({
        success: true,
        message: 'No qualifying invoices for overdue reminders',
        sent: { email: 0, sms: 0, total: 0 },
        failed: 0,
      });
    }

    // BATCH PROCESSING: Limit to 20 invoices per execution to avoid Vercel timeout
    const BATCH_SIZE = 20;
    const invoicesToProcess = qualifyingInvoices.slice(0, BATCH_SIZE);
    const remaining = qualifyingInvoices.length - invoicesToProcess.length;

    if (remaining > 0) {
      console.log(`[AutoSendOverdue] Processing first ${BATCH_SIZE} invoices, ${remaining} remaining for next run`);
    }

    let totalEmailSent = 0;
    let totalSmsSent = 0;
    let totalFailed = 0;
    const results: any[] = [];

    // Detailed failure tracking
    const failureBreakdown = {
      email_already_sent: 0,
      email_no_address: 0,
      email_send_failed: 0,
      sms_already_sent: 0,
      sms_no_phone: 0,
      sms_send_failed: 0,
      invoice_processing_error: 0,
      client_processing_error: 0,
    };

    // 3. Process each qualifying invoice
    for (const invoice of invoicesToProcess) {
          const invoiceNumber = invoice.number || `INV-${invoice.id}`;

          // ✅ RE-FETCH FRESH data from Supabase before checking flags
          console.log(`[AutoSendOverdue] Re-fetching invoice ${invoice.id} from Supabase for fresh flags...`);
          let freshInvoice;
          try {
            freshInvoice = await invoicesDb.getById(invoice.id);
            if (!freshInvoice) {
              console.error(`[AutoSendOverdue] Invoice ${invoice.id} not found in Supabase, skipping`);
              continue;
            }
          } catch (err) {
            console.error(`[AutoSendOverdue] Failed to re-fetch invoice ${invoice.id}, skipping:`, err);
            continue;
          }

          let fiscalSync = parseFiscalSync(freshInvoice.internal_note);

          let emailSent = false;
          let smsSent = false;

          try {
            // Send E1 if not already sent
            // Check both: our system (EMAIL_1) AND Fakturownia (email_status='sent')
            const e1AlreadySent = fiscalSync?.EMAIL_1 || freshInvoice.email_status === 'sent';

            if (e1AlreadySent) {
              console.log(`[AutoSendOverdue] ⊘ E1 already sent for invoice ${invoice.id} - skipping`);
              failureBreakdown.email_already_sent++;
              totalFailed++;
            } else if (!freshInvoice.buyer_email) {
              console.error(`[AutoSendOverdue] ✗ No email address for invoice ${invoice.id}`);
              failureBreakdown.email_no_address++;
              totalFailed++;
            } else {
              console.log(`[AutoSendOverdue] Sending E1 for invoice ${invoice.id} (${invoiceNumber})`);

              const emailData = {
                nazwa_klienta: freshInvoice.buyer_name || 'Klient',
                numer_faktury: freshInvoice.number || `#${freshInvoice.id}`,
                kwota: ((freshInvoice.total || 0) - (freshInvoice.paid || 0)).toFixed(2),
                waluta: freshInvoice.currency || 'EUR',
                termin: freshInvoice.payment_to
                  ? new Date(freshInvoice.payment_to).toLocaleDateString('pl-PL')
                  : 'brak',
              };

              const result = await sendEmailReminder(
                'EMAIL_1',
                freshInvoice.buyer_email,
                emailData,
                freshInvoice.id
              );

              if (result.success) {
                console.log(`[AutoSendOverdue] ✓ E1 sent for invoice ${invoice.id}`);
                emailSent = true;
                totalEmailSent++;

                // Update Fiscal Sync immediately
                const currentDate = new Date().toISOString();
                const updatedInternalNote = updateFiscalSync(
                  freshInvoice.internal_note,
                  'EMAIL_1',
                  true,
                  currentDate
                );

                await fakturowniaApi.updateInvoiceComment(invoice.id, updatedInternalNote);
                await invoicesDb.updateComment(invoice.id, updatedInternalNote);
                await commentsDb.logAction(invoice.id, 'Sent EMAIL reminder (level 1)', 'local');
              } else {
                console.error(`[AutoSendOverdue] ✗ Failed to send E1 for invoice ${invoice.id}: ${result.error}`);
                failureBreakdown.email_send_failed++;
                totalFailed++;
              }

              // Small delay to avoid overwhelming APIs
              await new Promise(resolve => setTimeout(resolve, 100));
            }

            // ============================================================
            // S1 CHECK: Re-fetch from Supabase to get latest flags (includes E1 if just sent)
            // ============================================================
            console.log(`[AutoSendOverdue] Re-fetching invoice ${invoice.id} for S1 check...`);
            try {
              freshInvoice = await invoicesDb.getById(invoice.id);
              if (!freshInvoice) {
                console.error(`[AutoSendOverdue] Invoice ${invoice.id} not found in Supabase for S1 check`);
                continue;
              }
            } catch (err) {
              console.error(`[AutoSendOverdue] Failed to re-fetch invoice ${invoice.id} for S1 check:`, err);
              continue;
            }

            fiscalSync = parseFiscalSync(freshInvoice.internal_note);

            // Send S1 if not already sent
            if (fiscalSync?.SMS_1) {
              console.log(`[AutoSendOverdue] ⊘ S1 already sent for invoice ${invoice.id} - skipping`);
              failureBreakdown.sms_already_sent++;
              totalFailed++;
            } else if (!freshInvoice.buyer_phone) {
              console.error(`[AutoSendOverdue] ✗ No phone number for invoice ${invoice.id}`);
              failureBreakdown.sms_no_phone++;
              totalFailed++;
            } else {
              console.log(`[AutoSendOverdue] Sending S1 for invoice ${invoice.id} (${invoiceNumber})`);

              const smsData = {
                nazwa_klienta: freshInvoice.buyer_name || 'Klient',
                numer_faktury: freshInvoice.number || `#${freshInvoice.id}`,
                kwota: ((freshInvoice.total || 0) - (freshInvoice.paid || 0)).toFixed(2),
                waluta: freshInvoice.currency || 'EUR',
                termin: freshInvoice.payment_to
                  ? new Date(freshInvoice.payment_to).toLocaleDateString('pl-PL')
                  : 'brak',
              };

              const result = await sendSmsReminder(
                'REMINDER_1',
                freshInvoice.buyer_phone,
                smsData
              );

              if (result.success) {
                console.log(`[AutoSendOverdue] ✓ S1 sent for invoice ${invoice.id}`);
                smsSent = true;
                totalSmsSent++;

                // Update Fiscal Sync immediately
                const currentDate = new Date().toISOString();
                const updatedInternalNote = updateFiscalSync(
                  freshInvoice.internal_note,
                  'SMS_1',
                  true,
                  currentDate
                );

                await fakturowniaApi.updateInvoiceComment(invoice.id, updatedInternalNote);
                await invoicesDb.updateComment(invoice.id, updatedInternalNote);
                await commentsDb.logAction(invoice.id, 'Sent SMS reminder (level 1)', 'local');
              } else {
                console.error(`[AutoSendOverdue] ✗ Failed to send S1 for invoice ${invoice.id}: ${result.error}`);
                failureBreakdown.sms_send_failed++;
                totalFailed++;
              }

              // Small delay
              await new Promise(resolve => setTimeout(resolve, 100));
            }

            // Find client info for this invoice
            const client = clients.find(c => c.id === invoice.client_id);

            results.push({
              client_id: invoice.client_id,
              client_name: client?.name || 'Unknown',
              invoice_id: invoice.id,
              invoice_number: invoiceNumber,
              email_sent: emailSent,
              sms_sent: smsSent,
            });

          } catch (error: any) {
            console.error(`[AutoSendOverdue] Error processing invoice ${invoice.id}:`, error);
            failureBreakdown.invoice_processing_error++;
            totalFailed++;

            const client = clients.find(c => c.id === invoice.client_id);
            results.push({
              client_id: invoice.client_id,
              client_name: client?.name || 'Unknown',
              invoice_id: invoice.id,
              invoice_number: invoiceNumber,
              error: error.message,
            });
          }
    }

    const totalSent = totalEmailSent + totalSmsSent;

    console.log(`[AutoSendOverdue] Completed: ${totalSent} total sent (E1: ${totalEmailSent}, S1: ${totalSmsSent}), ${totalFailed} failed`);
    console.log(`[AutoSendOverdue] Failure breakdown:`, JSON.stringify(failureBreakdown, null, 2));

    return NextResponse.json({
      success: true,
      message: `Daily windykacja completed: ${totalSent} messages sent (E1: ${totalEmailSent}, S1: ${totalSmsSent}), ${totalFailed} failed${remaining > 0 ? `, ${remaining} remaining` : ''}`,
      sent: {
        email: totalEmailSent,
        sms: totalSmsSent,
        total: totalSent,
      },
      failed: totalFailed,
      failure_breakdown: failureBreakdown,
      clients_processed: clients.length,
      invoices_processed: invoicesToProcess.length,
      invoices_remaining: remaining,
      results,
    });

  } catch (error: any) {
    console.error('[AutoSendOverdue] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}

// Vercel Cron sends GET requests by default, so we need to handle them
export async function GET(request: NextRequest) {
  console.log('[AutoSendOverdue] GET request received, forwarding to POST handler');
  return POST(request);
}
