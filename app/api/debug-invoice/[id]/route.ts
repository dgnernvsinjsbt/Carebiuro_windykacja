import { NextRequest, NextResponse } from 'next/server';
import { invoicesDb } from '@/lib/supabase';

export const dynamic = 'force-dynamic';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const invoiceId = parseInt(params.id);
    const invoice = await invoicesDb.getById(invoiceId);

    if (!invoice) {
      return NextResponse.json({ error: 'Invoice not found' }, { status: 404 });
    }

    return NextResponse.json({
      id: invoice.id,
      number: invoice.number,
      has_internal_note: !!invoice.internal_note,
      internal_note_length: invoice.internal_note?.length || 0,
      internal_note_preview: invoice.internal_note?.substring(0, 200) || null,
      updated_at: invoice.updated_at,
    });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
