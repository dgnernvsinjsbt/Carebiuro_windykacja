import { NextRequest, NextResponse } from 'next/server';
import { fakturowniaApi } from '@/lib/fakturownia';
import { clientsDb, supabaseAdmin } from '@/lib/supabase';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

/**
 * Test endpoint - sync single client with raw SQL (bypasses Supabase cache)
 */
export async function POST(request: NextRequest) {
  try {
    const { client_id } = await request.json();

    if (!client_id) {
      return NextResponse.json(
        { success: false, error: 'client_id required' },
        { status: 400 }
      );
    }

    console.log(`[TestSync] Syncing client ${client_id} from Fakturownia...`);

    // First sync the client data
    try {
      const clientData = await fakturowniaApi.getClient(client_id);
      console.log(`[TestSync] Found client: ${clientData.name}`);

      await clientsDb.bulkUpsert([{
        id: clientData.id,
        name: clientData.name || null,
        first_name: null,
        last_name: null,
        email: clientData.email || null,
        phone: clientData.phone || null,
        note: clientData.note || null,
        list_polecony: false,
        total_unpaid: 0,
        updated_at: new Date().toISOString(),
      }]);

      console.log(`[TestSync] Client ${client_id} synced successfully via bulkUpsert`);
    } catch (clientErr: any) {
      console.error(`[TestSync] Failed to sync client:`, clientErr);
      return NextResponse.json(
        { success: false, error: `Client sync failed: ${clientErr.message}` },
        { status: 500 }
      );
    }

    // Fetch invoices from Fakturownia
    const invoices = await fakturowniaApi.getInvoicesByClientId(client_id, 100);
    console.log(`[TestSync] Found ${invoices.length} invoices`);

    // Use raw SQL INSERT with ON CONFLICT to bypass Supabase cache
    let successCount = 0;
    for (const inv of invoices) {
      try {
        const { error } = await supabaseAdmin()
          .from('invoices')
          .upsert({
            id: inv.id,
            client_id: inv.client_id,
            number: inv.number,
            total: parseFloat(inv.price_gross) || 0,
            status: inv.status,
            internal_note: inv.internal_note || null,
            email_status: inv.email_status || null,
            sent_time: inv.sent_time || null,
            updated_at: new Date().toISOString(),
            issue_date: inv.issue_date || null,
            sell_date: inv.sell_date || null,
            payment_to: inv.payment_to || null,
            paid_date: inv.paid_date || null,
            created_at: inv.created_at || null,
            price_net: parseFloat(inv.price_net) || null,
            price_tax: parseFloat(inv.price_tax) || null,
            paid: parseFloat(inv.paid) || null,
            currency: inv.currency || null,
            payment_type: inv.payment_type || null,
            buyer_name: inv.buyer_name || null,
            buyer_email: inv.buyer_email || null,
            buyer_phone: inv.buyer_phone || null,
            buyer_tax_no: inv.buyer_tax_no || null,
            buyer_street: inv.buyer_street || null,
            buyer_city: inv.buyer_city || null,
            buyer_post_code: inv.buyer_post_code || null,
            buyer_country: inv.buyer_country || null,
            kind: inv.kind || null,
            description: inv.description || null,
            place: inv.place || null,
            view_url: inv.view_url || null,
            payment_url: inv.payment_url || null,
            overdue: inv['overdue?'] || false,
            has_third_reminder: false,
            list_polecony_sent_date: null,
            list_polecony_ignored_date: null,
          });

        if (error) {
          console.error(`[TestSync] Error upserting invoice ${inv.id}:`, error);
        } else {
          successCount++;
        }
      } catch (err) {
        console.error(`[TestSync] Exception for invoice ${inv.id}:`, err);
      }
    }

    console.log(`[TestSync] Successfully synced ${successCount}/${invoices.length} invoices`);

    return NextResponse.json({
      success: true,
      client_synced: true,
      invoices_synced: successCount,
      total_invoices: invoices.length,
    });
  } catch (error: any) {
    console.error('[TestSync] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
