import { NextRequest, NextResponse } from 'next/server';
import { revalidatePath } from 'next/cache';
import { fakturowniaApi } from '@/lib/fakturownia';
import { supabaseAdmin, invoicesDb } from '@/lib/supabase';
import { Invoice, FakturowniaInvoice } from '@/types';
import { verifyAndCleanInvoiceHash } from '@/lib/hash-verifier';

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
      phone: clientData.phone,
      mobile_phone: clientData.mobile_phone,
      email: clientData.email,
      hasNote: !!clientData.note,
      notePreview: clientData.note?.substring(0, 100),
    });

    // STEP 2: Update client in Supabase
    // Use phone OR mobile_phone (whichever is available)
    const clientPhone = clientData.phone || clientData.mobile_phone || null;
    console.log(`[SyncClient] Phone resolution: phone="${clientData.phone}" mobile_phone="${clientData.mobile_phone}" => using "${clientPhone}"`);

    const updatePayload = {
      name: clientData.name || null,
      first_name: clientData.first_name || null,
      last_name: clientData.last_name || null,
      email: clientData.email || null,
      phone: clientPhone,
      note: clientData.note || null,
      updated_at: new Date().toISOString(),
    };
    console.log(`[SyncClient] Updating client with payload:`, JSON.stringify(updatePayload));

    const { data: updateData, error: clientUpdateError } = await supabaseAdmin()
      .from('clients')
      .upsert({ id: client_id, ...updatePayload })
      .select();

    if (clientUpdateError) {
      console.error('[SyncClient] Error updating client:', JSON.stringify(clientUpdateError));
    } else {
      console.log('[SyncClient] ✓ Client updated, result:', JSON.stringify(updateData));
    }

    // STEP 3: Fetch all invoices for this client from Fakturownia
    console.log(`[SyncClient] Fetching invoices from Fakturownia for client ${client_id}...`);
    const clientInvoices = await fakturowniaApi.getInvoicesByClientId(client_id, 1000);
    console.log(`[SyncClient] Fetched ${clientInvoices.length} invoices from Fakturownia`);

    // STEP 3.5: AGGRESSIVE HASH VERIFICATION - Clean "Wystaw podobną" duplicates
    console.log(`[SyncClient] Verifying invoice hashes (detecting "Wystaw podobną" duplicates)...`);
    let cleanedCount = 0;

    for (const invoice of clientInvoices) {
      const result = await verifyAndCleanInvoiceHash(invoice, true); // cleanImmediately=true

      if (result.action === 'cleaned') {
        cleanedCount++;
        console.log(`🧹 [SyncClient] Cleaned duplicate: Invoice ${invoice.id} (hash mismatch)`);
      } else if (result.action === 'error') {
        console.error(`❌ [SyncClient] Hash verification error for invoice ${invoice.id}:`, result.message);
      }

      // Small delay between API calls to avoid rate limiting
      if (result.action === 'cleaned') {
        await new Promise(resolve => setTimeout(resolve, 100)); // 100ms delay
      }
    }

    if (cleanedCount > 0) {
      console.log(`✅ [SyncClient] Cleaned ${cleanedCount} "Wystaw podobną" duplicates`);
    } else {
      console.log(`✅ [SyncClient] No duplicates found - all hashes valid`);
    }

    // STEP 4: Transform and upsert into Supabase
    // Use client's phone as fallback if invoice's buyer_phone is empty
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
      // outstanding is a GENERATED COLUMN (calculated by Supabase as total - paid)
      currency: fi.currency || null,
      payment_type: fi.payment_type || null,

      // Buyer information
      buyer_name: fi.buyer_name || null,
      buyer_email: fi.buyer_email || null,
      // Fallback to client's phone if invoice's buyer_phone is empty
      buyer_phone: fi.buyer_phone || clientPhone,
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
    }));

    await invoicesDb.bulkUpsert(invoicesToSync);
    console.log(`[SyncClient] ✓ Synced ${invoicesToSync.length} invoices to Supabase`);

    // Revalidate pages to show fresh data immediately
    revalidatePath('/'); // Home page
    revalidatePath(`/client/${client_id}`); // Client detail page

    // VERIFY: Query the client from DB to confirm save worked
    const { data: verifyClient, error: verifyError } = await supabaseAdmin()
      .from('clients')
      .select('id, name, phone, email')
      .eq('id', client_id)
      .single();

    return NextResponse.json({
      success: true,
      data: {
        client_id,
        synced_invoices: invoicesToSync.length,
        client_phone_from_api: clientPhone,
        client_name: clientData.name,
        // Verification data - what's actually in the database now
        db_verification: verifyError ? { error: verifyError.message } : verifyClient,
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
