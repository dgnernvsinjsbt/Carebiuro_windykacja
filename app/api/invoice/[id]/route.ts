import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import { fakturowniaApi } from '@/lib/fakturownia';
import { invoicesDb, commentsDb } from '@/lib/supabase';
import { updateFiscalSync } from '@/lib/fiscal-sync-parser';

const ToggleStopSchema = z.object({
  stop: z.boolean(),
});

/**
 * GET /api/invoice/[id]
 * Get invoice details with client info and fiscal sync data
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const invoiceId = parseInt(params.id);

    if (isNaN(invoiceId)) {
      return NextResponse.json(
        { success: false, error: 'Invalid invoice ID' },
        { status: 400 }
      );
    }

    const invoice = await invoicesDb.getById(invoiceId);

    if (!invoice) {
      return NextResponse.json(
        { success: false, error: 'Invoice not found' },
        { status: 404 }
      );
    }

    return NextResponse.json({
      success: true,
      data: invoice,
    });
  } catch (error: any) {
    console.error('[Invoice] Error fetching invoice:', error);
    return NextResponse.json(
      {
        success: false,
        error: error.message || 'Failed to fetch invoice',
      },
      { status: 500 }
    );
  }
}

/**
 * PATCH /api/invoice/[id]
 * Update invoice STOP flag
 *
 * Request body: { "stop": true/false }
 */
export async function PATCH(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const invoiceId = parseInt(params.id);

    if (isNaN(invoiceId)) {
      return NextResponse.json(
        { success: false, error: 'Invalid invoice ID' },
        { status: 400 }
      );
    }

    const body = await request.json();
    const { stop } = ToggleStopSchema.parse(body);

    console.log(`[Invoice] Toggling STOP flag to ${stop} for invoice ${invoiceId}`);

    // 1. Get current invoice
    const invoice = await invoicesDb.getById(invoiceId);
    if (!invoice) {
      return NextResponse.json(
        { success: false, error: 'Invoice not found' },
        { status: 404 }
      );
    }

    // 2. Update Fiscal Sync comment
    const updatedComment = updateFiscalSync(invoice.comment, 'STOP', stop);

    // 3. Update in Fakturownia
    await fakturowniaApi.updateInvoiceComment(invoiceId, updatedComment);

    // 4. Update in Supabase
    await invoicesDb.updateComment(invoiceId, updatedComment);

    // 5. Log action
    await commentsDb.logAction(
      invoiceId,
      `STOP flag ${stop ? 'enabled' : 'disabled'}`,
      'local'
    );

    console.log(`[Invoice] STOP flag updated for invoice ${invoiceId}`);

    return NextResponse.json({
      success: true,
      data: {
        invoice_id: invoiceId,
        stop,
        updated_comment: updatedComment,
      },
    });
  } catch (error: any) {
    console.error('[Invoice] Error updating STOP flag:', error);

    if (error instanceof z.ZodError) {
      return NextResponse.json(
        {
          success: false,
          error: 'Invalid request data',
          details: error.errors,
        },
        { status: 400 }
      );
    }

    return NextResponse.json(
      {
        success: false,
        error: error.message || 'Failed to update invoice',
      },
      { status: 500 }
    );
  }
}
