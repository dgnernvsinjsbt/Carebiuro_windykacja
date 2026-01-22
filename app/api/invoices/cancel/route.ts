import { NextRequest, NextResponse } from 'next/server';
import { fakturowniaApi } from '@/lib/fakturownia';

// Force dynamic rendering - don't evaluate at build time
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { invoice_ids, client_id } = body;

    if (!invoice_ids || !Array.isArray(invoice_ids) || invoice_ids.length === 0) {
      return NextResponse.json(
        { success: false, error: 'invoice_ids array is required and must not be empty' },
        { status: 400 }
      );
    }

    if (!client_id) {
      return NextResponse.json(
        { success: false, error: 'client_id is required' },
        { status: 400 }
      );
    }

    console.log(`[CancelInvoices] Canceling ${invoice_ids.length} invoices`);

    const canceledInvoices: number[] = [];

    for (const invoiceId of invoice_ids) {
      try {
        await fakturowniaApi.fakturowniaRequest(
          '/invoices/cancel.json',
          {
            method: 'POST',
            body: JSON.stringify({
              api_token: process.env.FAKTUROWNIA_API_TOKEN,
              cancel_invoice_id: invoiceId,
              cancel_reason: 'Anulowana przez pracownika',
            }),
          }
        );
        canceledInvoices.push(invoiceId);
        console.log(`[CancelInvoices] ✓ Canceled invoice ID ${invoiceId}`);
      } catch (err: any) {
        console.error(`[CancelInvoices] Failed to cancel invoice ${invoiceId}:`, err.message);
      }
    }

    console.log(`[CancelInvoices] ✓ Canceled ${canceledInvoices.length}/${invoice_ids.length} invoices`);

    return NextResponse.json({
      success: true,
      data: {
        canceled_invoices: canceledInvoices.length,
        client_id: client_id,
      },
    });
  } catch (error: any) {
    console.error('[CancelInvoices] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to cancel invoices' },
      { status: 500 }
    );
  }
}
