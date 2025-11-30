import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

/**
 * GET /api/historia
 * Get message history from message_history table (NOT from internal_note!)
 *
 * Query params:
 * - startDate: ISO date string (e.g., 2025-10-01)
 * - endDate: ISO date string
 * - clientId: number
 * - messageType: 'email' | 'sms' | 'whatsapp'
 */
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

function getSupabaseAdmin() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);

    const filters = {
      startDate: searchParams.get('startDate') || undefined,
      endDate: searchParams.get('endDate') || undefined,
      clientId: searchParams.get('clientId') ? Number(searchParams.get('clientId')) : undefined,
      messageType: searchParams.get('messageType') as 'email' | 'sms' | 'whatsapp' | undefined,
    };

    const serverTime = new Date().toISOString();
    console.log('[Historia] Server time:', serverTime);
    console.log('[Historia] Fetching from message_history table:', filters);

    const supabase = getSupabaseAdmin();

    // First, get total count without any filters for debugging
    const { count: totalCount } = await supabase
      .from('message_history')
      .select('*', { count: 'exact', head: true });

    console.log('[Historia] Total records in message_history (no filters):', totalCount);

    // Query message_history table directly
    let query = supabase
      .from('message_history')
      .select('*')
      .order('sent_at', { ascending: false });

    // Apply date filters by comparing date part only
    if (filters.startDate) {
      console.log('[Historia] Start filter:', filters.startDate);
      // Use filter with date extraction - works with timestamptz
      query = query.filter('sent_at', 'gte', `${filters.startDate}T00:00:00Z`);
    }
    if (filters.endDate) {
      // Include entire end date by filtering < next day midnight UTC
      const [year, month, day] = filters.endDate.split('-').map(Number);
      const nextDay = new Date(Date.UTC(year, month - 1, day + 1));
      const endFilter = nextDay.toISOString();
      console.log('[Historia] End filter:', endFilter);
      query = query.filter('sent_at', 'lt', endFilter);
    }
    if (filters.clientId) {
      query = query.eq('client_id', filters.clientId);
    }
    if (filters.messageType) {
      query = query.eq('message_type', filters.messageType);
    }

    const { data: messages, error } = await query;

    // Debug: log first few messages
    if (messages && messages.length > 0) {
      console.log('[Historia] First 3 messages:', messages.slice(0, 3).map(m => ({
        id: m.id,
        invoice_number: m.invoice_number,
        sent_at: m.sent_at,
        client_name: m.client_name,
      })));
    }

    if (error) throw error;

    console.log(`[Historia] Found ${messages?.length || 0} messages in message_history`);

    // Transform to expected format
    const allMessages = (messages || []).map(msg => ({
      invoice_id: msg.invoice_id,
      invoice_number: msg.invoice_number,
      invoice_total: msg.invoice_total,
      invoice_currency: msg.invoice_currency || 'EUR',
      client_id: msg.client_id,
      client_name: msg.client_name,
      message_type: msg.message_type,
      level: msg.level,
      sent_at: msg.sent_at,
      sent_by: msg.sent_by || 'system',
      is_auto_initial: msg.is_auto_initial || false,
      status: msg.status || 'sent',
      error_message: msg.error_message,
    }));

    // Group messages by date → client → invoices
    const grouped = groupMessagesByDateAndClient(allMessages);

    const response = NextResponse.json({
      success: true,
      data: grouped,
      total: allMessages.length,
      debug: {
        source: 'message_history',
        server_time: serverTime,
        total_in_table: totalCount,
        messages_after_filter: messages?.length || 0,
        filters_applied: filters,
      },
    });

    // Disable all caching
    response.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
    response.headers.set('Pragma', 'no-cache');
    response.headers.set('Expires', '0');

    return response;
  } catch (error: any) {
    console.error('[Historia] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to fetch history' },
      { status: 500 }
    );
  }
}

/**
 * Group messages by date → client → invoices
 * Format for compact display
 */
function groupMessagesByDateAndClient(messages: any[]) {
  const grouped: Record<string, any> = {};

  messages.forEach((msg) => {
    // Group by date (YYYY-MM-DD)
    const date = new Date(msg.sent_at).toISOString().split('T')[0];

    if (!grouped[date]) {
      grouped[date] = {
        date,
        clients: {},
        totalMessages: 0,
      };
    }

    // Group by client
    const clientKey = `${msg.client_id}`;
    if (!grouped[date].clients[clientKey]) {
      grouped[date].clients[clientKey] = {
        client_id: msg.client_id,
        client_name: msg.client_name,
        invoices: {},
        messages: [],
      };
    }

    // Group by invoice
    const invoiceKey = `${msg.invoice_id}`;
    if (!grouped[date].clients[clientKey].invoices[invoiceKey]) {
      grouped[date].clients[clientKey].invoices[invoiceKey] = {
        invoice_id: msg.invoice_id,
        invoice_number: msg.invoice_number,
        invoice_total: msg.invoice_total,
        invoice_currency: msg.invoice_currency,
        messages: [],
      };
    }

    // Add message to invoice
    grouped[date].clients[clientKey].invoices[invoiceKey].messages.push({
      type: msg.message_type,
      level: msg.level,
      status: msg.status,
      sent_at: msg.sent_at,
      sent_by: msg.sent_by,
      is_auto_initial: msg.is_auto_initial,
      error_message: msg.error_message,
    });

    grouped[date].totalMessages++;
  });

  // Convert nested objects to arrays for easier rendering
  const result = Object.values(grouped).map((day: any) => ({
    date: day.date,
    totalMessages: day.totalMessages,
    clients: Object.values(day.clients).map((client: any) => ({
      ...client,
      invoices: Object.values(client.invoices),
    })),
  }));

  return result;
}
