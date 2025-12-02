import { NextRequest, NextResponse } from 'next/server';
import { fakturowniaApi } from '@/lib/fakturownia';
import { parseFiscalSync } from '@/lib/fiscal-sync-parser';
import { parseClientFlags } from '@/lib/client-flags-v2';
import { createClient } from '@supabase/supabase-js';

/**
 * Auto-send E1 + S1 for all overdue invoices for clients with windykacja enabled
 *
 * Runs daily at 8:00 AM via Vercel cron
 *
 * Logic:
 * 1. Find all clients with windykacja_enabled = true
 * 2. For each client, fetch invoices from Fakturownia
 * 3. Filter overdue invoices (payment_to < today)
 * 4. Send E1 + S1 if not already sent and STOP = false
 * 5. Update [FISCAL_SYNC] in Fakturownia
 */

// Force dynamic rendering
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  try {
    console.log('[AutoSendOverdue] Starting daily windykacja run...');

    // Initialize Supabase
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );

    // 1. Get all clients from Supabase
    const { data: allClients, error: clientsError } = await supabase
      .from('clients')
      .select('id, name, note');

    if (clientsError) {
      console.error('[AutoSendOverdue] Error fetching clients:', clientsError);
      return NextResponse.json(
        { success: false, error: clientsError.message },
        { status: 500 }
      );
    }

    if (!allClients || allClients.length === 0) {
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

    // Today's date for overdue check
    const today = new Date();
    today.setHours(0, 0, 0, 0);

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

        // 3. Filter overdue invoices
        const overdueInvoices = invoices.filter((invoice) => {
          // Skip paid invoices
          if (invoice.status === 'paid') return false;

          // Skip canceled invoices
          if (invoice.kind === 'canceled') return false;

          // Skip if no unpaid balance
          const balance = parseFloat(invoice.price_gross || '0') - parseFloat(invoice.paid || '0');
          if (balance <= 0) return false;

          // Check if overdue
          if (!invoice.payment_to) return false;
          const paymentDate = new Date(invoice.payment_to);
          paymentDate.setHours(0, 0, 0, 0);
          if (paymentDate >= today) return false; // Not overdue yet

          // Parse fiscal sync
          const fiscalSync = parseFiscalSync(invoice.internal_note);

          // Skip if STOP enabled
          if (fiscalSync?.STOP === true) {
            console.log(`[AutoSendOverdue] Skipping invoice ${invoice.id} - STOP enabled`);
            return false;
          }

          return true;
        });

        console.log(`[AutoSendOverdue] Found ${overdueInvoices.length} overdue invoices for client ${client.id}`);

        if (overdueInvoices.length === 0) continue;

        // 4. Send E1 + S1 for each overdue invoice
        for (const invoice of overdueInvoices) {
          const invoiceNumber = invoice.number || `INV-${invoice.id}`;
          const fiscalSync = parseFiscalSync(invoice.internal_note);

          let emailSent = false;
          let smsSent = false;

          try {
            // Send E1 if not already sent
            // Check both: our system (EMAIL_1) AND Fakturownia (email_status='sent')
            const e1AlreadySent = fiscalSync?.EMAIL_1 || invoice.email_status === 'sent';

            if (!e1AlreadySent) {
              console.log(`[AutoSendOverdue] Sending E1 for invoice ${invoice.id} (${invoiceNumber})`);

              const apiUrl = process.env.NODE_ENV === 'development'
                ? 'http://localhost:3000/api/reminder'
                : `${request.nextUrl.origin}/api/reminder`;

              const emailResponse = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  invoice_id: invoice.id,
                  type: 'email',
                  level: '1',
                }),
              });

              const emailData = await emailResponse.json();

              if (emailData.success) {
                console.log(`[AutoSendOverdue] ✓ E1 sent for invoice ${invoice.id}`);
                emailSent = true;
                totalEmailSent++;
              } else {
                console.error(`[AutoSendOverdue] ✗ Failed to send E1 for invoice ${invoice.id}: ${emailData.error}`);
                totalFailed++;
              }

              // Small delay to avoid overwhelming APIs
              await new Promise(resolve => setTimeout(resolve, 500));
            }

            // Send S1 if not already sent
            if (!fiscalSync?.SMS_1) {
              console.log(`[AutoSendOverdue] Sending S1 for invoice ${invoice.id} (${invoiceNumber})`);

              const apiUrl = process.env.NODE_ENV === 'development'
                ? 'http://localhost:3000/api/reminder'
                : `${request.nextUrl.origin}/api/reminder`;

              const smsResponse = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  invoice_id: invoice.id,
                  type: 'sms',
                  level: '1',
                }),
              });

              const smsData = await smsResponse.json();

              if (smsData.success) {
                console.log(`[AutoSendOverdue] ✓ S1 sent for invoice ${invoice.id}`);
                smsSent = true;
                totalSmsSent++;
              } else {
                console.error(`[AutoSendOverdue] ✗ Failed to send S1 for invoice ${invoice.id}: ${smsData.error}`);
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
      message: `Daily windykacja completed: ${totalSent} messages sent, ${totalFailed} failed`,
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
