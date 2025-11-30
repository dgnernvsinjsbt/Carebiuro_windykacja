import { NextRequest, NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';
import { parseFiscalSync } from '@/lib/fiscal-sync-parser';

/**
 * GET /api/historia
 * Get message history from invoices' internal_note
 * Supports BOTH formats:
 * - New: [FISCAL_SYNC]...[/FISCAL_SYNC] with dates
 * - Legacy: "email1, sms1" or ", sms1" (uses updated_at as date)
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

/**
 * Parse legacy format internal_note (e.g., "email1, sms1" or ", sms1")
 * Returns flags found in the note
 */
function parseLegacyFormat(note: string | null): {
  EMAIL_1?: boolean;
  EMAIL_2?: boolean;
  EMAIL_3?: boolean;
  SMS_1?: boolean;
  SMS_2?: boolean;
  SMS_3?: boolean;
} | null {
  if (!note) return null;

  // Skip if it's the new format
  if (note.includes('[FISCAL_SYNC]')) return null;

  const noteLower = note.toLowerCase();
  const flags: any = {};

  // Check for email flags (email1, email2, email3, e1, e2, e3)
  if (noteLower.includes('email1') || noteLower.includes('e1')) flags.EMAIL_1 = true;
  if (noteLower.includes('email2') || noteLower.includes('e2')) flags.EMAIL_2 = true;
  if (noteLower.includes('email3') || noteLower.includes('e3')) flags.EMAIL_3 = true;

  // Check for sms flags (sms1, sms2, sms3, s1, s2, s3)
  if (noteLower.includes('sms1') || noteLower.includes('s1')) flags.SMS_1 = true;
  if (noteLower.includes('sms2') || noteLower.includes('s2')) flags.SMS_2 = true;
  if (noteLower.includes('sms3') || noteLower.includes('s3')) flags.SMS_3 = true;

  // Return null if no flags found
  if (Object.keys(flags).length === 0) return null;

  return flags;
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

    console.log('[Historia] Fetching invoices with FISCAL_SYNC flags:', filters);

    // Fetch invoices with internal_note (contains FISCAL_SYNC or legacy format)
    let query = supabaseAdmin()
      .from('invoices')
      .select('id, number, client_id, internal_note, total, currency, buyer_name, issue_date, updated_at')
      .not('internal_note', 'is', null)
      .limit(1000); // Explicitly set limit to avoid default pagination

    if (filters.clientId) {
      query = query.eq('client_id', filters.clientId);
    }

    const { data: invoices, error, count } = await query;

    if (error) throw error;

    console.log(`[Historia] Found ${invoices?.length || 0} invoices with internal_note`);

    // DEBUG: Find Wilczek specifically
    const wilczek = invoices?.find(inv => inv.buyer_name?.includes('Wilczek'));
    if (wilczek) {
      console.log('[Historia] Wilczek FOUND:', wilczek.id, wilczek.number);
    } else {
      console.log('[Historia] Wilczek NOT in results - checking why...');
    }

    // DEBUG: Log first invoice details
    if (invoices && invoices.length > 0) {
      console.log(`[Historia] First invoice sample:`, {
        id: invoices[0].id,
        number: invoices[0].number,
        has_note: !!invoices[0].internal_note,
        note_preview: invoices[0].internal_note?.substring(0, 150),
      });
    }

    // Extract all messages from FISCAL_SYNC flags OR legacy format
    const allMessages: any[] = [];
    let legacyCount = 0;
    let fiscalSyncCount = 0;

    for (const invoice of invoices || []) {
      // Try new format first
      const fiscalSync = parseFiscalSync(invoice.internal_note);

      // Try legacy format if new format not found
      const legacyFlags = !fiscalSync ? parseLegacyFormat(invoice.internal_note) : null;

      if (!fiscalSync && !legacyFlags) {
        continue; // No parseable data
      }

      // Use legacy format fallback date (updated_at or issue_date)
      const fallbackDate = invoice.updated_at || invoice.issue_date || new Date().toISOString();

      if (fiscalSync) {
        fiscalSyncCount++;
      } else if (legacyFlags) {
        legacyCount++;
      }

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

          // Check if message was sent (from either format)
          let wasSent = false;
          let sentDate: string | null = null;

          if (fiscalSync) {
            wasSent = (fiscalSync as any)[flagKey] === true;
            sentDate = (fiscalSync as any)[dateKey] || null;
          } else if (legacyFlags) {
            wasSent = (legacyFlags as any)[flagKey] === true;
            sentDate = null; // Legacy format doesn't have dates
          }

          if (wasSent) {
            // Use actual date if available, otherwise fallback
            const effectiveDate = sentDate || fallbackDate;
            const sentDateOnly = effectiveDate.split('T')[0]; // Extract YYYY-MM-DD

            // Filter by date range
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
              sent_at: effectiveDate,
              sent_by: level === 1 ? 'system' : 'manual',
              is_auto_initial: level === 1,
              status: 'sent',
              is_legacy: !fiscalSync, // Mark if from legacy format
            });
          }
        }
      }
    }

    console.log(`[Historia] Parsed: ${fiscalSyncCount} FISCAL_SYNC, ${legacyCount} legacy format`);

    // Sort by date descending (newest first)
    allMessages.sort((a, b) => new Date(b.sent_at).getTime() - new Date(a.sent_at).getTime());

    console.log(`[Historia] Extracted ${allMessages.length} messages total`);

    // Group messages by date → client → invoices
    const grouped = groupMessagesByDateAndClient(allMessages);

    return NextResponse.json({
      success: true,
      data: grouped,
      total: allMessages.length,
      debug: {
        invoices_fetched: invoices?.length || 0,
        invoices_with_fiscal_sync: fiscalSyncCount,
        invoices_with_legacy_format: legacyCount,
        messages_extracted: allMessages.length,
        wilczek_found: !!wilczek,
        wilczek_data: wilczek ? {
          id: wilczek.id,
          number: wilczek.number,
          note_preview: wilczek.internal_note?.substring(0, 200),
        } : null,
        sample_invoice: invoices?.[0] ? {
          id: invoices[0].id,
          has_note: !!invoices[0].internal_note,
          note_preview: invoices[0].internal_note?.substring(0, 100),
        } : null,
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
