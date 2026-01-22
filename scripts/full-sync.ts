/**
 * Full Sync Script - GitHub Actions Direct Execution
 *
 * This script runs directly in GitHub Actions with no serverless timeout limits.
 * It syncs ALL invoices and clients from Fakturownia to Supabase.
 *
 * Usage: FAKTUROWNIA_API_TOKEN=xxx SUPABASE_URL=xxx SUPABASE_SERVICE_ROLE_KEY=xxx npx tsx scripts/full-sync.ts
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js';

// Types
interface FakturowniaInvoice {
  id: number;
  client_id: number;
  number: string;
  price_gross: string;
  price_net: string;
  price_tax: string;
  paid: string;
  status: string;
  internal_note: string | null;
  email_status: string | null;
  sent_time: string | null;
  updated_at: string;
  issue_date: string | null;
  sell_date: string | null;
  payment_to: string | null;
  paid_date: string | null;
  created_at: string | null;
  currency: string | null;
  payment_type: string | null;
  buyer_name: string | null;
  buyer_email: string | null;
  buyer_phone: string | null;
  buyer_tax_no: string | null;
  buyer_street: string | null;
  buyer_city: string | null;
  buyer_post_code: string | null;
  buyer_country: string | null;
  kind: string | null;
  description: string | null;
  place: string | null;
  view_url: string | null;
  payment_url: string | null;
  'overdue?': boolean | null;
}

interface FakturowniaClient {
  id: number;
  name: string;
  first_name: string | null;
  last_name: string | null;
  note: string | null;
}

// Environment
const FAKTUROWNIA_API_TOKEN = process.env.FAKTUROWNIA_API_TOKEN;
const FAKTUROWNIA_ACCOUNT = process.env.FAKTUROWNIA_ACCOUNT || 'cbb-office';
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!FAKTUROWNIA_API_TOKEN) {
  console.error('ERROR: FAKTUROWNIA_API_TOKEN is required');
  process.exit(1);
}

if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
  console.error('ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required');
  process.exit(1);
}

const supabase: SupabaseClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

// Rate limiting helper
const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// Fakturownia API helper
async function fakturowniaRequest<T>(endpoint: string): Promise<T> {
  const separator = endpoint.includes('?') ? '&' : '?';
  const url = `https://${FAKTUROWNIA_ACCOUNT}.fakturownia.pl${endpoint}${separator}api_token=${FAKTUROWNIA_API_TOKEN}`;

  const response = await fetch(url, {
    headers: { 'Accept': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Fakturownia API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

// Fetch all clients from Fakturownia (for notes and names)
async function fetchAllClients(): Promise<FakturowniaClient[]> {
  const allClients: FakturowniaClient[] = [];
  let page = 1;
  let hasMore = true;

  console.log('[Sync] Fetching all clients from Fakturownia...');

  while (hasMore) {
    const clients = await fakturowniaRequest<FakturowniaClient[]>(
      `/clients.json?page=${page}&per_page=100`
    );

    if (clients.length === 0) {
      hasMore = false;
    } else {
      allClients.push(...clients);
      if (page % 10 === 0) {
        console.log(`[Sync] ... fetched ${allClients.length} clients (page ${page})`);
      }
      page++;
      await sleep(1000); // Rate limit
    }
  }

  console.log(`[Sync] ✓ Fetched ${allClients.length} clients total`);
  return allClients;
}

// Main sync function
async function fullSync() {
  console.log('='.repeat(60));
  console.log('[Sync] FULL SYNC - GitHub Actions Direct Execution');
  console.log('='.repeat(60));
  console.log(`[Sync] Started at: ${new Date().toISOString()}`);
  console.log(`[Sync] Fakturownia account: ${FAKTUROWNIA_ACCOUNT}`);

  const startTime = Date.now();

  // STEP 1: Clear existing data
  console.log('\n[Sync] STEP 1: Clearing existing data from Supabase...');

  const { error: deleteInvoicesError } = await supabase.from('invoices').delete().neq('id', 0);
  if (deleteInvoicesError) {
    console.error('[Sync] Warning: Could not delete invoices:', deleteInvoicesError.message);
  }

  const { error: deleteClientsError } = await supabase.from('clients').delete().neq('id', 0);
  if (deleteClientsError) {
    console.error('[Sync] Warning: Could not delete clients:', deleteClientsError.message);
  }

  console.log('[Sync] ✓ Data cleared (invoice_hash_registry preserved)');

  // STEP 2: Stream invoices from Fakturownia
  console.log('\n[Sync] STEP 2: Streaming invoices from Fakturownia...');
  console.log('[Sync] Parameters: period=all, per_page=100, rate_limit=1s');

  const seenClientIds = new Set<number>();
  let totalInvoices = 0;
  let totalClients = 0;
  let page = 1;
  let hasMore = true;
  let consecutiveEmptyPages = 0;

  while (hasMore) {
    try {
      const pageInvoices = await fakturowniaRequest<FakturowniaInvoice[]>(
        `/invoices.json?period=all&page=${page}&per_page=100`
      );

      if (pageInvoices.length === 0) {
        consecutiveEmptyPages++;
        if (consecutiveEmptyPages >= 3) {
          hasMore = false;
          console.log(`[Sync] ✓ Page ${page}: End of data (${consecutiveEmptyPages} consecutive empty pages)`);
        } else {
          console.log(`[Sync] Page ${page}: Empty, checking next...`);
          page++;
          await sleep(1000);
        }
        continue;
      }

      consecutiveEmptyPages = 0;

      // Extract unique clients from this page
      const uniqueClientIdsOnPage = new Set<number>();
      const clientDataMap = new Map<number, FakturowniaInvoice>();

      for (const invoice of pageInvoices) {
        if (invoice.client_id) {
          uniqueClientIdsOnPage.add(invoice.client_id);
          if (!clientDataMap.has(invoice.client_id)) {
            clientDataMap.set(invoice.client_id, invoice);
          }
        }
      }

      // Upsert clients
      const clientIdsToUpsert = Array.from(uniqueClientIdsOnPage);
      const newClientIds = clientIdsToUpsert.filter(id => !seenClientIds.has(id));

      if (clientIdsToUpsert.length > 0) {
        const clientsToUpsert = clientIdsToUpsert.map(clientId => {
          const invoiceData = clientDataMap.get(clientId)!;
          return {
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
            total_unpaid: 0,
          };
        });

        const { error: clientError } = await supabase.from('clients').upsert(clientsToUpsert);
        if (clientError) {
          console.error(`[Sync] ERROR upserting clients on page ${page}:`, clientError.message);
        }

        newClientIds.forEach(id => seenClientIds.add(id));
        totalClients += newClientIds.length;
      }

      // Transform and save invoices
      const invoices = pageInvoices.map((fi: FakturowniaInvoice) => ({
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

      const { error: invoiceError } = await supabase.from('invoices').upsert(invoices);
      if (invoiceError) {
        console.error(`[Sync] ERROR upserting invoices on page ${page}:`, invoiceError.message);
      }

      totalInvoices += invoices.length;

      // Progress logging every 10 pages
      if (page % 10 === 0) {
        const elapsed = ((Date.now() - startTime) / 1000 / 60).toFixed(1);
        console.log(`[Sync] Page ${page}: ${totalInvoices} invoices, ${totalClients} clients (${elapsed} min)`);
      }

      page++;
      await sleep(1000); // Rate limit

    } catch (error: any) {
      console.error(`[Sync] ERROR on page ${page}:`, error.message);
      // Continue to next page on error
      page++;
      await sleep(2000);
    }
  }

  console.log(`\n[Sync] ✓ Invoice streaming complete: ${totalInvoices} invoices, ${totalClients} clients`);

  // STEP 3: Fetch client data (notes + names) from Fakturownia
  console.log('\n[Sync] STEP 3: Fetching client notes and names from Fakturownia...');

  const fakturowniaClients = await fetchAllClients();

  const clientNotesMap = new Map<number, string>();
  const clientNamesMap = new Map<number, { name: string; first_name: string | null; last_name: string | null }>();

  for (const fc of fakturowniaClients) {
    if (fc.note) {
      clientNotesMap.set(fc.id, fc.note);
    }
    clientNamesMap.set(fc.id, {
      name: fc.name,
      first_name: fc.first_name,
      last_name: fc.last_name,
    });
  }

  console.log(`[Sync] ✓ ${clientNotesMap.size} clients have notes`);

  // STEP 4: Calculate total_unpaid for all clients
  console.log('\n[Sync] STEP 4: Calculating total_unpaid for all clients...');

  // Fetch all invoices with pagination
  const allInvoices: Array<{ client_id: number | null; total: number | null; paid: number | null; number: string | null; status: string | null }> = [];
  let invoicePage = 0;
  const invoicePageSize = 1000;
  let hasMoreInvoices = true;

  while (hasMoreInvoices) {
    const { data: batch, error } = await supabase
      .from('invoices')
      .select('client_id, total, paid, number, status')
      .order('id', { ascending: true })
      .range(invoicePage * invoicePageSize, (invoicePage + 1) * invoicePageSize - 1);

    if (error) {
      console.error('[Sync] Error fetching invoices for totals:', error.message);
      break;
    }

    if (batch && batch.length > 0) {
      allInvoices.push(...batch);
      invoicePage++;
      hasMoreInvoices = batch.length === invoicePageSize;
    } else {
      hasMoreInvoices = false;
    }
  }

  console.log(`[Sync] Fetched ${allInvoices.length} invoices for total_unpaid calculation`);

  // Calculate totals per client (excluding paid and FK invoices)
  const clientTotalsMap = new Map<number, number>();

  for (const inv of allInvoices) {
    if (inv.client_id) {
      // Skip paid invoices
      if (inv.status === 'paid') continue;

      // Skip corrective invoices (FK prefix)
      if (inv.number && inv.number.startsWith('FK')) continue;

      // Calculate outstanding balance
      const outstanding = (inv.total || 0) - (inv.paid || 0);

      if (outstanding > 0) {
        const current = clientTotalsMap.get(inv.client_id) || 0;
        clientTotalsMap.set(inv.client_id, current + outstanding);
      }
    }
  }

  console.log(`[Sync] ✓ Calculated totals for ${clientTotalsMap.size} clients with unpaid balance`);

  // STEP 5: Update clients with notes and totals
  console.log('\n[Sync] STEP 5: Updating clients with notes, names, and totals...');

  // Fetch all existing clients with pagination
  const existingClients: any[] = [];
  let clientPage = 0;
  const clientPageSize = 1000;
  let hasMoreClients = true;

  while (hasMoreClients) {
    const { data: batch, error } = await supabase
      .from('clients')
      .select('*')
      .order('id', { ascending: true })
      .range(clientPage * clientPageSize, (clientPage + 1) * clientPageSize - 1);

    if (error) {
      console.error('[Sync] Error fetching clients:', error.message);
      break;
    }

    if (batch && batch.length > 0) {
      existingClients.push(...batch);
      clientPage++;
      hasMoreClients = batch.length === clientPageSize;
    } else {
      hasMoreClients = false;
    }
  }

  console.log(`[Sync] Fetched ${existingClients.length} clients for update`);

  // Update clients in batches of 500
  const batchSize = 500;
  let updatedCount = 0;

  for (let i = 0; i < existingClients.length; i += batchSize) {
    const batch = existingClients.slice(i, i + batchSize);

    const clientsToUpdate = batch.map((client: any) => {
      const nameData = clientNamesMap.get(client.id);
      return {
        ...client,
        name: nameData?.name || client.name,
        first_name: nameData?.first_name || client.first_name || null,
        last_name: nameData?.last_name || client.last_name || null,
        note: clientNotesMap.get(client.id) || client.note || null,
        total_unpaid: clientTotalsMap.get(client.id) || 0,
        updated_at: new Date().toISOString(),
      };
    });

    const { error } = await supabase.from('clients').upsert(clientsToUpdate);
    if (error) {
      console.error(`[Sync] Error updating clients batch ${i / batchSize + 1}:`, error.message);
    } else {
      updatedCount += clientsToUpdate.length;
    }
  }

  console.log(`[Sync] ✓ Updated ${updatedCount} clients`);

  // Final summary
  const duration = ((Date.now() - startTime) / 1000 / 60).toFixed(2);

  console.log('\n' + '='.repeat(60));
  console.log('[Sync] FULL SYNC COMPLETE');
  console.log('='.repeat(60));
  console.log(`[Sync] Duration: ${duration} minutes`);
  console.log(`[Sync] Total invoices: ${totalInvoices}`);
  console.log(`[Sync] Total clients: ${totalClients}`);
  console.log(`[Sync] Clients with unpaid balance: ${clientTotalsMap.size}`);
  console.log(`[Sync] Finished at: ${new Date().toISOString()}`);

  return {
    success: true,
    duration_minutes: parseFloat(duration),
    total_invoices: totalInvoices,
    total_clients: totalClients,
  };
}

// Run
fullSync()
  .then(result => {
    console.log('\n[Sync] Result:', JSON.stringify(result, null, 2));
    process.exit(0);
  })
  .catch(error => {
    console.error('\n[Sync] FATAL ERROR:', error);
    process.exit(1);
  });
