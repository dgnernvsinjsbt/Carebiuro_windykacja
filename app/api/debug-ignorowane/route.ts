import { NextRequest, NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const clientId = 211779362;

    // Test 1: Get all invoices for this client
    const { data: allInvoices } = await supabaseAdmin()
      .from('invoices')
      .select('id, client_id, outstanding, internal_note')
      .eq('client_id', clientId);

    // Test 2: Get invoices with LIKE query
    const { data: ignoredInvoices } = await supabaseAdmin()
      .from('invoices')
      .select('id, client_id, outstanding, internal_note')
      .eq('client_id', clientId)
      .like('internal_note', '%[LIST_POLECONY_IGNORED]true%');

    // Test 3: Get invoices with ILIKE query (case insensitive)
    const { data: ignoredInvoicesILike } = await supabaseAdmin()
      .from('invoices')
      .select('id, client_id, outstanding, internal_note')
      .eq('client_id', clientId)
      .ilike('internal_note', '%[LIST_POLECONY_IGNORED]true%');

    return NextResponse.json({
      clientId,
      allInvoices: allInvoices?.map(i => ({
        id: i.id,
        outstanding: i.outstanding,
        has_internal_note: !!i.internal_note,
        internal_note_length: i.internal_note?.length || 0,
        has_ignored_flag: i.internal_note?.includes('[LIST_POLECONY_IGNORED]true'),
        internal_note_preview: i.internal_note?.substring(0, 200)
      })),
      ignoredInvoices_LIKE: ignoredInvoices?.map(i => ({
        id: i.id,
        outstanding: i.outstanding
      })),
      ignoredInvoices_ILIKE: ignoredInvoicesILike?.map(i => ({
        id: i.id,
        outstanding: i.outstanding
      })),
      summary: {
        total_invoices: allInvoices?.length || 0,
        ignored_LIKE: ignoredInvoices?.length || 0,
        ignored_ILIKE: ignoredInvoicesILike?.length || 0,
        expected_outstanding_sum: allInvoices
          ?.filter(i => i.internal_note?.includes('[LIST_POLECONY_IGNORED]true'))
          .reduce((sum, i) => sum + (i.outstanding || 0), 0) || 0
      }
    });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
