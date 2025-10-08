import { supabaseAdmin } from '../lib/supabase';

async function testLikeQuery() {
  console.log('Testing LIKE query for [LIST_POLECONY_STATUS]sent...\n');

  // Test 1: Sprawdź konkretną fakturę
  const { data: invoice, error: invoiceError } = await supabaseAdmin()
    .from('invoices')
    .select('id, internal_note')
    .eq('id', 423246698)
    .single();

  if (invoiceError) {
    console.error('Error fetching invoice:', invoiceError);
  } else {
    console.log('Invoice 423246698:');
    console.log('Has internal_note:', !!invoice?.internal_note);
    console.log('Contains [LIST_POLECONY_STATUS]sent:', invoice?.internal_note?.includes('[LIST_POLECONY_STATUS]sent'));
    console.log('First 200 chars:', invoice?.internal_note?.substring(0, 200));
    console.log('\n');
  }

  // Test 2: LIKE query
  const { data: likeResults, error: likeError } = await supabaseAdmin()
    .from('invoices')
    .select('id, client_id, internal_note')
    .like('internal_note', '%[LIST_POLECONY_STATUS]sent%');

  if (likeError) {
    console.error('Error with LIKE query:', likeError);
  } else {
    console.log(`LIKE query returned ${likeResults?.length || 0} results`);
    likeResults?.forEach(inv => {
      console.log(`  - Invoice ${inv.id}, Client ${inv.client_id}`);
    });
  }

  // Test 3: Sprawdź wszystkie faktury klienta 211779362
  const { data: clientInvoices, error: clientError } = await supabaseAdmin()
    .from('invoices')
    .select('id, internal_note')
    .eq('client_id', 211779362);

  if (clientError) {
    console.error('Error fetching client invoices:', clientError);
  } else {
    console.log(`\nClient 211779362 has ${clientInvoices?.length || 0} invoices:`);
    clientInvoices?.forEach(inv => {
      const hasStatus = inv.internal_note?.includes('[LIST_POLECONY_STATUS]sent');
      console.log(`  - Invoice ${inv.id}: has status=${hasStatus}`);
    });
  }
}

testLikeQuery().catch(console.error);
