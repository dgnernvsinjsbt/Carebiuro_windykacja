import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';
import { parseInvoiceFlags } from '@/lib/invoice-flags';

export async function GET() {
  try {
    const supabase = supabaseAdmin;

    // Test 1: Fetch all clients
    const { data: allClients, error: clientsError } = await supabase()
      .from('clients')
      .select('*');

    // Test 2: LIKE query dla sent
    const { data: sentInvoices, error: sentError } = await supabase()
      .from('invoices')
      .select('*')
      .like('internal_note', '%[LIST_POLECONY_STATUS]sent%');

    // Test 3: Check konkretnej faktury
    const { data: invoice423246698 } = await supabase()
      .from('invoices')
      .select('id, internal_note')
      .eq('id', 423246698)
      .single();

    return NextResponse.json({
      test1_allClientsCount: allClients?.length || 0,
      test1_error: clientsError?.message || null,

      test2_sentInvoicesCount: sentInvoices?.length || 0,
      test2_invoiceIds: sentInvoices?.map(inv => inv.id) || [],
      test2_error: sentError?.message || null,

      test3_invoice423246698_exists: !!invoice423246698,
      test3_invoice423246698_hasStatus: invoice423246698?.internal_note?.includes('[LIST_POLECONY_STATUS]sent') || false,
      test3_invoice423246698_preview: invoice423246698?.internal_note?.substring(0, 200) || null,
    });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
