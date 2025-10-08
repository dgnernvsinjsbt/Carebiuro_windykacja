import { NextRequest, NextResponse } from 'next/server';
import { fakturowniaApi } from '@/lib/fakturownia';
import { parseFiscalSync } from '@/lib/fiscal-sync-parser';

/**
 * Auto-send S1 SMS for all eligible invoices when windykacja is enabled
 *
 * Fetches FRESH data from Fakturownia (not Supabase) to ensure we have latest invoice comments
 *
 * Eligible invoices:
 * - Not paid (status != 'paid')
 * - Not canceled (kind != 'canceled')
 * - STOP is false or not set
 * - SMS_1 not sent yet
 * - Has unpaid balance (total - paid > 0)
 */
// Force dynamic rendering - don't evaluate at build time
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  try {
    const { client_id } = await request.json();

    if (!client_id) {
      return NextResponse.json(
        { success: false, error: 'Client ID is required' },
        { status: 400 }
      );
    }

    console.log(`[AutoSend] Starting auto-send S1 for client ${client_id}`);

    // Fetch client's invoices DIRECTLY from Fakturownia (fresh data with latest comments!)
    const invoices = await fakturowniaApi.getInvoicesByClientId(client_id, 100);

    if (!invoices || invoices.length === 0) {
      console.log('[AutoSend] No invoices found for client');
      return NextResponse.json({
        success: true,
        message: 'No invoices to process',
        sent: 0,
      });
    }

    console.log(`[AutoSend] Found ${invoices.length} total invoices from Fakturownia`);

    // Filter invoices eligible for S1 auto-send
    const eligibleInvoices = invoices.filter((invoice) => {
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

      // Parse fiscal sync data from internal_note (Fakturownia uses internal_note for comments)
      const fiscalSync = parseFiscalSync(invoice.internal_note);

      // Skip if STOP is enabled
      if (fiscalSync?.STOP === true) {
        console.log(`[AutoSend] Skipping invoice ${invoice.id} - STOP enabled`);
        return false;
      }

      // Skip if SMS_1 already sent
      if (fiscalSync?.SMS_1 === true) {
        console.log(`[AutoSend] Skipping invoice ${invoice.id} - SMS_1 already sent`);
        return false;
      }

      return true;
    });

    console.log(`[AutoSend] Found ${eligibleInvoices.length} eligible invoices out of ${invoices.length}`);

    if (eligibleInvoices.length === 0) {
      return NextResponse.json({
        success: true,
        message: 'No eligible invoices for auto-send',
        sent: 0,
      });
    }

    // Send S1 SMS for each eligible invoice
    const results = [];
    let successCount = 0;
    let failureCount = 0;

    for (const invoice of eligibleInvoices) {
      try {
        console.log(`[AutoSend] Sending S1 for invoice ${invoice.id} (${invoice.number})`);

        // Use HTTP for local development to avoid SSL issues
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
          successCount++;
          results.push({ invoice_id: invoice.id, invoice_number: invoice.number, success: true });
          console.log(`[AutoSend] ✓ S1 sent for invoice ${invoice.id} (${invoice.number})`);
        } else {
          failureCount++;
          results.push({ invoice_id: invoice.id, invoice_number: invoice.number, success: false, error: data.error });
          console.log(`[AutoSend] ✗ Failed to send S1 for invoice ${invoice.id}: ${data.error}`);
        }

        // Small delay between requests to avoid overwhelming SMS API
        await new Promise(resolve => setTimeout(resolve, 500));

      } catch (error: any) {
        failureCount++;
        results.push({ invoice_id: invoice.id, success: false, error: error.message });
        console.error(`[AutoSend] Error sending S1 for invoice ${invoice.id}:`, error);
      }
    }

    console.log(`[AutoSend] Completed: ${successCount} sent, ${failureCount} failed`);

    return NextResponse.json({
      success: true,
      message: `Auto-send completed: ${successCount} SMS sent, ${failureCount} failed`,
      sent: successCount,
      failed: failureCount,
      total: eligibleInvoices.length,
      results,
    });

  } catch (error: any) {
    console.error('[AutoSend] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}
