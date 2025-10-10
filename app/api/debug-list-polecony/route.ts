import { NextRequest, NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';
import { hasThirdReminder, qualifiesForListPolecony } from '@/lib/list-polecony-logic';
import { parseInvoiceFlags } from '@/lib/invoice-flags';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  const { client_id } = await request.json();

  const supabase = supabaseAdmin;

  // Pobierz faktury klienta
  const { data: invoices, error: invoicesError } = await supabase()
    .from('invoices')
    .select('*')
    .eq('client_id', client_id);

  if (invoicesError) {
    return NextResponse.json({ error: invoicesError.message }, { status: 500 });
  }

  // Pobierz klienta
  const { data: client, error: clientError } = await supabase()
    .from('clients')
    .select('*')
    .eq('id', client_id)
    .single();

  if (clientError) {
    return NextResponse.json({ error: clientError.message }, { status: 500 });
  }

  // Analiza faktur
  const invoicesAnalysis = (invoices || []).map(inv => {
    const hasThird = hasThirdReminder(inv);
    const flags = parseInvoiceFlags(inv.internal_note);

    return {
      id: inv.id,
      number: inv.number,
      total: inv.total,
      status: inv.status,
      hasThirdReminder: hasThird,
      listPoleconyStatus: flags.listPoleconyStatus,
      listPoleconyStatusDate: flags.listPoleconyStatusDate,
      internal_note_preview: inv.internal_note?.substring(0, 300),
    };
  });

  const invoicesWithThirdReminder = invoicesAnalysis.filter(inv => inv.hasThirdReminder);
  const invoicesExcludedBySentOrIgnore = invoicesWithThirdReminder.filter(
    inv => inv.listPoleconyStatus === 'sent' || inv.listPoleconyStatus === 'ignore'
  );
  const invoicesQualifying = invoicesWithThirdReminder.filter(
    inv => inv.listPoleconyStatus !== 'sent' && inv.listPoleconyStatus !== 'ignore'
  );

  const qualifies = qualifiesForListPolecony(client, invoices || []);

  return NextResponse.json({
    client: {
      id: client.id,
      name: client.name,
      email: client.email,
    },
    stats: {
      total_invoices: invoices?.length || 0,
      invoices_with_third_reminder: invoicesWithThirdReminder.length,
      invoices_excluded_by_sent_or_ignore: invoicesExcludedBySentOrIgnore.length,
      invoices_qualifying: invoicesQualifying.length,
      qualifies_for_list_polecony: qualifies,
    },
    invoices: invoicesAnalysis,
    invoices_qualifying_details: invoicesQualifying,
  });
}
