import { NextRequest, NextResponse } from 'next/server';
import { fakturowniaApi } from '@/lib/fakturownia';
import { parseFiscalSync } from '@/lib/fiscal-sync-parser';
import { parseClientFlags } from '@/lib/client-flags-v2';
import { createClient } from '@supabase/supabase-js';
import type { FiscalSyncData } from '@/types';

/**
 * TEST ENDPOINT: Dry-run sequence check for a single client
 *
 * Usage: GET /api/windykacja/test-sequence?client_id=192213656&dry_run=true
 */

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const DAYS_BETWEEN_STEPS = 14;

interface SequenceStep {
  check: keyof FiscalSyncData;
  dateField: keyof FiscalSyncData;
  type: 'email' | 'sms';
  level: string;
  prevCheck?: keyof FiscalSyncData;
}

const SEQUENCE: SequenceStep[] = [
  { check: 'EMAIL_2', dateField: 'EMAIL_1_DATE', type: 'email', level: '2', prevCheck: 'EMAIL_1' },
  { check: 'EMAIL_3', dateField: 'EMAIL_2_DATE', type: 'email', level: '3', prevCheck: 'EMAIL_2' },
  { check: 'SMS_1', dateField: 'EMAIL_3_DATE', type: 'sms', level: '1', prevCheck: 'EMAIL_3' },
  { check: 'SMS_2', dateField: 'SMS_1_DATE', type: 'sms', level: '2', prevCheck: 'SMS_1' },
];

function getE1Date(invoice: any, fiscalSync: any): Date | null {
  if (fiscalSync?.EMAIL_1 && fiscalSync?.EMAIL_1_DATE) {
    return new Date(fiscalSync.EMAIL_1_DATE);
  }
  if (invoice.email_status === 'sent' && invoice.sent_time) {
    return new Date(invoice.sent_time);
  }
  return null;
}

function getDateFromFiscalSync(fiscalSync: any, dateField: string): Date | null {
  const dateValue = fiscalSync?.[dateField];
  if (!dateValue || dateValue === 'NULL') return null;
  return new Date(dateValue);
}

export async function GET(request: NextRequest) {
  try {
    const url = new URL(request.url);
    const clientId = url.searchParams.get('client_id');
    const dryRun = url.searchParams.get('dry_run') !== 'false';

    if (!clientId) {
      return NextResponse.json({ error: 'client_id required' }, { status: 400 });
    }

    console.log(`[TestSequence] Testing client ${clientId}, dry_run=${dryRun}`);

    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );

    // Get client
    const { data: client, error: clientError } = await supabase
      .from('clients')
      .select('id, name, note')
      .eq('id', parseInt(clientId))
      .single();

    if (clientError || !client) {
      return NextResponse.json({ error: 'Client not found' }, { status: 404 });
    }

    const flags = parseClientFlags(client.note);

    const clientInfo = {
      id: client.id,
      name: client.name,
      windykacja: flags.windykacja,
      note: client.note,
    };

    if (!flags.windykacja) {
      return NextResponse.json({
        success: true,
        dry_run: dryRun,
        client: clientInfo,
        message: 'Windykacja disabled for this client',
        actions: [],
      });
    }

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const fourteenDaysAgo = new Date(today);
    fourteenDaysAgo.setDate(fourteenDaysAgo.getDate() - DAYS_BETWEEN_STEPS);

    // Fetch invoices from Fakturownia (fresh data)
    const invoices = await fakturowniaApi.getInvoicesByClientId(parseInt(clientId), 100);

    const invoiceAnalysis: any[] = [];
    const plannedActions: any[] = [];

    for (const invoice of invoices) {
      const fiscalSync = parseFiscalSync(invoice.internal_note);

      // Basic info
      const invInfo: any = {
        id: invoice.id,
        number: invoice.number,
        status: invoice.status,
        total: invoice.price_gross,
        paid: invoice.paid,
        payment_to: invoice.payment_to,
        email_status: invoice.email_status,
        sent_time: invoice.sent_time,
        fiscal_sync: fiscalSync,
      };

      // Skip paid
      if (invoice.status === 'paid') {
        invInfo.skip_reason = 'paid';
        invoiceAnalysis.push(invInfo);
        continue;
      }

      // Skip canceled
      if (invoice.kind === 'canceled') {
        invInfo.skip_reason = 'canceled';
        invoiceAnalysis.push(invInfo);
        continue;
      }

      // Check balance
      const balance = parseFloat(invoice.price_gross || '0') - parseFloat(invoice.paid || '0');
      if (balance <= 0) {
        invInfo.skip_reason = 'no_balance';
        invoiceAnalysis.push(invInfo);
        continue;
      }

      // Check overdue
      if (!invoice.payment_to) {
        invInfo.skip_reason = 'no_payment_date';
        invoiceAnalysis.push(invInfo);
        continue;
      }

      const paymentDate = new Date(invoice.payment_to);
      paymentDate.setHours(0, 0, 0, 0);
      if (paymentDate >= today) {
        invInfo.skip_reason = 'not_overdue';
        invoiceAnalysis.push(invInfo);
        continue;
      }

      // Check STOP
      if (fiscalSync?.STOP === true) {
        invInfo.skip_reason = 'STOP_enabled';
        invoiceAnalysis.push(invInfo);
        continue;
      }

      invInfo.eligible = true;
      invInfo.days_overdue = Math.floor((today.getTime() - paymentDate.getTime()) / (1000 * 60 * 60 * 24));

      // Get E1 date
      const e1Date = getE1Date(invoice, fiscalSync);
      invInfo.e1_date = e1Date?.toISOString() || null;
      invInfo.e1_source = fiscalSync?.EMAIL_1 ? 'our_system' : (invoice.email_status === 'sent' ? 'fakturownia' : 'none');

      if (!e1Date) {
        invInfo.next_action = 'E1 (not sent yet - handled by auto-send-overdue)';
        invoiceAnalysis.push(invInfo);
        continue;
      }

      const daysSinceE1 = Math.floor((today.getTime() - e1Date.getTime()) / (1000 * 60 * 60 * 24));
      invInfo.days_since_e1 = daysSinceE1;

      // Check sequence
      for (const step of SEQUENCE) {
        // Skip if already done
        if (fiscalSync?.[step.check] === true) {
          continue;
        }

        // Check previous step
        if (step.prevCheck && fiscalSync?.[step.prevCheck] !== true) {
          if (step.check === 'EMAIL_2') {
            if (invoice.email_status !== 'sent') {
              continue;
            }
          } else {
            continue;
          }
        }

        // Get previous date
        let prevDate: Date | null = null;
        if (step.dateField === 'EMAIL_1_DATE') {
          prevDate = e1Date;
        } else {
          prevDate = getDateFromFiscalSync(fiscalSync, step.dateField);
        }

        if (!prevDate) {
          continue;
        }

        const daysSincePrev = Math.floor((today.getTime() - prevDate.getTime()) / (1000 * 60 * 60 * 24));

        if (prevDate > fourteenDaysAgo) {
          invInfo.next_action = `Waiting: ${step.type.toUpperCase()}_${step.level} in ${DAYS_BETWEEN_STEPS - daysSincePrev} days`;
          break;
        }

        // Ready to send!
        const action = {
          invoice_id: invoice.id,
          invoice_number: invoice.number,
          action: `${step.type.toUpperCase()}_${step.level}`,
          reason: `Previous action (${step.dateField}) was ${daysSincePrev} days ago (> ${DAYS_BETWEEN_STEPS} days)`,
          would_send: !dryRun,
        };

        plannedActions.push(action);
        invInfo.next_action = `SEND ${step.type.toUpperCase()}_${step.level}`;

        // Actually send if not dry run
        if (!dryRun) {
          try {
            const apiUrl = process.env.NODE_ENV === 'development'
              ? 'http://localhost:3000/api/reminder'
              : `${request.nextUrl.origin}/api/reminder`;

            const response = await fetch(apiUrl, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                invoice_id: invoice.id,
                type: step.type,
                level: step.level,
              }),
            });

            const data = await response.json();
            action.result = data;
          } catch (err: any) {
            action.error = err.message;
          }
        }

        break; // Only one action per invoice
      }

      invoiceAnalysis.push(invInfo);
    }

    return NextResponse.json({
      success: true,
      dry_run: dryRun,
      client: clientInfo,
      today: today.toISOString(),
      fourteen_days_ago: fourteenDaysAgo.toISOString(),
      invoices_total: invoices.length,
      invoices_analysis: invoiceAnalysis,
      planned_actions: plannedActions,
      message: plannedActions.length > 0
        ? `${plannedActions.length} action(s) ${dryRun ? 'would be' : 'were'} taken`
        : 'No actions needed',
    });

  } catch (error: any) {
    console.error('[TestSequence] Error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
