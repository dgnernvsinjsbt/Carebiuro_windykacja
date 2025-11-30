import { NextRequest, NextResponse } from 'next/server';
import { revalidatePath } from 'next/cache';
import { z } from 'zod';
import { fakturowniaApi } from '@/lib/fakturownia';
import { invoicesDb, commentsDb, messageHistoryDb, prepareMessageHistoryEntry } from '@/lib/supabase';
import { updateFiscalSync } from '@/lib/fiscal-sync-parser';
import { sendEmailReminder } from '@/lib/mailgun';
import { sendSmsReminder } from '@/lib/sms';

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

    // 2. Send notification
    if (type === 'sms') {
      // Send SMS directly via SMS Planet API (using template from message_templates)
      console.log(`[Reminder] Sending SMS via SMS Planet for SMS_${level}`);

      if (!invoice.buyer_phone) {
        console.error(`[SMS] ❌ No phone number for invoice ${invoice_id}`);
        return NextResponse.json(
          { success: false, error: 'Brak numeru telefonu dla tego klienta' },
          { status: 400 }
        );
      }

      const smsData = {
        nazwa_klienta: invoice.buyer_name || 'Klient',
        numer_faktury: invoice.number || `#${invoice.id}`,
        kwota: ((invoice.total || 0) - (invoice.paid || 0)).toFixed(2),
        waluta: invoice.currency || 'EUR',
        termin: invoice.payment_to
          ? new Date(invoice.payment_to).toLocaleDateString('pl-PL')
          : 'brak',
      };

      const templateKey = `REMINDER_${level}` as 'REMINDER_1' | 'REMINDER_2' | 'REMINDER_3';
      const result = await sendSmsReminder(
        templateKey,
        invoice.buyer_phone,
        smsData
      );

      if (!result.success) {
        console.error(`[Reminder] SMS send failed: ${result.error}`);
        return NextResponse.json(
          { success: false, error: `SMS send failed: ${result.error}` },
          { status: 500 }
        );
      }

      console.log(`[Reminder] SMS sent successfully: ${result.messageId}`);
    } else if (type === 'email') {
      // Send email directly via Mailgun
      console.log(`[Reminder] Sending email via Mailgun for EMAIL_${level}`);

      const emailData = {
        nazwa_klienta: invoice.buyer_name || 'Klient',
        numer_faktury: invoice.number || `#${invoice.id}`,
        kwota: ((invoice.total || 0) - (invoice.paid || 0)).toFixed(2),
        waluta: invoice.currency || 'EUR',
        termin: invoice.payment_to
          ? new Date(invoice.payment_to).toLocaleDateString('pl-PL')
          : 'brak',
      };

      const templateId = `EMAIL_${level}` as 'EMAIL_1' | 'EMAIL_2' | 'EMAIL_3';
      const result = await sendEmailReminder(
        templateId,
        invoice.buyer_email || 'brak@email.com',
        emailData,
        invoice.id // Załącz PDF faktury
      );

      if (!result.success) {
        console.error(`[Reminder] Email send failed: ${result.error}`);
        return NextResponse.json(
          { success: false, error: `Email send failed: ${result.error}` },
          { status: 500 }
        );
      }

      console.log(`[Reminder] Email sent successfully: ${result.mailgunId}`);
    } else if (type === 'whatsapp') {
      // Send webhook to n8n for whatsapp (if configured)
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
          console.log(`[Reminder] Webhook sent to n8n for whatsapp`);
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
    let historyLogged = false;
    let historyError: string | null = null;
    try {
      const historyEntry = prepareMessageHistoryEntry(
        invoice,
        type,
        level as 1 | 2 | 3,
        { sent_by: 'manual', is_auto_initial: false }
      );
      console.log(`[Reminder] Preparing history entry:`, JSON.stringify(historyEntry));
      const result = await messageHistoryDb.logMessage(historyEntry);
      console.log(`[Reminder] Message logged to history, result:`, JSON.stringify(result));
      historyLogged = true;
    } catch (err: any) {
      historyError = err?.message || String(err);
      console.error('[Reminder] Failed to log message to history:', historyError);
      // Don't fail the request if history logging fails, but report it
    }

    console.log(`[Reminder] Successfully processed ${type}_${level} for invoice ${invoice_id}`);

    // Revalidate pages to show fresh data immediately
    revalidatePath('/'); // Home page
    revalidatePath(`/client/${invoice.client_id}`); // Client detail page

    return NextResponse.json({
      success: true,
      data: {
        invoice_id,
        type,
        level,
        updated_internal_note: updatedInternalNote,
        history_logged: historyLogged,
        history_error: historyError,
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
