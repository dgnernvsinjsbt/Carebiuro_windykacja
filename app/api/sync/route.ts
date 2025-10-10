import { NextRequest, NextResponse } from 'next/server';
import { fakturowniaApi } from '@/lib/fakturownia';
import { clientsDb, invoicesDb, supabase } from '@/lib/supabase';
import { Client, Invoice, FakturowniaInvoice, FakturowniaClient } from '@/types';

/**
 * POST /api/sync
 * Full synchronization: Fakturownia → Supabase
 * PROTECTED: Only accessible via cron job with secret header
 * Runs daily at midnight (00:00)
 */
// Force dynamic rendering - don't evaluate at build time
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  try {
    // Security: Accept GitHub Actions or Vercel Cron
    const isVercelCron = request.headers.get('x-vercel-cron') === '1';
    const isGitHubAction = request.headers.get('x-github-action') === 'true';

    if (!isVercelCron && !isGitHubAction) {
      console.error('[Sync] Unauthorized: Not from Vercel Cron or GitHub Actions');
      return NextResponse.json(
        { success: false, error: 'Unauthorized' },
        { status: 401 }
      );
    }

    console.log('[Sync] Starting full synchronization...');
    const startTime = Date.now();

    // STEP 1: Clear all existing data from Supabase (fresh start)
    console.log('[Sync] STEP 1: Clearing all existing data from Supabase...');
    await invoicesDb.deleteAll();
    await clientsDb.deleteAll();
    console.log('[Sync] ✓ All data cleared');

    // STEP 2: Stream invoices + clients from Fakturownia and save to Supabase page by page
    console.log('[Sync] STEP 2: Streaming invoices from Fakturownia (ALL statuses)...');
    console.log('[Sync] Parameters: status=all, period=all, per_page=100, delay=2s');
    console.log('[Sync] Strategy: Fetch page → Create NEW clients → Save ALL invoices → Repeat');

    const seenClientIds = new Set<number>();
    let totalInvoices = 0;
    let totalClients = 0;
    let page = 1;
    let hasMore = true;

    while (hasMore) {
      // 1. Fetch one page (100 invoices)
      const pageInvoices = await fakturowniaApi.fakturowniaRequest<FakturowniaInvoice[]>(
        `/invoices.json?period=all&page=${page}&per_page=100`
      );

      if (pageInvoices.length === 0) {
        hasMore = false;
        console.log(`[Sync] ✓ Page ${page}: No more invoices`);
        break;
      }

      // 2. Extract unique client_ids from this page
      const uniqueClientIdsOnPage = new Set<number>();
      const clientDataMap = new Map<number, FakturowniaInvoice>();

      for (const invoice of pageInvoices) {
        if (invoice.client_id) {
          uniqueClientIdsOnPage.add(invoice.client_id);
          // Keep first occurrence for client data
          if (!clientDataMap.has(invoice.client_id)) {
            clientDataMap.set(invoice.client_id, invoice);
          }
        }
      }

      // 3. Create ONLY NEW clients (with real data: buyer_name, buyer_email, etc.)
      const newClientIds = Array.from(uniqueClientIdsOnPage).filter(id => !seenClientIds.has(id));

      console.log(`[Sync] Page ${page}: ${uniqueClientIdsOnPage.size} unique clients, ${newClientIds.length} new`);

      if (newClientIds.length > 0) {
        const newClients: Client[] = newClientIds.map(clientId => {
          const invoiceData = clientDataMap.get(clientId)!;
          return {
            // Fakturownia fields (minimal from invoice data)
            id: clientId,
            name: invoiceData.buyer_name || `Client ${clientId}`,
            first_name: null,
            last_name: null,
            tax_no: invoiceData.buyer_tax_no || null,
            post_code: invoiceData.buyer_post_code || null,
            city: invoiceData.buyer_city || null,
            street: invoiceData.buyer_street || null,
            street_no: null,
            country: invoiceData.buyer_country || null,
            email: invoiceData.buyer_email || null,
            phone: invoiceData.buyer_phone || null,
            mobile_phone: null,
            www: null,
            fax: null,
            note: null,
            bank: null,
            bank_account: null,
            shortcut: null,
            kind: null,
            token: null,
            discount: null,
            payment_to_kind: null,
            category_id: null,
            use_delivery_address: null,
            delivery_address: null,
            person: null,
            use_mass_payment: null,
            mass_payment_code: null,
            external_id: null,
            company: null,
            title: null,
            register_number: null,
            tax_no_check: null,
            disable_auto_reminders: null,
            created_at: null,
            updated_at: new Date().toISOString(),

            // Our custom fields
            total_unpaid: 0,
          };
        });

        console.log(`[Sync] Creating clients: ${newClientIds.slice(0, 5).join(', ')}${newClientIds.length > 5 ? '...' : ''}`);
        await clientsDb.bulkUpsert(newClients);
        newClientIds.forEach(id => seenClientIds.add(id));
        totalClients += newClientIds.length;
        console.log(`[Sync] ✓ Page ${page}: Created ${newClientIds.length} new clients (total: ${totalClients})`);
      }

      // Debug: check for invoices with missing clients
      const invoicesWithMissingClients = pageInvoices.filter(inv =>
        inv.client_id && !seenClientIds.has(inv.client_id)
      );
      if (invoicesWithMissingClients.length > 0) {
        console.error(`[Sync] ERROR: Page ${page} has ${invoicesWithMissingClients.length} invoices with missing clients!`);
        console.error(`[Sync] Missing client_ids: ${invoicesWithMissingClients.map(i => i.client_id).slice(0, 10).join(', ')}`);
      }

      // 4. Transform and save ALL invoices (for both new and existing clients)
      const invoices: Invoice[] = pageInvoices.map((fi: FakturowniaInvoice) => ({
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
      }));

      await invoicesDb.bulkUpsert(invoices);
      totalInvoices += invoices.length;
      console.log(`[Sync] ✓ Page ${page}: Saved ${invoices.length} invoices (total: ${totalInvoices})`);

      page++;
    }

    console.log(`[Sync] ✓ Streaming complete: ${totalInvoices} invoices, ${totalClients} clients`);

    // STEP 3: Fetch client notes from Fakturownia /clients.json
    console.log('[Sync] STEP 3: Fetching client notes from Fakturownia...');
    const fakturowniaClients = await fakturowniaApi.fetchAllClients();

    // Create map: clientId → note
    const clientNotesMap = new Map<number, string>();
    for (const fc of fakturowniaClients) {
      if (fc.note) {
        clientNotesMap.set(fc.id, fc.note);
      }
    }
    console.log(`[Sync] ✓ Fetched notes for ${clientNotesMap.size} clients from Fakturownia`);

    // STEP 4: Calculate total_unpaid for all clients by querying Supabase invoices
    console.log('[Sync] STEP 4: Calculating total_unpaid for all clients from Supabase invoices...');

    // Fetch all invoices grouped by client_id (excluding corrective invoices FK)
    const { data: allInvoices, error: fetchError } = await supabase()
      .from('invoices')
      .select('client_id, total, number');

    if (fetchError) {
      console.error('[Sync] Warning: Could not fetch invoices for totals:', fetchError);
      console.log('[Sync] Skipping total_unpaid update');
    } else {
      // Aggregate totals per client (excluding FK - corrective invoices)
      const clientTotalsMap = new Map<number, number>();

      for (const inv of allInvoices || []) {
        if (inv.client_id) {
          // Skip corrective invoices (FK prefix) - they shouldn't affect total_unpaid
          const isCorrectiveInvoice = inv.number && inv.number.startsWith('FK');
          if (!isCorrectiveInvoice) {
            const current = clientTotalsMap.get(inv.client_id) || 0;
            clientTotalsMap.set(inv.client_id, current + (inv.total || 0));
          }
        }
      }

      console.log(`[Sync] ✓ Calculated totals for ${clientTotalsMap.size} clients, updating...`);

      // Fetch existing clients to preserve their data
      const { data: existingClients } = await supabase()
        .from('clients')
        .select('*');

      const clientsToUpdate: Client[] = (existingClients || []).map(client => ({
        ...client, // Keep all existing fields
        note: clientNotesMap.get(client.id) || client.note || null, // Update note from Fakturownia
        total_unpaid: clientTotalsMap.get(client.id) || 0, // Update calculated total
        updated_at: new Date().toISOString(),
      }));

      await clientsDb.bulkUpsert(clientsToUpdate);
      console.log('[Sync] ✓ Client totals and notes updated');
    }

    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
    console.log(`[Sync] Synchronization complete in ${duration}s`);

    return NextResponse.json({
      success: true,
      data: {
        synced_clients: totalClients,
        synced_invoices: totalInvoices,
        duration_seconds: parseFloat(duration),
      },
    });
  } catch (error: any) {
    console.error('[Sync] Error:', error);

    // Send SMS alert on failure
    try {
      const smsFormData = new URLSearchParams();
      smsFormData.append('from', process.env.SMSPLANET_FROM || 'Carebiuro');
      smsFormData.append('to', '+48536214664');
      smsFormData.append('msg', `FULL SYNC FAILED: ${error.message.slice(0, 120)}`);

      await fetch('https://api2.smsplanet.pl/sms', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': `Bearer ${process.env.SMSPLANET_API_TOKEN}`,
        },
        body: smsFormData.toString(),
      });
    } catch (smsError) {
      console.error('[Sync] SMS alert failed:', smsError);
    }

    return NextResponse.json(
      {
        success: false,
        error: error.message || 'Synchronization failed',
      },
      { status: 500 }
    );
  }
}

/**
 * GET /api/sync?type=incremental
 * Incremental sync: Fetch only recently updated invoices
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const type = searchParams.get('type');

    if (type === 'incremental') {
      console.log('[Sync] Starting incremental sync...');

      // Fetch last 100 updated invoices
      const recentInvoices = await fakturowniaApi.getRecentInvoices(100);

      // Transform and upsert
      const invoices: Invoice[] = recentInvoices.map((fi: FakturowniaInvoice) => ({
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
      }));

      await invoicesDb.bulkUpsert(invoices);

      console.log(`[Sync] Incremental sync: ${invoices.length} invoices updated`);

      return NextResponse.json({
        success: true,
        data: {
          synced_invoices: invoices.length,
        },
      });
    }

    return NextResponse.json(
      {
        success: false,
        error: 'Invalid sync type. Use POST for full sync or GET with ?type=incremental',
      },
      { status: 400 }
    );
  } catch (error: any) {
    console.error('[Sync] Error:', error);
    return NextResponse.json(
      {
        success: false,
        error: error.message || 'Sync failed',
      },
      { status: 500 }
    );
  }
}
