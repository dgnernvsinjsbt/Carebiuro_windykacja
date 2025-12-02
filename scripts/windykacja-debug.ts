import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

function parseWindykacja(note: string | null): boolean {
  if (!note) return false;
  const match = note.match(/\[WINDYKACJA\](true|false)\[\/WINDYKACJA\]/i);
  return match ? match[1].toLowerCase() === 'true' : false;
}

async function main() {
  // Get clients with windykacja tag
  const { data: clients } = await supabase
    .from('clients')
    .select('id, name, note')
    .like('note', '%WINDYKACJA%');

  console.log('Klienci z tagiem WINDYKACJA w nocie:');
  for (const c of clients || []) {
    const enabled = parseWindykacja(c.note);
    console.log('- ' + c.name + ' (ID: ' + c.id + ') -> windykacja=' + enabled);
    console.log('  Note: ' + (c.note?.substring(0, 100) || 'null'));
  }
}

main().catch(console.error);
