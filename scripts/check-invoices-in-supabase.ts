/**
 * Sprawdź faktury w Supabase
 */

import { supabaseAdmin } from '../lib/supabase';

async function checkInvoices() {
  const invoiceIds = [423246738, 423246698];

  console.log('Checking invoices in Supabase...\n');

  const { data: invoices, error } = await supabaseAdmin
    .from('invoices')
    .select('id, comment, list_polecony_sent_date, list_polecony_ignored_date')
    .in('id', invoiceIds);

  if (error) {
    console.error('Error:', error);
    return;
  }

  if (!invoices || invoices.length === 0) {
    console.log('No invoices found');
    return;
  }

  for (const invoice of invoices) {
    console.log(`\n📄 Invoice ${invoice.id}:`);
    console.log(`   list_polecony_sent_date: ${invoice.list_polecony_sent_date || '(null)'}`);
    console.log(`   list_polecony_ignored_date: ${invoice.list_polecony_ignored_date || '(null)'}`);
    console.log(`   comment (first 200 chars): ${(invoice.comment || '').substring(0, 200)}...`);
  }
}

checkInvoices().catch(console.error);
