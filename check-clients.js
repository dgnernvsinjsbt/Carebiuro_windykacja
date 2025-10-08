const { createClient } = require('@supabase/supabase-js');
require('dotenv').config();

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

async function checkClients() {
  console.log('Checking clients in Supabase...\n');

  // Count total clients
  const { count, error: countError } = await supabase
    .from('clients')
    .select('*', { count: 'exact', head: true });

  if (countError) {
    console.error('Count error:', countError);
  } else {
    console.log(`Total clients in database: ${count}`);
  }

  // Get sample of clients
  const { data: sample, error: sampleError } = await supabase
    .from('clients')
    .select('id, name, email')
    .limit(5);

  if (sampleError) {
    console.error('Sample error:', sampleError);
  } else {
    console.log('\nSample clients:');
    sample.forEach(c => console.log(`  - ID: ${c.id}, Name: ${c.name || 'null'}, Email: ${c.email || 'null'}`));
  }

  // Check test client
  const { data: testClient, error: testError } = await supabase
    .from('clients')
    .select('*')
    .eq('id', 211779362)
    .single();

  if (testError) {
    console.log(`\nTest client 211779362: NOT FOUND (${testError.message})`);
  } else {
    console.log(`\nTest client 211779362: FOUND`);
    console.log(`  Name: ${testClient.name}`);
    console.log(`  Email: ${testClient.email}`);
    console.log(`  Phone: ${testClient.phone}`);
  }

  process.exit(0);
}

checkClients().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});