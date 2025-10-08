const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

const supabase = createClient(supabaseUrl, supabaseKey);

async function checkCounts() {
  const { count: clientCount } = await supabase
    .from('clients')
    .select('*', { count: 'exact', head: true });

  const { count: invoiceCount } = await supabase
    .from('invoices')
    .select('*', { count: 'exact', head: true });

  console.log(`Clients: ${clientCount}`);
  console.log(`Invoices: ${invoiceCount}`);
}

checkCounts();
