import { NextRequest, NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';
import { hasThirdReminder } from '@/lib/list-polecony-logic';
import { parseInvoiceFlags } from '@/lib/invoice-flags';

export const dynamic = 'force-dynamic';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const clientId = parseInt(params.id);

  // Pobierz klienta
  const { data: client } = await supabaseAdmin()
    .from('clients')
    .select('*')
    .eq('id', clientId)
    .single();

  // Pobierz faktury klienta
  const { data: invoices } = await supabaseAdmin()
    .from('invoices')
    .select('*')
    .eq('client_id', clientId);

  // Analiza każdej faktury
  const analysis = invoices?.map(inv => {
    const flags = parseInvoiceFlags(inv.internal_note);
    const has3rdReminder = hasThirdReminder(inv);

    return {
      id: inv.id,
      number: inv.number,
      internal_note: inv.internal_note,
      has_third_reminder: has3rdReminder,
      list_polecony_status: flags.listPoleconyStatus,
      list_polecony_date: flags.listPoleconyStatusDate,
    };
  });

  return NextResponse.json({
    client,
    invoices: analysis,
    total_invoices: invoices?.length || 0,
    invoices_with_3rd_reminder: analysis?.filter(a => a.has_third_reminder).length || 0,
    invoices_with_sent_status: analysis?.filter(a => a.list_polecony_status === 'sent').length || 0,
  });
}