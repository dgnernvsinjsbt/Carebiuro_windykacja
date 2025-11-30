import { NextRequest, NextResponse } from 'next/server';
import { fakturowniaApi } from '@/lib/fakturownia';
import { parseFiscalSync } from '@/lib/fiscal-sync-parser';
import { parseClientFlags } from '@/lib/client-flags-v2';
import { createClient } from '@supabase/supabase-js';
import type { FiscalSyncData } from '@/types';

/**
 * Auto-send sequence: E2, E3, S1, S2 based on 14-day intervals
 *
 * Runs daily at 8:30 AM via Vercel cron (after auto-send-overdue at 8:15)
 *
 * Sequence:
 * - Day 0:  E1 sent (by Fakturownia or auto-send-overdue)
 * - Day 14: E2 automatically sent
 * - Day 28: E3 automatically sent
 * - Day 42: S1 automatically sent
 * - Day 56: S2 automatically sent
 *
 * Logic:
 * 1. Find all clients with windykacja enabled
 * 2. For each client, fetch invoices from Fakturownia
 * 3. Filter overdue invoices with STOP = false
 * 4. Check the last action date (E1/E2/E3/S1) and send next step if > 14 days
 * 5. Only one action per invoice per day
 */

// Force dynamic rendering
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const DAYS_BETWEEN_STEPS = 14;

interface SequenceStep {
  check: keyof FiscalSyncData;       // Field to check if already sent (e.g., 'EMAIL_2')
  dateField: keyof FiscalSyncData;   // Previous step's date field (e.g., 'EMAIL_1_DATE')
  type: 'email' | 'sms';
  level: string;
  prevCheck?: keyof FiscalSyncData;  // Previous step that must be completed
}

// Sequence definition: E1 → E2 → E3 → S1 → S2
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
    check: 'SMS_1',
    dateField: 'EMAIL_3_DATE',
    type: 'sms',
    level: '1',
    prevCheck: 'EMAIL_3'
  },
  {
    check: 'SMS_2',
    dateField: 'SMS_1_DATE',
    type: 'sms',
    level: '2',
    prevCheck: 'SMS_1'
  },
];

function getE1Date(invoice: any, fiscalSync: any): Date | null {
  // Check if E1 was sent by our system
  if (fiscalSync?.EMAIL_1 && fiscalSync?.EMAIL_1_DATE) {
    return new Date(fiscalSync.EMAIL_1_DATE);
  }

  // Check if email was sent by Fakturownia (email_status = 'sent')
  if (invoice.email_status === 'sent' && invoice.sent_time) {
    return new Date(invoice.sent_time);
  }

  return null;
}

function getDateFromFiscalSync(fiscalSync: any, dateField: string): Date | null {
  const dateValue = fiscalSync?.[dateField];
  if (!dateValue || dateValue === 'NULL') return null;
  return new Date(dateValue);
}

export async function POST(request: NextRequest) {
  try {
    console.log('[AutoSendSequence] Starting 14-day sequence check...');

    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );

    // 1. Get all clients with windykacja enabled
    const { data: allClients, error: clientsError } = await supabase
      .from('clients')
      .select('id, name, note');

    if (clientsError) {
      console.error('[AutoSendSequence] Error fetching clients:', clientsError);
      return NextResponse.json(
        { success: false, error: clientsError.message },
        { status: 500 }
      );
    }

    const clients = (allClients || []).filter(client => {
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

    console.log(`[AutoSendSequence] Found ${clients.length} clients with windykacja enabled`);

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const fourteenDaysAgo = new Date(today);
    fourteenDaysAgo.setDate(fourteenDaysAgo.getDate() - DAYS_BETWEEN_STEPS);

    let totalEmailSent = 0;
    let totalSmsSent = 0;
    let totalFailed = 0;
    const results: any[] = [];

    // 2. Process each client
    for (const client of clients) {
      console.log(`[AutoSendSequence] Processing client: ${client.name} (ID: ${client.id})`);

      try {
        const invoices = await fakturowniaApi.getInvoicesByClientId(client.id, 500);

        if (!invoices || invoices.length === 0) {
          console.log(`[AutoSendSequence] No invoices for client ${client.id}`);
          continue;
        }

        // 3. Filter overdue invoices
        const overdueInvoices = invoices.filter((invoice) => {
          if (invoice.status === 'paid') return false;
          if (invoice.kind === 'canceled') return false;

          const balance = parseFloat(invoice.price_gross || '0') - parseFloat(invoice.paid || '0');
          if (balance <= 0) return false;

          if (!invoice.payment_to) return false;
          const paymentDate = new Date(invoice.payment_to);
          paymentDate.setHours(0, 0, 0, 0);
          if (paymentDate >= today) return false;

          const fiscalSync = parseFiscalSync(invoice.internal_note);
          if (fiscalSync?.STOP === true) {
            console.log(`[AutoSendSequence] Skipping invoice ${invoice.id} - STOP enabled`);
            return false;
          }

          return true;
        });

        console.log(`[AutoSendSequence] Found ${overdueInvoices.length} overdue invoices for client ${client.id}`);

        // 4. Check sequence for each invoice
        for (const invoice of overdueInvoices) {
          const invoiceNumber = invoice.number || `INV-${invoice.id}`;
          const fiscalSync = parseFiscalSync(invoice.internal_note);

          // Get E1 date (from our system or Fakturownia)
          const e1Date = getE1Date(invoice, fiscalSync);

          if (!e1Date) {
            // E1 not sent yet - skip (auto-send-overdue handles E1)
            console.log(`[AutoSendSequence] Invoice ${invoice.id} - E1 not sent yet, skipping`);
            continue;
          }

          // Check each step in sequence
          let actionTaken = false;

          for (const step of SEQUENCE) {
            // Skip if this step already done
            if (fiscalSync?.[step.check] === true) {
              continue;
            }

            // Check if previous step is done
            if (step.prevCheck && fiscalSync?.[step.prevCheck] !== true) {
              // For EMAIL_2, we also accept Fakturownia's email_status=sent as E1
              if (step.check === 'EMAIL_2') {
                if (invoice.email_status !== 'sent') {
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
              const apiUrl = process.env.NODE_ENV === 'development'
                ? 'http://localhost:3000/api/reminder'
                : `${request.nextUrl.origin}/api/reminder`;

              const response = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  invoice_id: invoice.id,
                  type: step.type,
                  level: step.level,
                }),
              });

              const data = await response.json();

              if (data.success) {
                console.log(`[AutoSendSequence] ✓ ${step.type.toUpperCase()}_${step.level} sent for invoice ${invoice.id}`);
                if (step.type === 'email') {
                  totalEmailSent++;
                } else {
                  totalSmsSent++;
                }
                actionTaken = true;

                results.push({
                  client_id: client.id,
                  client_name: client.name,
                  invoice_id: invoice.id,
                  invoice_number: invoiceNumber,
                  action: `${step.type.toUpperCase()}_${step.level}`,
                  success: true,
                });
              } else {
                console.error(`[AutoSendSequence] ✗ Failed to send ${step.type.toUpperCase()}_${step.level} for invoice ${invoice.id}: ${data.error}`);
                totalFailed++;

                results.push({
                  client_id: client.id,
                  client_name: client.name,
                  invoice_id: invoice.id,
                  invoice_number: invoiceNumber,
                  action: `${step.type.toUpperCase()}_${step.level}`,
                  success: false,
                  error: data.error,
                });
              }

              // Delay to avoid overwhelming APIs
              await new Promise(resolve => setTimeout(resolve, 500));

            } catch (error: any) {
              console.error(`[AutoSendSequence] Error sending ${step.type}_${step.level} for invoice ${invoice.id}:`, error);
              totalFailed++;

              results.push({
                client_id: client.id,
                client_name: client.name,
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

      } catch (error: any) {
        console.error(`[AutoSendSequence] Error processing client ${client.id}:`, error);
        totalFailed++;
      }
    }

    const totalSent = totalEmailSent + totalSmsSent;

    console.log(`[AutoSendSequence] Completed: ${totalSent} total sent (E: ${totalEmailSent}, S: ${totalSmsSent}), ${totalFailed} failed`);

    return NextResponse.json({
      success: true,
      message: `Sequence check completed: ${totalSent} messages sent, ${totalFailed} failed`,
      sent: {
        email: totalEmailSent,
        sms: totalSmsSent,
        total: totalSent,
      },
      failed: totalFailed,
      clients_processed: clients.length,
      days_between_steps: DAYS_BETWEEN_STEPS,
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

// Vercel Cron sends GET requests
export async function GET(request: NextRequest) {
  console.log('[AutoSendSequence] GET request received, forwarding to POST handler');
  return POST(request);
}
