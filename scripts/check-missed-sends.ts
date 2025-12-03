import { createClient } from '@supabase/supabase-js';
import * as dotenv from 'dotenv';
dotenv.config();

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL as string,
  process.env.SUPABASE_SERVICE_ROLE_KEY as string
);

const FAKTUROWNIA_TOKEN = process.env.FAKTUROWNIA_TOKEN || '1p1Eim2e_yp2ZsDRqMi3';
const FAKTUROWNIA_ACCOUNT = process.env.FAKTUROWNIA_ACCOUNT || 'carebiuro';

async function fetchFakturowniaInvoices(clientId: number) {
  const res = await fetch(
    `https://${FAKTUROWNIA_ACCOUNT}.fakturownia.pl/invoices.json?client_id=${clientId}&per_page=100&api_token=${FAKTUROWNIA_TOKEN}`
  );
  return res.json();
}

async function main() {
  const today = new Date();
  const thirtyDaysAgo = new Date(today);
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

  console.log('=== MISSED SENDS ANALYSIS ===');
  console.log('Today:', today.toISOString().split('T')[0]);
  console.log('30 days ago:', thirtyDaysAgo.toISOString().split('T')[0]);
  console.log('');

  // Get all windykacja clients
  const { data: clients } = await supabase
    .from('clients')
    .select('id, name, email')
    .like('note', '%[WINDYKACJA]true%');

  console.log(`Found ${clients?.length} windykacja clients`);
  console.log('');

  const missedInvoices: any[] = [];

  for (const client of clients || []) {
    // Get invoices from Fakturownia (fresh data with internal_note)
    const invoices = await fetchFakturowniaInvoices(client.id);

    for (const inv of invoices) {
      // Skip paid/canceled
      if (inv.status === 'paid' || inv.kind === 'canceled') continue;

      // Check balance
      const balance = parseFloat(inv.price_gross || '0') - parseFloat(inv.paid || '0');
      if (balance <= 0) continue;

      // Check issue_date is 30+ days ago
      if (!inv.issue_date) continue;
      const issueDate = new Date(inv.issue_date);
      if (issueDate > thirtyDaysAgo) continue; // Not 30 days old yet

      // Check if E1 was sent (by Fakturownia or our system)
      const fakturowniaE1 = inv.email_status === 'sent' && inv.sent_time;
      const ourE1 = inv.internal_note && inv.internal_note.includes('EMAIL_1=true');

      if (!fakturowniaE1 && !ourE1) {
        missedInvoices.push({
          client_id: client.id,
          client_name: client.name,
          client_email: client.email,
          invoice_id: inv.id,
          invoice_number: inv.number,
          issue_date: inv.issue_date,
          payment_to: inv.payment_to,
          balance,
          days_since_issue: Math.floor((today.getTime() - issueDate.getTime()) / (1000 * 60 * 60 * 24)),
          internal_note: inv.internal_note || '(empty)',
          email_status: inv.email_status,
        });
      }
    }

    // Rate limit
    await new Promise(r => setTimeout(r, 300));
  }

  console.log('=== INVOICES THAT SHOULD HAVE RECEIVED E1 BUT DIDNT ===');
  console.log(`Total: ${missedInvoices.length}`);
  console.log('');

  // Sort by balance descending
  missedInvoices.sort((a, b) => b.balance - a.balance);

  for (const inv of missedInvoices.slice(0, 20)) {
    console.log(`${inv.invoice_number} - ${inv.client_name}`);
    console.log(`  Balance: €${inv.balance.toFixed(2)}`);
    console.log(`  Issue date: ${inv.issue_date} (${inv.days_since_issue} days ago)`);
    console.log(`  Payment due: ${inv.payment_to}`);
    console.log(`  Email: ${inv.client_email || 'NO EMAIL'}`);
    console.log(`  Fakturownia email_status: ${inv.email_status}`);
    console.log(`  Internal note: ${inv.internal_note.substring(0, 50)}`);
    console.log('');
  }

  if (missedInvoices.length > 20) {
    console.log(`... and ${missedInvoices.length - 20} more`);
  }

  // Summary
  const totalMissedAmount = missedInvoices.reduce((sum, inv) => sum + inv.balance, 0);
  console.log('');
  console.log('=== SUMMARY ===');
  console.log(`Invoices that qualify but never received E1: ${missedInvoices.length}`);
  console.log(`Total amount at risk: €${totalMissedAmount.toFixed(2)}`);
}

main().catch(console.error);
