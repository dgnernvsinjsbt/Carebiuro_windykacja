import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';
import { parseInvoiceFlags } from '@/lib/invoice-flags';

export async function GET() {
  try {
    const supabase = supabaseAdmin;

    // Oblicz datę 31 dni wstecz
    const thirtyOneDaysAgo = new Date();
    thirtyOneDaysAgo.setDate(thirtyOneDaysAgo.getDate() - 31);

    // Test 1: Wszystkie faktury ze status=sent
    const { data: sentInvoices, error: sentError } = await supabase()
      .from('invoices')
      .select('id, client_id, internal_note, status')
      .like('internal_note', '%[LIST_POLECONY_STATUS]sent%');

    // Test 2: Faktury ze status=sent i status != 'paid'
    const { data: unpaidSentInvoices, error: unpaidError } = await supabase()
      .from('invoices')
      .select('id, client_id, internal_note, status')
      .like('internal_note', '%[LIST_POLECONY_STATUS]sent%')
      .neq('status', 'paid');

    // Test 3: Analiza dat dla każdej faktury
    const invoiceAnalysis = (unpaidSentInvoices || []).map(inv => {
      const flags = parseInvoiceFlags(inv.internal_note);
      let sentDate = null;
      let daysAgo = null;
      let qualifies = false;

      if (flags.listPoleconyStatusDate) {
        sentDate = new Date(flags.listPoleconyStatusDate);
        daysAgo = Math.floor((Date.now() - sentDate.getTime()) / (1000 * 60 * 60 * 24));
        qualifies = sentDate <= thirtyOneDaysAgo && flags.listPoleconyStatus === 'sent';
      }

      return {
        invoice_id: inv.id,
        client_id: inv.client_id,
        invoice_status: inv.status,
        listPoleconyStatus: flags.listPoleconyStatus,
        listPoleconyStatusDate: flags.listPoleconyStatusDate,
        daysAgo,
        qualifiesForKaczmarski: qualifies,
      };
    });

    // Test 4: Klient 211779362 konkretnie
    const { data: clientInvoices } = await supabase()
      .from('invoices')
      .select('id, internal_note, status')
      .eq('client_id', 211779362);

    const client211779362Analysis = (clientInvoices || []).map(inv => {
      const flags = parseInvoiceFlags(inv.internal_note);
      return {
        invoice_id: inv.id,
        status: inv.status,
        has_list_polecony_status: !!flags.listPoleconyStatus,
        listPoleconyStatus: flags.listPoleconyStatus,
        listPoleconyStatusDate: flags.listPoleconyStatusDate,
      };
    });

    return NextResponse.json({
      thirtyOneDaysAgo: thirtyOneDaysAgo.toISOString(),
      test1_allSentInvoices: sentInvoices?.length || 0,
      test1_error: sentError?.message || null,

      test2_unpaidSentInvoices: unpaidSentInvoices?.length || 0,
      test2_error: unpaidError?.message || null,

      test3_invoiceAnalysis: invoiceAnalysis,
      test3_qualifyingCount: invoiceAnalysis.filter(i => i.qualifiesForKaczmarski).length,

      test4_client211779362: {
        totalInvoices: clientInvoices?.length || 0,
        invoices: client211779362Analysis,
      },
    });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
