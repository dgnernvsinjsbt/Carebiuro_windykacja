import { NextRequest, NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const startDate = searchParams.get('startDate') || '2025-11-19';
    const endDate = searchParams.get('endDate') || '2025-11-19';

    console.log('[DebugHistoriaQuery] Testing query with dates:', { startDate, endDate });

    // Step 1: Get invoices with internal_note
    const { data: invoices, error } = await supabaseAdmin()
      .from('invoices')
      .select('id, number, internal_note')
      .not('internal_note', 'is', null);

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    console.log(`[DebugHistoriaQuery] Found ${invoices?.length || 0} invoices with internal_note`);

    // Step 2: Filter invoices with 2025-11-19 in internal_note
    const invoicesWithDate = invoices?.filter(inv =>
      inv.internal_note?.includes('2025-11-19')
    ) || [];

    console.log(`[DebugHistoriaQuery] Found ${invoicesWithDate.length} invoices with 2025-11-19`);

    // Step 3: Check specific invoice
    const targetInvoice = invoices?.find(inv => inv.id === 432947787);

    return NextResponse.json({
      total_invoices_with_internal_note: invoices?.length || 0,
      invoices_with_2025_11_19: invoicesWithDate.length,
      sample_invoices: invoicesWithDate.slice(0, 3).map(inv => ({
        id: inv.id,
        number: inv.number,
        has_internal_note: !!inv.internal_note,
        note_preview: inv.internal_note?.substring(0, 200),
      })),
      target_invoice_432947787: targetInvoice ? {
        id: targetInvoice.id,
        number: targetInvoice.number,
        has_note: !!targetInvoice.internal_note,
        note_preview: targetInvoice.internal_note?.substring(0, 200),
      } : 'NOT FOUND',
    });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
