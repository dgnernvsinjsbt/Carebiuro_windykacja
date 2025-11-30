import { NextRequest, NextResponse } from 'next/server';
import { fakturowniaApi } from '@/lib/fakturownia';
import { parseFiscalSync } from '@/lib/fiscal-sync-parser';

export const dynamic = 'force-dynamic';

/**
 * Test endpoint - symuluje auto-send-overdue dla pojedynczego klienta
 * Używaj: POST /api/windykacja/test-client?client_id=136422702
 */
export async function POST(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const clientIdParam = searchParams.get('client_id');

    if (!clientIdParam) {
      return NextResponse.json(
        { error: 'Missing client_id parameter' },
        { status: 400 }
      );
    }

    const clientId = parseInt(clientIdParam);
    console.log(`[TestClient] Testing windykacja for client ${clientId}`);

    // Get invoices from Fakturownia
    const invoices = await fakturowniaApi.getInvoicesByClientId(clientId, 500);

    if (!invoices || invoices.length === 0) {
      return NextResponse.json({
        success: false,
        message: 'No invoices found for this client',
        client_id: clientId,
      });
    }

    console.log(`[TestClient] Found ${invoices.length} total invoices`);

    // Filter overdue invoices
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const overdueInvoices = invoices.filter((invoice) => {
      // Skip paid
      if (invoice.status === 'paid') return false;

      // Skip canceled
      if (invoice.kind === 'canceled') return false;

      // Skip if no balance
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
        console.log(`[TestClient] Skipping invoice ${invoice.id} - STOP=true`);
        return false;
      }

      return true;
    });

    console.log(`[TestClient] Found ${overdueInvoices.length} overdue invoices`);

    if (overdueInvoices.length === 0) {
      return NextResponse.json({
        success: true,
        message: 'No eligible overdue invoices to send reminders',
        client_id: clientId,
        total_invoices: invoices.length,
        overdue_invoices: 0,
      });
    }

    // Show what would be sent
    const results = [];
    for (const invoice of overdueInvoices) {
      const fiscalSync = parseFiscalSync(invoice.internal_note);
      const needsEmail = !fiscalSync?.EMAIL_1;
      const needsSms = !fiscalSync?.SMS_1;

      results.push({
        invoice_id: invoice.id,
        invoice_number: invoice.number,
        payment_to: invoice.payment_to,
        balance: parseFloat(invoice.price_gross || '0') - parseFloat(invoice.paid || '0'),
        needs_email_1: needsEmail,
        needs_sms_1: needsSms,
        has_internal_note: !!invoice.internal_note,
        fiscal_sync: fiscalSync,
      });
    }

    // Now actually send (only E1 for this test)
    let sentCount = 0;
    let failedCount = 0;

    for (const invoice of overdueInvoices) {
      const fiscalSync = parseFiscalSync(invoice.internal_note);

      // Try to send E1
      if (!fiscalSync?.EMAIL_1) {
        console.log(`[TestClient] Sending E1 for invoice ${invoice.id}`);

        const apiUrl = request.nextUrl.origin + '/api/reminder';

        try {
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
            console.log(`[TestClient] ✓ E1 sent for invoice ${invoice.id}`);
            sentCount++;
          } else {
            console.error(`[TestClient] ✗ Failed to send E1: ${emailData.error}`);
            failedCount++;
          }
        } catch (error: any) {
          console.error(`[TestClient] ✗ Error sending E1: ${error.message}`);
          failedCount++;
        }

        // Wait 500ms before next
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
    }

    return NextResponse.json({
      success: true,
      message: `Test completed: ${sentCount} sent, ${failedCount} failed`,
      client_id: clientId,
      total_invoices: invoices.length,
      overdue_invoices: overdueInvoices.length,
      sent: sentCount,
      failed: failedCount,
      details: results,
    });
  } catch (error: any) {
    console.error('[TestClient] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}

// Support GET for easier testing
export async function GET(request: NextRequest) {
  console.log('[TestClient] GET request received, forwarding to POST');
  return POST(request);
}
