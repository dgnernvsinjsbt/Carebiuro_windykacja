#!/usr/bin/env node
/**
 * Clear all data from Supabase (invoices and clients)
 */

const { createClient } = require('@supabase/supabase-js');

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL;
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!SUPABASE_URL || !SUPABASE_KEY) {
  console.error('❌ Missing Supabase environment variables');
  console.error('NEXT_PUBLIC_SUPABASE_URL:', SUPABASE_URL ? '✅' : '❌');
  console.error('NEXT_PUBLIC_SUPABASE_ANON_KEY:', SUPABASE_KEY ? '✅' : '❌');
  process.exit(1);
}

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

async function clearDatabase() {
  try {
    console.log('🗑️  Clearing Supabase database...\n');

    console.log('Deleting all invoices...');
    const { error: invoiceError } = await supabase
      .from('invoices')
      .delete()
      .neq('id', 0); // delete all (neq 0 matches everything)

    if (invoiceError) throw invoiceError;
    console.log('✅ All invoices deleted\n');

    console.log('Deleting all clients...');
    const { error: clientError } = await supabase
      .from('clients')
      .delete()
      .neq('id', 0);

    if (clientError) throw clientError;
    console.log('✅ All clients deleted\n');

    console.log('🎉 Database cleared successfully!');
  } catch (error) {
    console.error('❌ Error clearing database:', error.message);
    process.exit(1);
  }
}

clearDatabase();
