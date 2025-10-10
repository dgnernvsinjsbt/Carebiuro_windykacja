import { supabaseAdmin } from '../lib/supabase';
import { hasThirdReminder, qualifiesForListPolecony } from '../lib/list-polecony-logic';
import { parseInvoiceFlags } from '../lib/invoice-flags';

async function debug() {
  const client_id = 211779362;

  const supabase = supabaseAdmin;

  const { data: invoices } = await supabase()
    .from('invoices')
    .select('*')
    .eq('client_id', client_id);

  const { data: client } = await supabase()
    .from('clients')
    .select('*')
    .eq('id', client_id)
    .single();

  console.log(`\n=== Client ${client_id}: ${client?.name} ===`);
  console.log(`Total invoices: ${invoices?.length || 0}\n`);

  const qualifyingInvoices = [];

  for (const inv of invoices || []) {
    const hasThird = hasThirdReminder(inv);
    const flags = parseInvoiceFlags(inv.internal_note);
    const shouldShow = hasThird && flags.listPoleconyStatus !== 'sent' && flags.listPoleconyStatus !== 'ignore';

    console.log(`Invoice ${inv.number}:`);
    console.log(`  - hasThirdReminder: ${hasThird}`);
    console.log(`  - listPoleconyStatus: ${flags.listPoleconyStatus}`);
    console.log(`  - Should show: ${shouldShow}`);
    console.log('');

    if (shouldShow) {
      qualifyingInvoices.push(inv);
    }
  }

  console.log(`\n=== Summary ===`);
  console.log(`Qualifying invoices: ${qualifyingInvoices.length}`);
  console.log(`Total debt: €${qualifyingInvoices.reduce((sum, inv) => sum + (inv.total || 0), 0)}`);
  console.log(`Qualifies (ALL invoices): ${qualifiesForListPolecony(client, invoices || [])}`);
  console.log(`Qualifies (ONLY qualifying): ${qualifiesForListPolecony(client, qualifyingInvoices)}`);
}

debug();
