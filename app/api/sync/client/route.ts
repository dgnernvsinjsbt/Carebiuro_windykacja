import { NextRequest, NextResponse } from 'next/server';
import { revalidatePath } from 'next/cache';
import { fakturowniaApi } from '@/lib/fakturownia';
import { supabase, invoicesDb } from '@/lib/supabase';
import { Invoice, FakturowniaInvoice } from '@/types';

/**
 * POST /api/sync/client
 * Sync data for a specific client:
 * 1. Fetch client data from Fakturownia (including note with WINDYKACJA tag)
 * 2. Update client in Supabase
 * 3. Fetch all invoices for this client from Fakturownia
 * 4. Upsert invoice data into Supabase (update existing, insert new)
 */
// Force dynamic rendering - don't evaluate at build time
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { client_id } = body;

    if (!client_id) {
      return NextResponse.json(
        { success: false, error: 'client_id is required' },
        { status: 400 }
      );
    }

    console.log(`[SyncClient] Starting sync for client ${client_id}...`);

    // STEP 1: Fetch client data from Fakturownia (including note)
    console.log(`[SyncClient] Fetching client data from Fakturownia...`);
    const clientData = await fakturowniaApi.getClient(client_id);
    console.log(`[SyncClient] Client data:`, {
      id: clientData.id,
      name: clientData.name,
      hasNote: !!clientData.note,
      notePreview: clientData.note?.substring(0, 100),
    });

    // STEP 2: Update client in Supabase
    console.log(`[SyncClient] Updating client in Supabase...`);
    const { error: clientUpdateError } = await supabase()
      .from('clients')
      .update({
        name: clientData.name || null,
        email: clientData.email || null,
        phone: clientData.phone || null,
        note: clientData.note || null, // WINDYKACJA tag jest tutaj
        updated_at: new Date().toISOString(),
      })
      .eq('id', client_id);

    if (clientUpdateError) {
      console.error('[SyncClient] Error updating client:', clientUpdateError);
      // Continue anyway - not critical
    } else {
      console.log('[SyncClient] ✓ Client updated');
    }

    // STEP 3: Fetch all invoices for this client from Fakturownia
    console.log(`[SyncClient] Fetching invoices from Fakturownia for client ${client_id}...`);
    const clientInvoices = await fakturowniaApi.getInvoicesByClientId(client_id, 1000);
    console.log(`[SyncClient] Fetched ${clientInvoices.length} invoices from Fakturownia`);

    // STEP 4: Transform and upsert into Supabase
    const invoicesToSync: Invoice[] = clientInvoices.map((fi: FakturowniaInvoice) => ({
      id: fi.id,
      client_id: fi.client_id,
      number: fi.number,
      total: parseFloat(fi.price_gross) || 0,
      status: fi.status,
      internal_note: fi.internal_note || null,
      email_status: fi.email_status || null,
      sent_time: fi.sent_time || null,
      updated_at: fi.updated_at,

      // Core invoice dates
      issue_date: fi.issue_date || null,
      sell_date: fi.sell_date || null,
      payment_to: fi.payment_to || null,
      paid_date: fi.paid_date || null,
      created_at: fi.created_at || null,

      // Financial data
      price_net: parseFloat(fi.price_net) || null,
      price_tax: parseFloat(fi.price_tax) || null,
      paid: parseFloat(fi.paid) || null,
      currency: fi.currency || null,
      payment_type: fi.payment_type || null,

      // Buyer information
      buyer_name: fi.buyer_name || null,
      buyer_email: fi.buyer_email || null,
      buyer_phone: fi.buyer_phone || null,
      buyer_tax_no: fi.buyer_tax_no || null,
      buyer_street: fi.buyer_street || null,
      buyer_city: fi.buyer_city || null,
      buyer_post_code: fi.buyer_post_code || null,
      buyer_country: fi.buyer_country || null,

      // Document metadata
      kind: fi.kind || null,
      description: fi.description || null,
      place: fi.place || null,
      view_url: fi.view_url || null,
      payment_url: fi.payment_url || null,

      // Status fields
      overdue: fi['overdue?'] || null,

      // Optimization flags (will be calculated later by parser)
      has_third_reminder: null,
      list_polecony_sent_date: null,
      list_polecony_ignored_date: null,
    }));

    await invoicesDb.bulkUpsert(invoicesToSync);
    console.log(`[SyncClient] ✓ Synced ${invoicesToSync.length} invoices to Supabase`);

    // Revalidate pages to show fresh data immediately
    revalidatePath('/'); // Home page
    revalidatePath(`/client/${client_id}`); // Client detail page

    return NextResponse.json({
      success: true,
      data: {
        client_id,
        synced_invoices: invoicesToSync.length,
      },
    });
  } catch (error: any) {
    console.error('[SyncClient] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to sync client invoices' },
      { status: 500 }
    );
  }
}
