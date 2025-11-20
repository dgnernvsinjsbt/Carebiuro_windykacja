import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
);

console.log('\n🔧 Enabling windykacja for test client...\n');

// Parse windykacja from note
function parseWindykacja(note) {
  if (!note) return false;
  return /\[WINDYKACJA\]true\[\/WINDYKACJA\]/.test(note);
}

// Find client "test"
const { data: client, error } = await supabase
  .from('clients')
  .select('id, name, note')
  .ilike('name', '%test%')
  .single();

if (error) {
  console.log('❌ Error:', error.message);
  process.exit(1);
}

if (!client) {
  console.log('❌ Client "test" not found');
  process.exit(1);
}

const currentWindykacja = parseWindykacja(client.note);

console.log(`✅ Found client: ${client.name} (ID: ${client.id})`);
console.log(`   Current windykacja: ${currentWindykacja ? '✅ ENABLED' : '❌ DISABLED'}`);
console.log(`   Note: ${client.note || '(empty)'}\n`);

if (currentWindykacja) {
  console.log('✓ Windykacja already enabled - nothing to do\n');
  process.exit(0);
}

// Update Fakturownia note to enable windykacja
console.log('📝 Updating Fakturownia note...\n');

const updatedNote = `[WINDYKACJA]true[/WINDYKACJA]\n${client.note || ''}`.trim();

const response = await fetch(
  `https://${process.env.FAKTUROWNIA_ACCOUNT}.fakturownia.pl/clients/${client.id}.json`,
  {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      api_token: process.env.FAKTUROWNIA_API_TOKEN,
      client: {
        note: updatedNote
      }
    })
  }
);

if (!response.ok) {
  console.log('❌ Failed to update Fakturownia');
  const text = await response.text();
  console.log('Response:', text);
  process.exit(1);
}

console.log('✅ Fakturownia note updated\n');

// Sync back to Supabase
console.log('🔄 Syncing back to Supabase...\n');

const { error: updateError } = await supabase
  .from('clients')
  .update({ note: updatedNote })
  .eq('id', client.id);

if (updateError) {
  console.log('⚠️  Warning: Failed to sync to Supabase:', updateError.message);
} else {
  console.log('✅ Supabase updated\n');
}

console.log('🎯 Windykacja ENABLED for client "test"\n');
console.log('Now the client will receive E1/S1 for overdue invoices at 8:15 AM daily.\n');
