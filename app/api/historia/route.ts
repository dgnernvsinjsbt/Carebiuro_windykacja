import { NextRequest, NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';
import { parseFiscalSync } from '@/lib/fiscal-sync-parser';

/**
 * GET /api/historia
 * Get message history directly from invoices' FISCAL_SYNC flags
 *
 * Query params:
 * - startDate: ISO date string (e.g., 2025-10-01)
 * - endDate: ISO date string
 * - clientId: number
 * - messageType: 'email' | 'sms' | 'whatsapp'
 * - limit: number (default 100)
 */
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);

    const filters = {
      startDate: searchParams.get('startDate') || undefined,
      endDate: searchParams.get('endDate') || undefined,
      clientId: searchParams.get('clientId') ? Number(searchParams.get('clientId')) : undefined,
      messageType: searchParams.get('messageType') as 'email' | 'sms' | 'whatsapp' | undefined,
    };

    console.log('[Historia] Fetching invoices with FISCAL_SYNC flags:', filters);

    // Fetch invoices with internal_note (contains FISCAL_SYNC from Fakturownia)
    let query = supabaseAdmin()
      .from('invoices')
      .select('id, number, client_id, internal_note, total, currency, buyer_name, issue_date')
      .not('internal_note', 'is', null);

    if (filters.clientId) {
      query = query.eq('client_id', filters.clientId);
    }

    const { data: invoices, error } = await query;

    if (error) throw error;

    console.log(`[Historia] Found ${invoices?.length || 0} invoices with internal_note`);

    // DEBUG: Log first invoice details
    if (invoices && invoices.length > 0) {
      console.log(`[Historia] First invoice sample:`, {
        id: invoices[0].id,
        number: invoices[0].number,
        has_note: !!invoices[0].internal_note,
        note_preview: invoices[0].internal_note?.substring(0, 150),
      });
    }

    // Extract all messages from FISCAL_SYNC flags
    const allMessages: any[] = [];

    for (const invoice of invoices || []) {
      const fiscalSync = parseFiscalSync(invoice.internal_note);
      if (!fiscalSync) {
        console.log(`[Historia] Invoice ${invoice.id} has no FISCAL_SYNC - skipping`);
        continue;
      }
      console.log(`[Historia] Invoice ${invoice.id} parsed FISCAL_SYNC successfully`);
      console.log(`[Historia] Invoice ${invoice.id} FISCAL_SYNC:`, {
        EMAIL_1: fiscalSync.EMAIL_1,
        EMAIL_1_DATE: fiscalSync.EMAIL_1_DATE,
        SMS_1: fiscalSync.SMS_1,
        SMS_1_DATE: fiscalSync.SMS_1_DATE,
      });

      // Check each message type and level
      const messageTypes = [
        { type: 'email', levels: [1, 2, 3] },
        { type: 'sms', levels: [1, 2, 3] },
        { type: 'whatsapp', levels: [1, 2, 3] },
      ];

      for (const { type, levels } of messageTypes) {
        // Filter by messageType if specified
        if (filters.messageType && type !== filters.messageType) continue;

        for (const level of levels) {
          const flagKey = `${type.toUpperCase()}_${level}`;
          const dateKey = `${type.toUpperCase()}_${level}_DATE`;

          const wasSent = (fiscalSync as any)[flagKey];
          const sentDate = (fiscalSync as any)[dateKey];

          if (wasSent && sentDate) {
            // Filter by date range if specified (extract date part from ISO timestamp)
            const sentDateOnly = sentDate.split('T')[0]; // Extract YYYY-MM-DD
            console.log(`[Historia] Message ${type}_${level} on invoice ${invoice.id}:`, {
              sentDate,
              sentDateOnly,
              startDate: filters.startDate,
              endDate: filters.endDate,
              passesStartFilter: !filters.startDate || sentDateOnly >= filters.startDate,
              passesEndFilter: !filters.endDate || sentDateOnly <= filters.endDate,
            });
            if (filters.startDate && sentDateOnly < filters.startDate) continue;
            if (filters.endDate && sentDateOnly > filters.endDate) continue;

            allMessages.push({
              invoice_id: invoice.id,
              invoice_number: invoice.number || `INV-${invoice.id}`,
              invoice_total: invoice.total,
              invoice_currency: invoice.currency || 'EUR',
              client_id: invoice.client_id,
              client_name: invoice.buyer_name || 'Unknown',
              message_type: type,
              level,
              sent_at: sentDate,
              sent_by: level === 1 ? 'system' : 'manual', // Level 1 = auto-send-initial
              is_auto_initial: level === 1,
              status: 'sent',
            });
          }
        }
      }
    }

    // Sort by date descending (newest first)
    allMessages.sort((a, b) => new Date(b.sent_at).getTime() - new Date(a.sent_at).getTime());

    console.log(`[Historia] Extracted ${allMessages.length} messages from FISCAL_SYNC flags`);

    // Group messages by date → client → invoices
    const grouped = groupMessagesByDateAndClient(allMessages);

    return NextResponse.json({
      success: true,
      data: grouped,
      total: allMessages.length,
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
