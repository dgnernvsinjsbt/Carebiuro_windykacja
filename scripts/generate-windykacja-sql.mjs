import dotenv from 'dotenv';
import { resolve } from 'path';
import { writeFileSync } from 'fs';

dotenv.config({ path: resolve(process.cwd(), '.env') });

const FAKTUROWNIA_TOKEN = process.env.FAKTUROWNIA_TOKEN || '1p1Eim2e_yp2ZsDRqMi3';
const FAKTUROWNIA_ACCOUNT = process.env.FAKTUROWNIA_ACCOUNT || 'cbb-office';

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

function escapeSql(str) {
  if (!str) return 'NULL';
  return "'" + str.replace(/'/g, "''") + "'";
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

  // Generate SQL UPDATE statements
  let sql = '-- Update windykacja notes from Fakturownia\n';
  sql += `-- Generated: ${new Date().toISOString()}\n`;
  sql += `-- Total clients to update: ${windykacjaClients.length}\n\n`;

  sql += 'BEGIN;\n\n';

  for (const client of windykacjaClients) {
    const clientName = client.name ? client.name.substring(0, 40) : 'Unknown';
    sql += `-- Client ${client.id}: ${clientName}\n`;
    sql += `UPDATE clients SET note = ${escapeSql(client.note)}, updated_at = NOW() WHERE id = ${client.id};\n\n`;
  }

  sql += 'COMMIT;\n';

  // Write to file
  const sqlFile = './scripts/update-windykacja-notes.sql';
  writeFileSync(sqlFile, sql, 'utf8');

  console.log(`✅ SQL file generated: ${sqlFile}`);
  console.log(`\nTo apply these updates, run:`);
  console.log(`SUPABASE_ACCESS_TOKEN="sbp_488bb6b5a6b6e2b652b28c6c736776023117c461" npx supabase db push --dry-run --file ${sqlFile}`);
}

main().catch(console.error);
