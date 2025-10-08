import { NextRequest, NextResponse } from 'next/server';
import { fakturowniaApi } from '@/lib/fakturownia';
import { clientsDb, invoicesDb } from '@/lib/supabase';
import { Client, Invoice, FakturowniaInvoice, FakturowniaClient } from '@/types';

/**
 * POST /api/test-import
 * Safe test import: 10 clients + their invoices
 * With rate limiting protection
 */
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
      id: fc.id,
      name: fc.name,
      email: fc.email,
      phone: fc.phone,
      total_unpaid: 0, // Will calculate from invoices
      updated_at: new Date().toISOString(),
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
          comment: fi.internal_note || null, // Map 'internal_note' from Fakturownia to 'comment' in our DB
          email_status: fi.email_status || null,
          sent_time: fi.sent_time || null,
          updated_at: fi.updated_at,
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
