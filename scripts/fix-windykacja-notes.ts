import { createClient } from '@supabase/supabase-js';
import * as dotenv from 'dotenv';
import { resolve } from 'path';

dotenv.config({ path: resolve(process.cwd(), '.env') });

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY!;
const FAKTUROWNIA_TOKEN = process.env.FAKTUROWNIA_TOKEN || '1p1Eim2e_yp2ZsDRqMi3';
const FAKTUROWNIA_ACCOUNT = process.env.FAKTUROWNIA_ACCOUNT || 'carebiuro';

const supabase = createClient(SUPABASE_URL, SERVICE_KEY);

async function fetchAllFakturowniaClients() {
  const allClients: any[] = [];
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

  // Update each one in Supabase
  let updated = 0;
  for (const client of windykacjaClients) {
    const { error } = await supabase
      .from('clients')
      .update({
        note: client.note,
        updated_at: new Date().toISOString()
      })
      .eq('id', client.id);

    if (error) {
      console.error(`Failed to update client ${client.id}:`, error.message);
    } else {
      updated++;
      const name = client.name ? client.name.substring(0, 40) : 'Unknown';
      console.log(`Updated ${client.id}: ${name}`);
    }
  }

  console.log(`\nDone! Updated ${updated}/${windykacjaClients.length} clients`);
}

main().catch(console.error);
