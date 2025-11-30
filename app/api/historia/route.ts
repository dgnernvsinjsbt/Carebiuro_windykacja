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

    console.log('[Historia] Fetching from message_history table:', filters);

    // Query message_history table directly
    let query = getSupabaseAdmin()
      .from('message_history')
      .select('*')
      .order('sent_at', { ascending: false });

    // Apply date filters
    if (filters.startDate) {
      query = query.gte('sent_at', `${filters.startDate}T00:00:00`);
    }
    if (filters.endDate) {
      query = query.lte('sent_at', `${filters.endDate}T23:59:59`);
    }
    if (filters.clientId) {
      query = query.eq('client_id', filters.clientId);
    }
    if (filters.messageType) {
      query = query.eq('message_type', filters.messageType);
    }

    const { data: messages, error } = await query;

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

    return NextResponse.json({
      success: true,
      data: grouped,
      total: allMessages.length,
      debug: {
        source: 'message_history',
        messages_found: messages?.length || 0,
        filters_applied: filters,
      },
    });
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
