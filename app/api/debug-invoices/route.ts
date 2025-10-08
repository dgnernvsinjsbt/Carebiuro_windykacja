import { NextResponse } from 'next/server';
import { fakturowniaApi } from '@/lib/fakturownia';

export async function GET() {
  try {
    const clientId = 211779362;
    const invoices = await fakturowniaApi.getInvoicesByClientId(clientId, 1000);

    return NextResponse.json({
      success: true,
      client_id: clientId,
      count: invoices.length,
      invoices: invoices.map(inv => ({
        id: inv.id,
        number: inv.number,
        status: inv.status,
        kind: (inv as any).kind,
        comment: inv.internal_note?.substring(0, 100) || '(empty)',
      })),
    });
  } catch (error: any) {
    return NextResponse.json({
      success: false,
      error: error.message,
    }, { status: 500 });
  }
}
