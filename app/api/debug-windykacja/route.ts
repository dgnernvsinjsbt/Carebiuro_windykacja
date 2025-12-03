import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { parseClientFlags } from '@/lib/client-flags-v2';

export const dynamic = 'force-dynamic';

// Fetch all clients using pagination (Supabase has 1000 row limit per query)
async function fetchAllClients(supabase: any) {
  const allClients: any[] = [];
  const pageSize = 1000;
  let offset = 0;
  let hasMore = true;

  while (hasMore) {
    const { data, error } = await supabase
      .from('clients')
      .select('id, name, note')
      .range(offset, offset + pageSize - 1)
      .order('id', { ascending: true });

    if (error) throw error;

    if (data && data.length > 0) {
      allClients.push(...data);
      offset += pageSize;
      hasMore = data.length === pageSize;
    } else {
      hasMore = false;
    }
  }

  return allClients;
}

export async function GET() {
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );

  try {
    // Get count first
    const { count } = await supabase
      .from('clients')
      .select('*', { count: 'exact', head: true });

    // Fetch all clients using pagination
    const allClients = await fetchAllClients(supabase);

    // Filter by windykacja
    const windykacjaClients = allClients.filter(client => {
      const flags = parseClientFlags(client.note);
      return flags.windykacja === true;
    });

    return NextResponse.json({
      total_clients_fetched: allClients.length,
      total_in_db: count,
      windykacja_enabled: windykacjaClients.length,
      sample_windykacja: windykacjaClients.slice(0, 10).map(c => ({
        id: c.id,
        name: c.name,
        note_preview: c.note?.substring(0, 100) || null
      })),
    });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
