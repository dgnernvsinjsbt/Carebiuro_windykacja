import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
import { resolve } from 'path';

dotenv.config({ path: resolve(process.cwd(), '.env') });

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL;
const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
const FAKTUROWNIA_TOKEN = process.env.FAKTUROWNIA_TOKEN || '1p1Eim2e_yp2ZsDRqMi3';
const FAKTUROWNIA_ACCOUNT = process.env.FAKTUROWNIA_ACCOUNT || 'cbb-office';

const supabase = createClient(SUPABASE_URL, SERVICE_KEY);

async function fetchAllFakturowniaClients() {
  const allClients = [];
  let page = 1;

  while (true) {
    const res = await fetch(
      `https://${FAKTUROWNIA_ACCOUNT}.fakturownia.pl/clients.json?page=${page}&per_page=100&api_token=${FAKTUROWNIA_TOKEN}`
    );
    const data = await res.json();

    if (!data || data.length === 0) break;
    allClients.push(...data);
    console.log(`Fetched page ${page}: ${data.length} clients`);
    page++;

    // Small delay to avoid rate limiting
    await new Promise(r => setTimeout(r, 500));
  }

  return allClients;
}

async function main() {
  console.log('Fetching all clients from Fakturownia...');
  const fakturowniaClients = await fetchAllFakturowniaClients();
  console.log(`\nTotal: ${fakturowniaClients.length} clients from Fakturownia`);

  // Find clients with [WINDYKACJA]true in their note
  const windykacjaClients = fakturowniaClients.filter(c =>
    c.note && c.note.includes('[WINDYKACJA]true')
  );

  console.log(`Found ${windykacjaClients.length} clients with windykacja=true\n`);

  // Prepare batch update data
  const clientUpdates = windykacjaClients.map(client => ({
    id: client.id,
    note: client.note,
    updated_at: new Date().toISOString()
  }));

  console.log('Updating all clients in batch using upsert...');

  // Use upsert for batch update (max 1000 per batch for Supabase)
  const batchSize = 100; // Use smaller batch to be safe
  let totalUpdated = 0;

  for (let i = 0; i < clientUpdates.length; i += batchSize) {
    const batch = clientUpdates.slice(i, i + batchSize);
    console.log(`\nUpdating batch ${Math.floor(i / batchSize) + 1} (${batch.length} clients)...`);

    const { data, error } = await supabase
      .from('clients')
      .upsert(batch, { onConflict: 'id' });

    if (error) {
      console.error(`Batch ${Math.floor(i / batchSize) + 1} failed:`, error);
    } else {
      totalUpdated += batch.length;
      console.log(`✓ Batch ${Math.floor(i / batchSize) + 1} complete (${batch.length} clients updated)`);
    }

    // Small delay between batches
    await new Promise(r => setTimeout(r, 1000));
  }

  console.log(`\n✅ Done! Updated ${totalUpdated}/${windykacjaClients.length} clients with windykacja flag`);
}

main().catch(console.error);
