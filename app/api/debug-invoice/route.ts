import { NextRequest, NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';
import { hasThirdReminder } from '@/lib/list-polecony-logic';
import { parseFiscalSync } from '@/lib/fiscal-sync-parser';
import { parseInvoiceFlags } from '@/lib/invoice-flags';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const invoice_id = searchParams.get('id') || '423246698';

  const supabase = supabaseAdmin;

  const { data: invoice, error } = await supabase()
    .from('invoices')
    .select('*')
    .eq('id', invoice_id)
    .single();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  if (!invoice) {
    return NextResponse.json({ error: 'Invoice not found' }, { status: 404 });
  }

  const fiscalSync = parseFiscalSync(invoice.internal_note);
  const hasThird = hasThirdReminder(invoice);
  const flags = parseInvoiceFlags(invoice.internal_note);

  return NextResponse.json({
    invoice: {
      id: invoice.id,
      number: invoice.number,
      client_id: invoice.client_id,
      total: invoice.total,
      status: invoice.status,
    },
    internal_note: invoice.internal_note,
    internal_note_length: invoice.internal_note?.length || 0,
    parsed_fiscal_sync: fiscalSync,
    has_third_reminder: hasThird,
    list_polecony_flags: flags,
    debug: {
      has_internal_note: !!invoice.internal_note,
      has_FISCAL_SYNC_section: invoice.internal_note?.includes('[FISCAL_SYNC]') || false,
      EMAIL_3_raw: fiscalSync?.EMAIL_3,
      SMS_3_raw: fiscalSync?.SMS_3,
      WHATSAPP_3_raw: fiscalSync?.WHATSAPP_3,
    }
  });
}
