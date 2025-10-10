import { NextRequest, NextResponse } from 'next/server';
import { fakturowniaApi } from '@/lib/fakturownia';
import { clientsDb, invoicesDb } from '@/lib/supabase';
import { Client, Invoice, FakturowniaInvoice, FakturowniaClient } from '@/types';

/**
 * POST /api/test-import
 * Safe test import: 10 clients + their invoices
 * With rate limiting protection
 */
// Force dynamic rendering - don't evaluate at build time
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  try {
    console.log('[Test Import] Starting safe import of 10 clients...');
    const startTime = Date.now();
    const log: string[] = [];

    // Step 1: Fetch first 10 clients
    log.push('Step 1: Fetching 10 clients from Fakturownia...');
    console.log('[Test Import] Fetching 10 clients...');

    const fakturowniaClients = await fakturowniaApi.getAllClients(1, 10);
    log.push(`✓ Fetched ${fakturowniaClients.length} clients`);
    console.log(`[Test Import] Got ${fakturowniaClients.length} clients`);

    // Transform to our schema
    const clients: Client[] = fakturowniaClients.map((fc: FakturowniaClient) => ({
      // Fakturownia fields (1:1 mapping)
      id: fc.id,
      name: fc.name || null,
      first_name: fc.first_name || null,
      last_name: fc.last_name || null,
      tax_no: fc.tax_no || null,
      post_code: fc.post_code || null,
      city: fc.city || null,
      street: fc.street || null,
      street_no: fc.street_no || null,
      country: fc.country || null,
      email: fc.email || null,
      phone: fc.phone || null,
      mobile_phone: fc.mobile_phone || null,
      www: fc.www || null,
      fax: fc.fax || null,
      note: fc.note || null,
      bank: fc.bank || null,
      bank_account: fc.bank_account || null,
      shortcut: fc.shortcut || null,
      kind: fc.kind || null,
      token: fc.token || null,
      discount: fc.discount || null,
      payment_to_kind: fc.payment_to_kind || null,
      category_id: fc.category_id || null,
      use_delivery_address: fc.use_delivery_address || false,
      delivery_address: fc.delivery_address || null,
      person: fc.person || null,
      use_mass_payment: fc.use_mass_payment || false,
      mass_payment_code: fc.mass_payment_code || null,
      external_id: fc.external_id || null,
      company: fc.company || false,
      title: fc.title || null,
      register_number: fc.register_number || null,
      tax_no_check: fc.tax_no_check || null,
      disable_auto_reminders: fc.disable_auto_reminders || false,
      created_at: fc.created_at || null,
      updated_at: fc.updated_at || new Date().toISOString(),

      // Our custom fields
      total_unpaid: 0, // Will calculate from invoices
    }));

    // Step 2: Save clients to Supabase
    log.push('Step 2: Saving clients to Supabase...');
    await clientsDb.bulkUpsert(clients);
    log.push(`✓ Saved ${clients.length} clients to database`);
    console.log(`[Test Import] Saved ${clients.length} clients to Supabase`);

    // Step 3: Fetch invoices for each client using client_id parameter
    log.push('Step 3: Fetching invoices for each client...');
    const allInvoices: Invoice[] = [];

    for (let i = 0; i < clients.length; i++) {
      const client = clients[i];
      console.log(`[Test Import] Fetching invoices for client ${i + 1}/${clients.length}: ${client.name}`);

      try {
        // Use the new method that fetches by client_id
        const clientInvoices = await fakturowniaApi.getInvoicesByClientId(client.id, 100);

        // Transform to our schema
        const invoices: Invoice[] = clientInvoices.map((fi: FakturowniaInvoice) => ({
          id: fi.id,
          client_id: fi.client_id,
          number: fi.number,
          total: parseFloat(fi.price_gross) || 0,
          status: fi.status,
          internal_note: fi.internal_note || null,
          email_status: fi.email_status || null,
          sent_time: fi.sent_time || null,
          updated_at: fi.updated_at,
          issue_date: fi.issue_date || null,
          sell_date: fi.sell_date || null,
          payment_to: fi.payment_to || null,
          paid_date: fi.paid_date || null,
          created_at: fi.created_at || null,
          price_net: parseFloat(fi.price_net) || null,
          price_tax: parseFloat(fi.price_tax) || null,
          paid: parseFloat(fi.paid) || null,
          currency: fi.currency || null,
          payment_type: fi.payment_type || null,
          buyer_name: fi.buyer_name || null,
          buyer_email: fi.buyer_email || null,
          buyer_phone: fi.buyer_phone || null,
          buyer_tax_no: fi.buyer_tax_no || null,
          buyer_street: fi.buyer_street || null,
          buyer_city: fi.buyer_city || null,
          buyer_post_code: fi.buyer_post_code || null,
          buyer_country: fi.buyer_country || null,
          kind: fi.kind || null,
          description: fi.description || null,
          place: fi.place || null,
          view_url: fi.view_url || null,
          payment_url: fi.payment_url || null,
          overdue: fi['overdue?'] || null,
        }));

        allInvoices.push(...invoices);

        // Calculate unpaid for this client
        const unpaidTotal = invoices
          .filter(inv => ['issued', 'sent', 'not_paid'].includes(inv.status || ''))
          .reduce((sum, inv) => sum + (inv.total || 0), 0);

        client.total_unpaid = unpaidTotal;

        log.push(`  - ${client.name}: ${invoices.length} invoices, ${unpaidTotal.toFixed(2)} PLN unpaid`);
        console.log(`[Test Import] Client ${client.id}: ${invoices.length} invoices, ${unpaidTotal.toFixed(2)} PLN unpaid`);

      } catch (error: any) {
        log.push(`  ⚠ Error fetching invoices for ${client.name}: ${error.message}`);
        console.error(`[Test Import] Error for client ${client.id}:`, error);
        client.total_unpaid = 0;
      }
    }

    log.push(`✓ Total invoices fetched: ${allInvoices.length}`);

    // Step 4: Save all invoices to Supabase
    log.push('Step 4: Saving invoices to Supabase...');
    if (allInvoices.length > 0) {
      await invoicesDb.bulkUpsert(allInvoices);
      log.push(`✓ Saved ${allInvoices.length} invoices to database`);
    } else {
      log.push('⚠ No invoices found for these clients');
    }

    // Step 5: Update clients with total_unpaid
    log.push('Step 5: Updating client totals...');
    await clientsDb.bulkUpsert(clients);
    log.push(`✓ Updated ${clients.length} clients with unpaid totals`);

    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
    log.push(`\n✅ Import complete in ${duration}s`);
    console.log(`[Test Import] Complete in ${duration}s`);

    return NextResponse.json({
      success: true,
      data: {
        imported_clients: clients.length,
        imported_invoices: allInvoices.length,
        duration_seconds: parseFloat(duration),
        clients: clients.map(c => ({
          id: c.id,
          name: c.name,
          total_unpaid: c.total_unpaid,
        })),
      },
      log: log,
    });
  } catch (error: any) {
    console.error('[Test Import] Error:', error);
    return NextResponse.json(
      {
        success: false,
        error: error.message || 'Import failed',
      },
      { status: 500 }
    );
  }
}
