// Quick script to check invoices for client 211779362
const fs = require('fs');

const clientId = 211779362;
const envContent = fs.readFileSync('.env', 'utf8');
const apiToken = envContent.split('\n').find(line => line.startsWith('FAKTUROWNIA_API_KEY=')).split('=')[1];
const domain = 'carebiuro';

async function checkInvoices() {
  const url = `https://${domain}.fakturownia.pl/invoices.json?client_id=${clientId}&api_token=${apiToken}`;

  console.log('Fetching invoices from Fakturownia...');
  const response = await fetch(url);
  const invoices = await response.json();

  console.log(`\nFound ${invoices.length} invoices for client ${clientId}:\n`);

  invoices.forEach(inv => {
    console.log(`- Invoice ${inv.id}: ${inv.number}`);
    console.log(`  Status: ${inv.status}`);
    console.log(`  Kind: ${inv.kind}`);
    console.log(`  Comment: ${inv.internal_note?.substring(0, 100) || '(empty)'}`);
    console.log('');
  });
}

checkInvoices().catch(console.error);
