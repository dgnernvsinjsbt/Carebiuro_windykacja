import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { parseClientFlags } from '@/lib/client-flags-v2';

export const dynamic = 'force-dynamic';

export async function GET() {
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );

  // Get all clients
  const { data: allClients, error, count } = await supabase
    .from('clients')
    .select('id, name, note', { count: 'exact' })
    .limit(10000);

  if (error) {
    return NextResponse.json({ error: error.message });
  }

  // Filter by windykacja
  const windykacjaClients = (allClients || []).filter(client => {
    const flags = parseClientFlags(client.note);
    return flags.windykacja === true;
  });

  return NextResponse.json({
    total_clients_fetched: allClients?.length || 0,
    total_in_db: count,
    windykacja_enabled: windykacjaClients.length,
    sample_windykacja: windykacjaClients.slice(0, 5).map(c => ({ id: c.id, name: c.name })),
  });
}
