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

    let totalEmailSent = 0;
    let totalSmsSent = 0;
    let totalFailed = 0;
    const results: any[] = [];

    // 2. Process each client
    for (const client of clients) {
      console.log(`[AutoSendOverdue] Processing client: ${client.name} (ID: ${client.id})`);

      try {
        // Fetch client's invoices from Fakturownia (fresh data with latest comments)
        const invoices = await fakturowniaApi.getInvoicesByClientId(client.id, 500);

        if (!invoices || invoices.length === 0) {
          console.log(`[AutoSendOverdue] No invoices for client ${client.id}`);
          continue;
        }

        console.log(`[AutoSendOverdue] Found ${invoices.length} total invoices for client ${client.id}`);

        // 3. Filter qualifying invoices (30+ days since issue_date)
        const qualifyingInvoices = invoices.filter((invoice) => {
          // Skip paid invoices
          if (invoice.status === 'paid') return false;

          // Skip canceled invoices
          if (invoice.kind === 'canceled') return false;

          // Skip VAT invoices - they are always paid (issued only after proforma payment)
          if (invoice.kind === 'vat') return false;

          // Skip if no unpaid balance
          const balance = parseFloat(invoice.price_gross || '0') - parseFloat(invoice.paid || '0');
          if (balance <= 0) return false;

          // Check if invoice is 30+ days old (from issue_date)
          if (!invoice.issue_date) return false;
          const issueDate = new Date(invoice.issue_date);
          issueDate.setHours(0, 0, 0, 0);
          if (issueDate > thirtyDaysAgo) return false; // Not 30 days old yet

          // Parse fiscal sync
          const fiscalSync = parseFiscalSync(invoice.internal_note);

          // Skip if STOP enabled
          if (fiscalSync?.STOP === true) {
            console.log(`[AutoSendOverdue] Skipping invoice ${invoice.id} - STOP enabled`);
            return false;
          }

          return true;
        });

        console.log(`[AutoSendOverdue] Found ${qualifyingInvoices.length} qualifying invoices for client ${client.id}`);

        if (qualifyingInvoices.length === 0) continue;

        // 4. Send E1 + S1 for each qualifying invoice
        for (const invoice of qualifyingInvoices) {
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

          const fiscalSync = parseFiscalSync(freshInvoice.internal_note);

          let emailSent = false;
          let smsSent = false;

          try {
            // Send E1 if not already sent
            // Check both: our system (EMAIL_1) AND Fakturownia (email_status='sent')
            const e1AlreadySent = fiscalSync?.EMAIL_1 || freshInvoice.email_status === 'sent';

            if (!e1AlreadySent) {
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
                freshInvoice.buyer_email || 'brak@email.com',
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
                totalFailed++;
              }

              // Small delay to avoid overwhelming APIs
              await new Promise(resolve => setTimeout(resolve, 500));
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
            if (!fiscalSync?.SMS_1) {
              console.log(`[AutoSendOverdue] Sending S1 for invoice ${invoice.id} (${invoiceNumber})`);

              if (!freshInvoice.buyer_phone) {
                console.error(`[AutoSendOverdue] ✗ No phone number for invoice ${invoice.id}`);
                totalFailed++;
                await new Promise(resolve => setTimeout(resolve, 500));
                continue;
              }

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
                totalFailed++;
              }

              // Small delay
              await new Promise(resolve => setTimeout(resolve, 500));
            }

            results.push({
              client_id: client.id,
              client_name: client.name,
              invoice_id: invoice.id,
              invoice_number: invoiceNumber,
              email_sent: emailSent,
              sms_sent: smsSent,
            });

          } catch (error: any) {
            console.error(`[AutoSendOverdue] Error processing invoice ${invoice.id}:`, error);
            totalFailed++;
            results.push({
              client_id: client.id,
              client_name: client.name,
              invoice_id: invoice.id,
              invoice_number: invoiceNumber,
              error: error.message,
            });
          }
        }

      } catch (error: any) {
        console.error(`[AutoSendOverdue] Error processing client ${client.id}:`, error);
        totalFailed++;
      }
    }

    const totalSent = totalEmailSent + totalSmsSent;

    console.log(`[AutoSendOverdue] Completed: ${totalSent} total sent (E1: ${totalEmailSent}, S1: ${totalSmsSent}), ${totalFailed} failed`);

    return NextResponse.json({
      success: true,
      message: `Daily windykacja completed: ${totalSent} messages sent (E1: ${totalEmailSent}, S1: ${totalSmsSent}), ${totalFailed} failed`,
      sent: {
        email: totalEmailSent,
        sms: totalSmsSent,
        total: totalSent,
      },
      failed: totalFailed,
      clients_processed: clients.length,
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
