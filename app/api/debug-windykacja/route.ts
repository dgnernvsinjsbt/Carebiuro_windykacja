import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { parseClientFlags } from '@/lib/client-flags-v2';
import { parseWindykacja } from '@/lib/windykacja-parser';
import { supabaseAdmin } from '@/lib/supabase';

export const dynamic = 'force-dynamic';

// EXACT same function as app/page.tsx fetchAllClients
async function fetchAllClientsLikeMainPage() {
  const pageSize = 1000;
  let allClients: Array<any> = [];
  let page = 0;
  let hasMore = true;

  while (hasMore) {
    const { data, error } = await supabaseAdmin()
      .from('clients')
      .select('*')
      .order('id', { ascending: true })
      .range(page * pageSize, (page + 1) * pageSize - 1);

    if (error) {
      console.error('[fetchAllClients] Error:', error);
      break;
    }

    if (data && data.length > 0) {
      allClients = allClients.concat(data);
      page++;
      hasMore = data.length === pageSize;
    } else {
      hasMore = false;
    }
  }

  return allClients;
}

// Debug endpoint pagination (anon key)
async function fetchAllClientsDebug(supabase: any) {
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

    // Fetch using BOTH methods
    const clientsDebug = await fetchAllClientsDebug(supabase);
    const clientsMainPage = await fetchAllClientsLikeMainPage();

    // Filter using BOTH parsers
    const windykacjaDebug = clientsDebug.filter(c => parseClientFlags(c.note).windykacja === true);
    const windykacjaMainPageV1 = clientsMainPage.filter(c => parseWindykacja(c.note)); // ClientsTable uses this
    const windykacjaMainPageV2 = clientsMainPage.filter(c => parseClientFlags(c.note).windykacja === true);

    // Find clients that are in debug (anon) but NOT in mainpage (service) - these are the missing 12
    const debugIds = new Set(windykacjaDebug.map(c => c.id));
    const mainpageIds = new Set(windykacjaMainPageV1.map(c => c.id));
    const missingInMainpage = windykacjaDebug.filter(c => !mainpageIds.has(c.id));

    // Compare note field for a specific missing client
    const missingClientId = missingInMainpage[0]?.id;
    const clientDebug = clientsDebug.find(c => c.id === missingClientId);
    const clientMainpage = clientsMainPage.find(c => c.id === missingClientId);

    return NextResponse.json({
      total_in_db: count,

      // Environment info
      env: {
        supabase_url: process.env.NEXT_PUBLIC_SUPABASE_URL?.substring(0, 40) + '...',
        has_service_key: !!process.env.SUPABASE_SERVICE_ROLE_KEY,
        service_key_prefix: process.env.SUPABASE_SERVICE_ROLE_KEY?.substring(0, 50) + '...',
      },

      // Debug method (anon key, select id,name,note)
      debug_method: {
        fetched: clientsDebug.length,
        windykacja_parseClientFlags: windykacjaDebug.length,
      },

      // Main page method (service key, select *)
      mainpage_method: {
        fetched: clientsMainPage.length,
        windykacja_parseWindykacja: windykacjaMainPageV1.length,
        windykacja_parseClientFlags: windykacjaMainPageV2.length,
      },

      // MISSING CLIENTS - in anon but not in service
      missing_clients: {
        count: missingInMainpage.length,
        ids: missingInMainpage.map(c => c.id),
        first_missing: missingClientId ? {
          id: missingClientId,
          note_anon: clientDebug?.note,
          note_service: clientMainpage?.note,
        } : null,
      },

      // Sample from main page method with parseWindykacja (what ClientsTable uses)
      sample_windykacja: windykacjaMainPageV1.slice(0, 10).map(c => ({
        id: c.id,
        name: c.name,
        note_preview: c.note?.substring(0, 100) || null
      })),
    });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
