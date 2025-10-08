const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error('Missing env variables');
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

async function clearDb() {
  console.log('🗑️  Clearing database...');

  const { error: invoicesError } = await supabase
    .from('invoices')
    .delete()
    .neq('id', 0);

  if (invoicesError) {
    console.error('Error deleting invoices:', invoicesError);
  } else {
    console.log('✅ Invoices deleted');
  }

  const { error: clientsError } = await supabase
    .from('clients')
    .delete()
    .neq('id', 0);

  if (clientsError) {
    console.error('Error deleting clients:', clientsError);
  } else {
    console.log('✅ Clients deleted');
  }

  console.log('🎉 Done!');
}

clearDb();
