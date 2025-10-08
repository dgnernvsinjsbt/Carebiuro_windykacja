import { NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function GET() {
  try {
    console.log('[TestSupabase] Testing supabase connection...');

    // Test 1: Check if supabase is a function
    console.log('[TestSupabase] typeof supabase:', typeof supabase);

    // Test 2: Call the function
    const client = supabase();
    console.log('[TestSupabase] Client created:', !!client);

    // Test 3: Try to fetch clients
    const { data, error, count } = await client
      .from('clients')
      .select('id, name, first_name, last_name', { count: 'exact' })
      .limit(5);

    if (error) {
      console.error('[TestSupabase] Error:', error);
      return NextResponse.json({
        success: false,
        error: error.message,
        details: error,
      });
    }

    console.log('[TestSupabase] Success! Found clients:', data?.length, 'Total count:', count);

    return NextResponse.json({
      success: true,
      clientsFound: data?.length || 0,
      totalCount: count,
      sampleClients: data,
    });
  } catch (err: any) {
    console.error('[TestSupabase] Exception:', err);
    return NextResponse.json({
      success: false,
      error: err.message,
      stack: err.stack,
    }, { status: 500 });
  }
}
