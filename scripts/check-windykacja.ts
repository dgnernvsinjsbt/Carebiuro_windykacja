import { createClient } from '@supabase/supabase-js';
import * as dotenv from 'dotenv';
dotenv.config();

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL as string,
  process.env.SUPABASE_SERVICE_ROLE_KEY as string
);

async function check() {
  const { data, count } = await supabase
    .from('clients')
    .select('id, name, note', { count: 'exact' })
    .like('note', '%[WINDYKACJA]true%');

  console.log('Windykacja clients in Supabase (service key):', count || data?.length);
  console.log('Sample:', data?.slice(0, 5).map(c => ({ id: c.id, name: c.name })));
}
check();
