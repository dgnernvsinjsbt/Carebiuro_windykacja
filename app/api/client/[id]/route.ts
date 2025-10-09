import { NextRequest, NextResponse } from 'next/server';
import { clientsDb } from '@/lib/supabase';

/**
 * GET /api/client/[id]
 * Fetch client details (email, phone) from Supabase
 * Used for lazy loading on client detail page
 */
// Force dynamic rendering - don't evaluate at build time
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const clientId = parseInt(params.id);

    if (isNaN(clientId)) {
      return NextResponse.json(
        { error: 'Invalid client ID' },
        { status: 400 }
      );
    }

    console.log(`[API] Fetching client details for ID: ${clientId}`);

    // Fetch client from Supabase (synced from Fakturownia)
    const client = await clientsDb.getById(clientId);

    if (!client) {
      return NextResponse.json(
        { error: 'Client not found' },
        { status: 404 }
      );
    }

    return NextResponse.json({
      id: client.id,
      name: client.name,
      email: client.email,
      phone: client.phone,
    });
  } catch (error: any) {
    console.error('[API] Error fetching client:', error);
    return NextResponse.json(
      { error: error.message || 'Failed to fetch client' },
      { status: 500 }
    );
  }
}
