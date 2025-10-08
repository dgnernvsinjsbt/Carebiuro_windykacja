import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import { fakturowniaApi } from '@/lib/fakturownia';
import { invoicesDb, commentsDb, messageHistoryDb, prepareMessageHistoryEntry } from '@/lib/supabase';
import { updateFiscalSync } from '@/lib/fiscal-sync-parser';

// Validation schema
const ReminderSchema = z.object({
  invoice_id: z.number(),
  type: z.enum(['email', 'sms', 'whatsapp']),
  level: z.enum(['1', '2', '3']).transform(Number),
});

/**
 * POST /api/reminder
 * Send reminder and update Fiscal Sync flags
 *
 * Flow:
 * 1. Validate request
 * 2. Get invoice from Supabase
 * 3. Send webhook to n8n (for actual email/SMS/WhatsApp sending)
 * 4. Update [FISCAL_SYNC] comment in Fakturownia
 * 5. Update invoice in Supabase
 * 6. Log action to invoice_comments
 */
// Force dynamic rendering - don't evaluate at build time
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { invoice_id, type, level } = ReminderSchema.parse(body);

    console.log(`[Reminder] Processing ${type.toUpperCase()}_${level} for invoice ${invoice_id}`);

    // 1. Get invoice from Supabase
    const invoice = await invoicesDb.getById(invoice_id);
    if (!invoice) {
      return NextResponse.json(
        { success: false, error: 'Invoice not found' },
        { status: 404 }
      );
    }

    // 2. Send notification (SMS via SMS Planet API, others via n8n webhook)
    if (type === 'sms') {
      console.log(`[SMS] Starting SMS send for invoice ${invoice_id}`);
      console.log(`[SMS] Invoice details:`, {
        number: invoice.number,
        buyer_phone: invoice.buyer_phone,
        total: invoice.total,
        currency: invoice.currency,
      });

      // Send SMS directly via SMS Planet API
      if (!invoice.buyer_phone) {
        console.error(`[SMS] ❌ No phone number for invoice ${invoice_id}`);
        return NextResponse.json(
          { success: false, error: 'Brak numeru telefonu dla tego klienta' },
          { status: 400 }
        );
      }

      const smsApiToken = process.env.SMSPLANET_API_TOKEN;
      const smsFrom = process.env.SMSPLANET_FROM || 'Cbb-Office';

      console.log(`[SMS] SMS API config:`, {
        from: smsFrom,
        tokenConfigured: !!smsApiToken,
        tokenLength: smsApiToken?.length,
      });

      if (!smsApiToken) {
        console.error(`[SMS] ❌ SMSPLANET_API_TOKEN not configured in .env`);
        return NextResponse.json(
          { success: false, error: 'SMS API not configured' },
          { status: 500 }
        );
      }

      // Prepare SMS message
      const issueDate = invoice.issue_date
        ? new Date(invoice.issue_date).toLocaleDateString('pl-PL', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
          })
        : 'nieznana';

      // Calculate unpaid balance (total - paid)
      const total = typeof invoice.total === 'string' ? invoice.total : String(invoice.total || '0');
      const paid = typeof invoice.paid === 'string' ? invoice.paid : String(invoice.paid || '0');
      const balance = parseFloat(total) - parseFloat(paid);
      const balanceFormatted = balance.toFixed(2);

      const invoiceNumber = invoice.number || `#${invoice.id}`;
      const message = `Drogi kliencie, w dniu ${issueDate} na Twoj Email wyslalismy fakture ${invoiceNumber} na ${balanceFormatted} ${invoice.currency || 'EUR'}.\n\nCBB / Carebiuro`;

      console.log(`[SMS] Message prepared:`, {
        to: invoice.buyer_phone,
        from: smsFrom,
        messageLength: message.length,
        messagePreview: message.substring(0, 100) + '...',
      });

      // Create form data for SMS Planet API
      const formData = new URLSearchParams();
      formData.append('from', smsFrom);
      formData.append('to', invoice.buyer_phone);
      formData.append('msg', message);

      console.log(`[SMS] Form data created, length: ${formData.toString().length} bytes`);
      console.log(`[SMS] Calling SMS Planet API: POST https://api2.smsplanet.pl/sms`);

      try {
        const smsResponse = await fetch('https://api2.smsplanet.pl/sms', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': `Bearer ${smsApiToken}`,
          },
          body: formData.toString(),
        });

        const smsResult = await smsResponse.text();

        console.log(`[SMS] API response received:`, {
          status: smsResponse.status,
          statusText: smsResponse.statusText,
          ok: smsResponse.ok,
          headers: Object.fromEntries(smsResponse.headers.entries()),
          bodyLength: smsResult.length,
          body: smsResult,
        });

        if (!smsResponse.ok) {
          console.error(`[SMS] ❌ SMS Planet API returned error ${smsResponse.status}`);
          console.error(`[SMS] Response body:`, smsResult);
          return NextResponse.json(
            {
              success: false,
              error: `Failed to send SMS: ${smsResponse.status} ${smsResponse.statusText}`,
              details: smsResult
            },
            { status: 500 }
          );
        }

        console.log(`[SMS] ✓ SMS sent successfully to ${invoice.buyer_phone}`);
        console.log(`[SMS] SMS Planet confirmed delivery`);
      } catch (smsError: any) {
        console.error(`[SMS] ❌ Exception while sending SMS:`, {
          message: smsError.message,
          stack: smsError.stack,
          name: smsError.name,
          cause: smsError.cause,
        });
        return NextResponse.json(
          {
            success: false,
            error: 'Failed to send SMS: ' + smsError.message,
            details: smsError.stack
          },
          { status: 500 }
        );
      }
    } else {
      // Send webhook to n8n for email/whatsapp (if configured)
      const webhookUrl = getWebhookUrl(type);
      if (webhookUrl) {
        try {
          await fetch(webhookUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              invoice_id,
              invoice_number: invoice.number || `INV-${invoice.id}`,
              client_id: invoice.client_id,
              type,
              level,
              timestamp: new Date().toISOString(),
            }),
          });
          console.log(`[Reminder] Webhook sent to n8n for ${type}`);
        } catch (webhookError) {
          console.error('[Reminder] Webhook error:', webhookError);
          // Continue even if webhook fails
        }
      }
    }

    // 3. Update Fiscal Sync in Fakturownia with current timestamp
    const fieldName = `${type.toUpperCase()}_${level}` as any;
    const currentDate = new Date().toISOString();
    const updatedInternalNote = updateFiscalSync(invoice.internal_note, fieldName, true, currentDate);

    const updatedInvoice = await fakturowniaApi.updateInvoiceComment(
      invoice_id,
      updatedInternalNote
    );

    // 4. Update invoice in Supabase
    await invoicesDb.updateComment(invoice_id, updatedInternalNote);

    // 5. Log action to comments
    await commentsDb.logAction(
      invoice_id,
      `Sent ${type.toUpperCase()} reminder (level ${level})`,
      'local'
    );

    // 6. Log message to history
    try {
      const historyEntry = prepareMessageHistoryEntry(
        invoice,
        type,
        level as 1 | 2 | 3,
        { sent_by: 'manual', is_auto_initial: false }
      );
      await messageHistoryDb.logMessage(historyEntry);
      console.log(`[Reminder] Message logged to history`);
    } catch (historyError) {
      console.error('[Reminder] Failed to log message to history:', historyError);
      // Don't fail the request if history logging fails
    }

    console.log(`[Reminder] Successfully processed ${type}_${level} for invoice ${invoice_id}`);

    return NextResponse.json({
      success: true,
      data: {
        invoice_id,
        type,
        level,
        updated_comment: updatedComment,
      },
    });
  } catch (error: any) {
    console.error('[Reminder] Error:', error);

    if (error instanceof z.ZodError) {
      return NextResponse.json(
        {
          success: false,
          error: 'Invalid request data',
          details: error.errors,
        },
        { status: 400 }
      );
    }

    return NextResponse.json(
      {
        success: false,
        error: error.message || 'Failed to send reminder',
      },
      { status: 500 }
    );
  }
}

/**
 * Get n8n webhook URL based on reminder type
 * These should be configured in .env
 */
function getWebhookUrl(type: 'email' | 'sms' | 'whatsapp'): string | null {
  const urls = {
    email: process.env.N8N_WEBHOOK_EMAIL,
    sms: process.env.N8N_WEBHOOK_SMS,
    whatsapp: process.env.N8N_WEBHOOK_WHATSAPP,
  };

  return urls[type] || null;
}
