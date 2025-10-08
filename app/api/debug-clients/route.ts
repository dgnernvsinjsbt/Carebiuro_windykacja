import { NextRequest, NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function GET(request: NextRequest) {
  try {
    // Count total clients
    const { count: totalCount, error: countError } = await supabaseAdmin()
      .from('clients')
      .select('*', { count: 'exact', head: true });

    if (countError) {
      console.error('[DebugClients] Count error:', countError);
    }

    // Get sample of clients
    const { data: sampleClients, error: sampleError } = await supabaseAdmin()
      .from('clients')
      .select('id, name, email, phone, total_unpaid, updated_at')
      .order('id', { ascending: true })
      .limit(10);

    if (sampleError) {
      console.error('[DebugClients] Sample error:', sampleError);
    }

    // Get test client specifically
    const { data: testClient, error: testError } = await supabaseAdmin()
      .from('clients')
      .select('*')
      .eq('id', 211779362)
      .single();

    return NextResponse.json({
      success: true,
      total_clients: totalCount || 0,
      sample_clients: sampleClients || [],
      test_client: testClient || null,
      test_client_exists: !!testClient,
      errors: {
        count: countError?.message,
        sample: sampleError?.message,
        test: testError?.message
      }
    });
  } catch (error: any) {
    console.error('[DebugClients] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}