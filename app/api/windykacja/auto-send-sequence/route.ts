import { NextRequest, NextResponse } from 'next/server';
import { fakturowniaApi } from '@/lib/fakturownia';
import { parseFiscalSync, updateFiscalSync } from '@/lib/fiscal-sync-parser';
import { parseClientFlags } from '@/lib/client-flags-v2';
import { createClient } from '@supabase/supabase-js';
import { sendEmailReminder } from '@/lib/mailgun';
import { sendSmsReminder } from '@/lib/sms';
import { invoicesDb, commentsDb, messageHistoryDb, prepareMessageHistoryEntry } from '@/lib/supabase';
import type { FiscalSyncData } from '@/types';

/**
 * Auto-send sequence: E2, E3, S2, S3 based on 14-day intervals
 *
 * Runs daily at 7:30 AM via Vercel cron (after auto-send-overdue at 7:15)
 *
 * Two parallel tracks (emails and SMS have same logic):
 * - Day 0:  E1 + S1 sent (by auto-send-overdue)
 * - Day 14: E2 + S2 automatically sent
 * - Day 28: E3 + S3 automatically sent
 *
 * E2/E3/S2/S3 only check:
 * 1. Is windykacja enabled on client? (checked in client filter)
 * 2. Was previous step (E1/E2/S1/S2) sent 14+ days ago?
 * 3. Is invoice open (not paid, not canceled, has balance)?
 * 4. Is STOP flag false?
 *
 * NOTE: The 30-day issue_date check is ONLY for E1/S1 (auto-send-overdue).
 * Once E1/S1 is sent, the sequence continues based on 14-day intervals only.
 */

// Force dynamic rendering
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const DAYS_BETWEEN_STEPS = 14;

interface SequenceStep {
  check: keyof Omit<FiscalSyncData, 'UPDATED'>;       // Field to check if already sent (e.g., 'EMAIL_2')
  dateField: keyof FiscalSyncData;   // Previous step's date field (e.g., 'EMAIL_1_DATE')
  type: 'email' | 'sms';
  level: string;
  prevCheck?: keyof Omit<FiscalSyncData, 'UPDATED'>;  // Previous step that must be completed
}

// Sequence definition - Two parallel tracks:
// Email track: E1 → E2 → E3 (14 days apart)
// SMS track: S1 → S2 → S3 (14 days apart)
// E1 + S1 are sent by auto-send-overdue on day 0
const SEQUENCE: SequenceStep[] = [
  {
    check: 'EMAIL_2',
    dateField: 'EMAIL_1_DATE',
    type: 'email',
    level: '2',
    prevCheck: 'EMAIL_1'
  },
  {
    check: 'EMAIL_3',
    dateField: 'EMAIL_2_DATE',
    type: 'email',
    level: '3',
    prevCheck: 'EMAIL_2'
  },
  {
    check: 'SMS_2',
    dateField: 'SMS_1_DATE',
    type: 'sms',
    level: '2',
    prevCheck: 'SMS_1'
  },
  {
    check: 'SMS_3',
    dateField: 'SMS_2_DATE',
    type: 'sms',
    level: '3',
    prevCheck: 'SMS_2'
  },
];

function getE1Date(invoice: any, fiscalSync: any): Date | null {
  // Priority: Fakturownia's sent_time first (actual email sent date)
  // Then our system's EMAIL_1_DATE (may be later if we just marked it)

  // Check if email was sent by Fakturownia (email_status = 'sent')
  if (invoice.email_status === 'sent' && invoice.sent_time) {
    return new Date(invoice.sent_time);
  }

  // Fallback: Check if E1 was sent by our system
  if (fiscalSync?.EMAIL_1 && fiscalSync?.EMAIL_1_DATE && fiscalSync.EMAIL_1_DATE !== 'NULL') {
    return new Date(fiscalSync.EMAIL_1_DATE);
  }

  return null;
}

function getDateFromFiscalSync(fiscalSync: any, dateField: string): Date | null {
  const dateValue = fiscalSync?.[dateField];
  if (!dateValue || dateValue === 'NULL') return null;
  return new Date(dateValue);
}

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
    console.log('[AutoSendSequence] Starting 14-day sequence check...');

    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );

    // 1. Get all clients using pagination (Supabase has 1000 row limit)
    let allClients: any[];
    try {
      allClients = await fetchAllClients(supabase);
    } catch (error: any) {
      console.error('[AutoSendSequence] Error fetching clients:', error);
      return NextResponse.json(
        { success: false, error: error.message },
        { status: 500 }
      );
    }

    const clients = allClients.filter(client => {
      const flags = parseClientFlags(client.note);
      return flags.windykacja === true;
    });

    if (clients.length === 0) {
      console.log('[AutoSendSequence] No clients with windykacja enabled');
      return NextResponse.json({
        success: true,
        message: 'No clients with windykacja enabled',
        sent: { email: 0, sms: 0, total: 0 },
        failed: 0,
      });
    }

    console.log(`[AutoSendSequence] Found ${clients.length} clients with windykacja enabled (out of ${allClients.length} total)`);

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const fourteenDaysAgo = new Date(today);
    fourteenDaysAgo.setDate(fourteenDaysAgo.getDate() - DAYS_BETWEEN_STEPS);

    // Get client IDs for windykacja clients
    const windykacjaClientIds = clients.map(c => c.id);

    // 2. Fetch ALL qualifying invoices from Supabase in ONE query (much faster than per-client Fakturownia calls)
    console.log(`[AutoSendSequence] Fetching invoices from Supabase for ${windykacjaClientIds.length} clients...`);

    const { data: allInvoices, error: invoicesError } = await supabase
      .from('invoices')
      .select('*')
      .in('client_id', windykacjaClientIds)
      .neq('status', 'paid')
      .neq('kind', 'canceled')
      .order('issue_date', { ascending: false });

    if (invoicesError) {
      console.error('[AutoSendSequence] Error fetching invoices:', invoicesError);
      return NextResponse.json(
        { success: false, error: invoicesError.message },
        { status: 500 }
      );
    }

    // 3. Filter qualifying invoices (has balance, STOP not set, E1 sent)
    const qualifyingInvoices = (allInvoices || []).filter((invoice) => {
      const balance = (invoice.total || 0) - (invoice.paid || 0);
      if (balance <= 0) return false;

      const fiscalSync = parseFiscalSync(invoice.internal_note);
      if (fiscalSync?.STOP === true) {
        console.log(`[AutoSendSequence] Skipping invoice ${invoice.id} - STOP enabled`);
        return false;
      }

      // Must have E1 or S1 sent to be in sequence
      const e1Sent = fiscalSync?.EMAIL_1 || invoice.email_status === 'sent';
      const s1Sent = fiscalSync?.SMS_1;
      if (!e1Sent && !s1Sent) return false;

      return true;
    });

    console.log(`[AutoSendSequence] Found ${qualifyingInvoices.length} qualifying invoices (out of ${allInvoices?.length || 0} total)`);

    if (qualifyingInvoices.length === 0) {
      return NextResponse.json({
        success: true,
        message: 'No qualifying invoices for sequence',
        sent: { email: 0, sms: 0, total: 0 },
        failed: 0,
      });
    }

    // BATCH PROCESSING: Limit to 20 invoices per execution to avoid Vercel timeout
    const BATCH_SIZE = 20;
    const invoicesToProcess = qualifyingInvoices.slice(0, BATCH_SIZE);
    const remaining = qualifyingInvoices.length - invoicesToProcess.length;

    if (remaining > 0) {
      console.log(`[AutoSendSequence] Processing first ${BATCH_SIZE} invoices, ${remaining} remaining for next run`);
    }

    let totalEmailSent = 0;
    let totalSmsSent = 0;
    let totalFailed = 0;
    const results: any[] = [];

    // 4. Check sequence for each invoice
    for (const invoice of invoicesToProcess) {
          const invoiceNumber = invoice.number || `INV-${invoice.id}`;

          // ✅ RE-FETCH FRESH data from Supabase before checking flags
          console.log(`[AutoSendSequence] Re-fetching invoice ${invoice.id} from Supabase for fresh flags...`);
          let freshInvoice;
          try {
            freshInvoice = await invoicesDb.getById(invoice.id);
            if (!freshInvoice) {
              console.error(`[AutoSendSequence] Invoice ${invoice.id} not found in Supabase, skipping`);
              continue;
            }
          } catch (err) {
            console.error(`[AutoSendSequence] Failed to re-fetch invoice ${invoice.id}, skipping:`, err);
            continue;
          }

          let fiscalSync = parseFiscalSync(freshInvoice.internal_note);

          // Get E1 date (from our system or Fakturownia)
          const e1Date = getE1Date(freshInvoice, fiscalSync);

          if (!e1Date) {
            // E1 not sent yet - skip (auto-send-overdue handles E1)
            console.log(`[AutoSendSequence] Invoice ${invoice.id} - E1 not sent yet, skipping`);
            continue;
          }

          // Check each step in sequence
          let actionTaken = false;

          for (const step of SEQUENCE) {
            // ============================================================
            // RE-FETCH before EACH step to get latest flags from Supabase
            // ============================================================
            console.log(`[AutoSendSequence] Re-fetching invoice ${invoice.id} for ${step.check} check...`);
            try {
              freshInvoice = await invoicesDb.getById(invoice.id);
              if (!freshInvoice) {
                console.error(`[AutoSendSequence] Invoice ${invoice.id} not found in Supabase for ${step.check} check`);
                break;
              }
            } catch (err) {
              console.error(`[AutoSendSequence] Failed to re-fetch invoice ${invoice.id} for ${step.check} check:`, err);
              break;
            }

            fiscalSync = parseFiscalSync(freshInvoice.internal_note);

            // Skip if this step already done
            if (fiscalSync?.[step.check] === true) {
              continue;
            }

            // Check if previous step is done
            if (step.prevCheck && fiscalSync?.[step.prevCheck] !== true) {
              // For EMAIL_2, we also accept Fakturownia's email_status=sent as E1
              if (step.check === 'EMAIL_2') {
                if (freshInvoice.email_status !== 'sent') {
                  continue;
                }
              } else {
                continue;
              }
            }

            // Get the date of the previous action
            let prevDate: Date | null = null;

            if (step.dateField === 'EMAIL_1_DATE') {
              prevDate = e1Date; // Use E1 date (from our system or Fakturownia)
            } else {
              prevDate = getDateFromFiscalSync(fiscalSync, step.dateField);
            }

            if (!prevDate) {
              console.log(`[AutoSendSequence] Invoice ${invoice.id} - No date for ${step.dateField}, skipping ${step.check}`);
              continue;
            }

            // Check if 14 days have passed
            if (prevDate > fourteenDaysAgo) {
              const daysAgo = Math.floor((today.getTime() - prevDate.getTime()) / (1000 * 60 * 60 * 24));
              console.log(`[AutoSendSequence] Invoice ${invoice.id} - ${step.dateField} was ${daysAgo} days ago (need ${DAYS_BETWEEN_STEPS}), skipping ${step.check}`);
              continue;
            }

            // Ready to send this step!
            console.log(`[AutoSendSequence] Sending ${step.type.toUpperCase()}_${step.level} for invoice ${invoice.id} (${invoiceNumber})`);

            try {
              // Prepare message data
              const messageData = {
                nazwa_klienta: freshInvoice.buyer_name || 'Klient',
                numer_faktury: freshInvoice.number || `#${freshInvoice.id}`,
                kwota: ((freshInvoice.total || 0) - (freshInvoice.paid || 0)).toFixed(2),
                waluta: freshInvoice.currency || 'EUR',
                termin: freshInvoice.payment_to
                  ? new Date(freshInvoice.payment_to).toLocaleDateString('pl-PL')
                  : 'brak',
              };

              let result;

              // Send email or SMS directly
              if (step.type === 'email') {
                const templateId = `EMAIL_${step.level}` as 'EMAIL_1' | 'EMAIL_2' | 'EMAIL_3';
                result = await sendEmailReminder(
                  templateId,
                  freshInvoice.buyer_email || 'brak@email.com',
                  messageData,
                  freshInvoice.id
                );
              } else if (step.type === 'sms') {
                if (!freshInvoice.buyer_phone) {
                  console.error(`[AutoSendSequence] ✗ No phone number for invoice ${invoice.id}`);
                  totalFailed++;
                  const clientForNoPhone = clients.find(c => c.id === invoice.client_id);
                  results.push({
                    client_id: invoice.client_id,
                    client_name: clientForNoPhone?.name || 'Unknown',
                    invoice_id: invoice.id,
                    invoice_number: invoiceNumber,
                    action: `${step.type.toUpperCase()}_${step.level}`,
                    success: false,
                    error: 'Brak numeru telefonu',
                  });
                  continue;
                }

                const templateKey = `REMINDER_${step.level}` as 'REMINDER_1' | 'REMINDER_2' | 'REMINDER_3';
                result = await sendSmsReminder(
                  templateKey,
                  freshInvoice.buyer_phone,
                  messageData
                );
              }

              if (result && result.success) {
                console.log(`[AutoSendSequence] ✓ ${step.type.toUpperCase()}_${step.level} sent for invoice ${invoice.id}`);
                if (step.type === 'email') {
                  totalEmailSent++;
                } else {
                  totalSmsSent++;
                }
                actionTaken = true;

                // Update Fiscal Sync immediately
                const currentDate = new Date().toISOString();
                const updatedInternalNote = updateFiscalSync(
                  freshInvoice.internal_note,
                  step.check,
                  true,
                  currentDate
                );

                await fakturowniaApi.updateInvoiceComment(invoice.id, updatedInternalNote);
                await invoicesDb.updateComment(invoice.id, updatedInternalNote);
                await commentsDb.logAction(
                  invoice.id,
                  `Sent ${step.type.toUpperCase()} reminder (level ${step.level})`,
                  'local'
                );

                const clientForSuccess = clients.find(c => c.id === invoice.client_id);
                results.push({
                  client_id: invoice.client_id,
                  client_name: clientForSuccess?.name || 'Unknown',
                  invoice_id: invoice.id,
                  invoice_number: invoiceNumber,
                  action: `${step.type.toUpperCase()}_${step.level}`,
                  success: true,
                });
              } else {
                console.error(`[AutoSendSequence] ✗ Failed to send ${step.type.toUpperCase()}_${step.level} for invoice ${invoice.id}: ${result?.error}`);
                totalFailed++;

                const clientForFail = clients.find(c => c.id === invoice.client_id);
                results.push({
                  client_id: invoice.client_id,
                  client_name: clientForFail?.name || 'Unknown',
                  invoice_id: invoice.id,
                  invoice_number: invoiceNumber,
                  action: `${step.type.toUpperCase()}_${step.level}`,
                  success: false,
                  error: result?.error,
                });
              }

              // Delay to avoid overwhelming APIs
              await new Promise(resolve => setTimeout(resolve, 100));

            } catch (error: any) {
              console.error(`[AutoSendSequence] Error sending ${step.type}_${step.level} for invoice ${invoice.id}:`, error);
              totalFailed++;

              const clientForError = clients.find(c => c.id === invoice.client_id);
              results.push({
                client_id: invoice.client_id,
                client_name: clientForError?.name || 'Unknown',
                invoice_id: invoice.id,
                invoice_number: invoiceNumber,
                action: `${step.type.toUpperCase()}_${step.level}`,
                success: false,
                error: error.message,
              });
            }

            // Only one action per invoice per day
            if (actionTaken) {
              break;
            }
          }
    }

    const totalSent = totalEmailSent + totalSmsSent;

    console.log(`[AutoSendSequence] Completed: ${totalSent} total sent (E: ${totalEmailSent}, S: ${totalSmsSent}), ${totalFailed} failed`);

    return NextResponse.json({
      success: true,
      message: `Sequence check completed: ${totalSent} messages sent, ${totalFailed} failed${remaining > 0 ? `, ${remaining} remaining` : ''}`,
      sent: {
        email: totalEmailSent,
        sms: totalSmsSent,
        total: totalSent,
      },
      failed: totalFailed,
      clients_processed: clients.length,
      invoices_processed: invoicesToProcess.length,
      invoices_remaining: remaining,
      results,
    });

  } catch (error: any) {
    console.error('[AutoSendSequence] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}

// Vercel Cron sends GET requests by default, so we need to handle them
export async function GET(request: NextRequest) {
  console.log('[AutoSendSequence] GET request received, forwarding to POST handler');
  return POST(request);
}
