import { NextRequest, NextResponse } from 'next/server';
import { fakturowniaApi } from '@/lib/fakturownia';
import { parseFiscalSync, updateFiscalSync } from '@/lib/fiscal-sync-parser';
import { parseClientFlags } from '@/lib/client-flags-v2';
import { createClient } from '@supabase/supabase-js';
import { sendEmailReminder } from '@/lib/mailgun';
import { sendSmsReminder } from '@/lib/sms';
import { invoicesDb, commentsDb, messageHistoryDb, prepareMessageHistoryEntry } from '@/lib/supabase';

/**
 * Auto-send sequence: E1→E2→E3 and S1→S2→S3
 *
 * Dwa OSOBNE tory (email i SMS nie wpływają na siebie):
 *
 * TOR EMAIL:
 * - E1 nie wysłany? → wyślij E1
 * - E1 wysłany > 14 dni temu AND E2 nie wysłany? → wyślij E2
 * - E2 wysłany > 14 dni temu AND E3 nie wysłany? → wyślij E3
 *
 * TOR SMS:
 * - S1 nie wysłany? → wyślij S1
 * - S1 wysłany > 14 dni temu AND S2 nie wysłany? → wyślij S2
 * - S2 wysłany > 14 dni temu AND S3 nie wysłany? → wyślij S3
 *
 * WARUNKI BLOKUJĄCE:
 * - Faktura zapłacona → nie wysyłaj
 * - Faktura anulowana → nie wysyłaj
 * - STOP=true → nie wysyłaj
 */

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const DAYS_BETWEEN_STEPS = 14;

// Helper: czy minęło X dni od daty?
function daysSince(date: Date | null): number {
  if (!date) return -1;
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const diff = now.getTime() - date.getTime();
  return Math.floor(diff / (1000 * 60 * 60 * 24));
}

// Helper: pobierz datę z fiscal sync
function getDate(fiscalSync: any, field: string): Date | null {
  const val = fiscalSync?.[field];
  if (!val || val === 'NULL') return null;
  return new Date(val);
}

// Helper: pobierz datę E1 (z Fakturowni lub naszego systemu)
function getE1Date(invoice: any, fiscalSync: any): Date | null {
  // Najpierw Fakturownia (email_status=sent + sent_time)
  if (invoice.email_status === 'sent' && invoice.sent_time) {
    return new Date(invoice.sent_time);
  }
  // Potem nasz system
  return getDate(fiscalSync, 'EMAIL_1_DATE');
}

export async function POST(request: NextRequest) {
  try {
    // TEST MODE
    const url = new URL(request.url);
    const testInvoiceId = url.searchParams.get('test_invoice_id');
    const isTestMode = !!testInvoiceId;

    console.log(isTestMode
      ? `[AutoSendSequence] 🧪 TEST MODE: invoice ${testInvoiceId}`
      : '[AutoSendSequence] Starting...');

    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );

    // 1. Pobierz klientów z windykacja=true
    const { data: allClients, error: clientsError } = await supabase
      .from('clients')
      .select('id, name, note');

    if (clientsError) throw clientsError;

    const windykacjaClients = (allClients || []).filter(c => {
      const flags = parseClientFlags(c.note);
      return flags.windykacja === true;
    });

    const windykacjaClientIds = windykacjaClients.map(c => c.id);
    console.log(`[AutoSendSequence] Klienci z windykacja=true: ${windykacjaClientIds.length}`);

    if (windykacjaClientIds.length === 0) {
      return NextResponse.json({
        success: true,
        message: 'Brak klientów z windykacja=true',
        sent: { email: 0, sms: 0 },
        failed: 0,
      });
    }

    // 2. Pobierz faktury tych klientów
    let invoiceQuery = supabase
      .from('invoices')
      .select('*')
      .neq('status', 'paid')
      .neq('kind', 'canceled');

    if (isTestMode) {
      invoiceQuery = invoiceQuery.eq('id', parseInt(testInvoiceId));
    } else {
      invoiceQuery = invoiceQuery.in('client_id', windykacjaClientIds);
    }

    const { data: invoices, error: invoicesError } = await invoiceQuery;
    if (invoicesError) throw invoicesError;

    console.log(`[AutoSendSequence] Faktur do sprawdzenia: ${invoices?.length || 0}`);

    let emailsSent = 0;
    let smsSent = 0;
    let failed = 0;
    const results: any[] = [];

    // 3. Dla KAŻDEJ faktury sprawdź DWA OSOBNE TORY
    for (const invoice of invoices || []) {
      const balance = (invoice.total || 0) - (invoice.paid || 0);
      if (balance <= 0) continue; // zapłacona

      const fiscalSync = parseFiscalSync(invoice.internal_note);
      if (fiscalSync?.STOP === true) {
        console.log(`[AutoSendSequence] ${invoice.number} - STOP, pomijam`);
        continue;
      }

      const client = windykacjaClients.find(c => c.id === invoice.client_id);

      // ========== TOR EMAIL ==========
      const e1Sent = fiscalSync?.EMAIL_1 === true || invoice.email_status === 'sent';
      const e2Sent = fiscalSync?.EMAIL_2 === true;
      const e3Sent = fiscalSync?.EMAIL_3 === true;
      const e1Date = getE1Date(invoice, fiscalSync);
      const e2Date = getDate(fiscalSync, 'EMAIL_2_DATE');

      let emailToSend: 1 | 2 | 3 | null = null;

      if (!e1Sent) {
        emailToSend = 1;
      } else if (!e2Sent && daysSince(e1Date) >= DAYS_BETWEEN_STEPS) {
        emailToSend = 2;
      } else if (!e3Sent && daysSince(e2Date) >= DAYS_BETWEEN_STEPS) {
        emailToSend = 3;
      }

      if (emailToSend) {
        console.log(`[AutoSendSequence] ${invoice.number} - wysyłam E${emailToSend}`);

        try {
          const emailData = {
            nazwa_klienta: invoice.buyer_name || 'Klient',
            numer_faktury: invoice.number || `#${invoice.id}`,
            kwota: balance.toFixed(2),
            waluta: invoice.currency || 'EUR',
            termin: invoice.payment_to
              ? new Date(invoice.payment_to).toLocaleDateString('pl-PL')
              : 'brak',
          };

          const templateId = `EMAIL_${emailToSend}` as 'EMAIL_1' | 'EMAIL_2' | 'EMAIL_3';
          const result = await sendEmailReminder(
            templateId,
            invoice.buyer_email || 'brak@email.com',
            emailData,
            invoice.id
          );

          if (result.success) {
            emailsSent++;

            // Aktualizuj flagi
            const flagName = `EMAIL_${emailToSend}` as 'EMAIL_1' | 'EMAIL_2' | 'EMAIL_3';
            const updatedNote = updateFiscalSync(invoice.internal_note, flagName, true, new Date().toISOString());
            await fakturowniaApi.updateInvoiceComment(invoice.id, updatedNote);
            await invoicesDb.updateComment(invoice.id, updatedNote);
            await commentsDb.logAction(invoice.id, `Sent EMAIL reminder (level ${emailToSend})`, 'local');

            try {
              const historyEntry = prepareMessageHistoryEntry(invoice, 'email', emailToSend, { sent_by: 'auto' });
              await messageHistoryDb.logMessage(historyEntry);
            } catch (e) { /* ignore history errors */ }

            results.push({
              invoice_id: invoice.id,
              invoice_number: invoice.number,
              client_name: client?.name,
              action: `EMAIL_${emailToSend}`,
              success: true,
            });
          } else {
            failed++;
            results.push({
              invoice_id: invoice.id,
              invoice_number: invoice.number,
              client_name: client?.name,
              action: `EMAIL_${emailToSend}`,
              success: false,
              error: result.error,
            });
          }
        } catch (err: any) {
          failed++;
          console.error(`[AutoSendSequence] Błąd E${emailToSend} dla ${invoice.number}:`, err.message);
        }
      }

      // ========== TOR SMS ==========
      const s1Sent = fiscalSync?.SMS_1 === true;
      const s2Sent = fiscalSync?.SMS_2 === true;
      const s3Sent = fiscalSync?.SMS_3 === true;
      const s1Date = getDate(fiscalSync, 'SMS_1_DATE');
      const s2Date = getDate(fiscalSync, 'SMS_2_DATE');

      let smsToSend: 1 | 2 | 3 | null = null;

      if (!s1Sent) {
        smsToSend = 1;
      } else if (!s2Sent && daysSince(s1Date) >= DAYS_BETWEEN_STEPS) {
        smsToSend = 2;
      } else if (!s3Sent && daysSince(s2Date) >= DAYS_BETWEEN_STEPS) {
        smsToSend = 3;
      }

      if (smsToSend) {
        if (!invoice.buyer_phone) {
          console.log(`[AutoSendSequence] ${invoice.number} - brak telefonu, S${smsToSend} pominięty`);
          failed++;
          results.push({
            invoice_id: invoice.id,
            invoice_number: invoice.number,
            client_name: client?.name,
            action: `SMS_${smsToSend}`,
            success: false,
            error: 'Brak numeru telefonu',
          });
        } else {
          console.log(`[AutoSendSequence] ${invoice.number} - wysyłam S${smsToSend}`);

          try {
            const smsData = {
              nazwa_klienta: invoice.buyer_name || 'Klient',
              numer_faktury: invoice.number || `#${invoice.id}`,
              kwota: balance.toFixed(2),
              waluta: invoice.currency || 'EUR',
              termin: invoice.payment_to
                ? new Date(invoice.payment_to).toLocaleDateString('pl-PL')
                : 'brak',
            };

            const templateKey = `REMINDER_${smsToSend}` as 'REMINDER_1' | 'REMINDER_2' | 'REMINDER_3';
            const result = await sendSmsReminder(templateKey, invoice.buyer_phone, smsData);

            if (result.success) {
              smsSent++;

              // Aktualizuj flagi
              const flagName = `SMS_${smsToSend}` as 'SMS_1' | 'SMS_2' | 'SMS_3';
              const updatedNote = updateFiscalSync(invoice.internal_note, flagName, true, new Date().toISOString());
              await fakturowniaApi.updateInvoiceComment(invoice.id, updatedNote);
              await invoicesDb.updateComment(invoice.id, updatedNote);
              await commentsDb.logAction(invoice.id, `Sent SMS reminder (level ${smsToSend})`, 'local');

              try {
                const historyEntry = prepareMessageHistoryEntry(invoice, 'sms', smsToSend, { sent_by: 'auto' });
                await messageHistoryDb.logMessage(historyEntry);
              } catch (e) { /* ignore history errors */ }

              results.push({
                invoice_id: invoice.id,
                invoice_number: invoice.number,
                client_name: client?.name,
                action: `SMS_${smsToSend}`,
                success: true,
              });
            } else {
              failed++;
              results.push({
                invoice_id: invoice.id,
                invoice_number: invoice.number,
                client_name: client?.name,
                action: `SMS_${smsToSend}`,
                success: false,
                error: result.error,
              });
            }
          } catch (err: any) {
            failed++;
            console.error(`[AutoSendSequence] Błąd S${smsToSend} dla ${invoice.number}:`, err.message);
          }
        }
      }
    }

    const totalSent = emailsSent + smsSent;
    console.log(`[AutoSendSequence] Zakończono: ${emailsSent} emaili, ${smsSent} SMS, ${failed} błędów`);

    return NextResponse.json({
      success: true,
      test_mode: isTestMode,
      message: `Wysłano: ${emailsSent} emaili, ${smsSent} SMS. Błędów: ${failed}`,
      sent: { email: emailsSent, sms: smsSent, total: totalSent },
      failed,
      invoices_checked: invoices?.length || 0,
      results,
    });

  } catch (error: any) {
    console.error('[AutoSendSequence] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  return POST(request);
}
