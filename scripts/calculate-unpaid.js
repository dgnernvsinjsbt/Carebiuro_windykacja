const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

const supabase = createClient(supabaseUrl, supabaseKey);

async function calculateUnpaid() {
  console.log('📊 Calculating total_unpaid for all clients...');
  console.log('Excluding: status=paid, kind=canceled, kind=correction');

  // Fetch ALL invoices that are UNPAID (with pagination)
  let allInvoices = [];
  let page = 0;
  const pageSize = 1000;
  let hasMore = true;

  while (hasMore) {
    const { data, error } = await supabase
      .from('invoices')
      .select('client_id, total, status, kind')
      .neq('status', 'paid')          // Not paid
      .neq('kind', 'canceled')         // Not canceled
      .neq('kind', 'correction')       // Not corrections
      .range(page * pageSize, (page + 1) * pageSize - 1);

    if (error) {
      console.error('❌ Error fetching invoices:', error);
      return;
    }

    allInvoices = allInvoices.concat(data);
    hasMore = data.length === pageSize;
    page++;
    console.log(`  Fetched page ${page}: ${data.length} invoices (total: ${allInvoices.length})`);
  }

  console.log(`✓ Found ${allInvoices.length} unpaid invoices`);

  // Aggregate totals per client
  const clientTotalsMap = new Map();

  for (const inv of allInvoices) {
    if (inv.client_id) {
      const current = clientTotalsMap.get(inv.client_id) || 0;
      clientTotalsMap.set(inv.client_id, current + (inv.total || 0));
    }
  }

  console.log(`✓ Calculated totals for ${clientTotalsMap.size} clients`);

  // Fetch ALL clients (with pagination)
  let existingClients = [];
  let clientPage = 0;
  let hasMoreClients = true;

  while (hasMoreClients) {
    const { data, error } = await supabase
      .from('clients')
      .select('*')
      .range(clientPage * pageSize, (clientPage + 1) * pageSize - 1);

    if (error) {
      console.error('❌ Error fetching clients:', error);
      return;
    }

    existingClients = existingClients.concat(data);
    hasMoreClients = data.length === pageSize;
    clientPage++;
    console.log(`  Fetched client page ${clientPage}: ${data.length} clients (total: ${existingClients.length})`);
  }

  console.log(`✓ Fetched ${existingClients.length} clients from database`);

  // Update each client with their calculated total_unpaid
  let updated = 0;
  for (const client of existingClients) {
    const totalUnpaid = clientTotalsMap.get(client.id) || 0;

    const { error: updateError } = await supabase
      .from('clients')
      .update({
        total_unpaid: totalUnpaid,
        updated_at: new Date().toISOString()
      })
      .eq('id', client.id);

    if (updateError) {
      console.error(`❌ Error updating client ${client.id}:`, updateError);
    } else {
      updated++;
      if (updated % 100 === 0) {
        console.log(`  Updated ${updated}/${existingClients.length} clients...`);
      }
    }
  }

  console.log(`\n🎉 Done! Updated ${updated} clients with total_unpaid`);
}

calculateUnpaid();
