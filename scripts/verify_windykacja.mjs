import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
dotenv.config();

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

console.log('Checking windykacja clients in Supabase...\n');

const { data, error, count } = await supabase
  .from('clients')
  .select('id, name, note', { count: 'exact' })
  .ilike('note', '%[WINDYKACJA]true%')
  .order('name');

if (error) {
  console.error('Error:', error);
} else {
  console.log(`✅ Found ${count} clients with windykacja=true\n`);
  console.log('First 10:');
  data.slice(0, 10).forEach(c => {
    const shortName = c.name.length > 40 ? c.name.substring(0, 40) + '...' : c.name;
    console.log(`  ${c.id}: ${shortName}`);
  });
}
