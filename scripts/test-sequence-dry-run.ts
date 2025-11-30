/**
 * Dry-run test for sequence logic on single client
 * Usage: npx tsx scripts/test-sequence-dry-run.ts
 */

import { createClient } from '@supabase/supabase-js';
import { config } from 'dotenv';
import { parseFiscalSync } from '../lib/fiscal-sync-parser';
import { parseClientFlags } from '../lib/client-flags-v2';
import { fakturowniaApi } from '../lib/fakturownia';
import type { FiscalSyncData } from '../types';

config();

const DAYS_BETWEEN_STEPS = 14;
const CLIENT_ID = 192213656; // Agnieszka Rozmus

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

function getE1Date(invoice: any, fiscalSync: FiscalSyncData | null): Date | null {
  if (fiscalSync?.EMAIL_1 && fiscalSync?.EMAIL_1_DATE) {
    return new Date(fiscalSync.EMAIL_1_DATE);
  }
  if (invoice.email_status === 'sent' && invoice.sent_time) {
    return new Date(invoice.sent_time);
  }
  return null;
}

async function main() {
  console.log('='.repeat(60));
  console.log('DRY-RUN: Test sekwencji windykacyjnej');
  console.log('='.repeat(60));

  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );

  // 1. Get client
  const { data: client, error: clientError } = await supabase
    .from('clients')
    .select('id, name, note')
    .eq('id', CLIENT_ID)
    .single();

  if (clientError || !client) {
    console.error('Klient nie znaleziony');
    process.exit(1);
  }

  const flags = parseClientFlags(client.note);

  console.log('\n📋 KLIENT:');
  console.log(`   ID: ${client.id}`);
  console.log(`   Nazwa: ${client.name}`);
  console.log(`   Windykacja: ${flags.windykacja ? '✅ TAK' : '❌ NIE'}`);

  if (!flags.windykacja) {
    console.log('\n⚠️  Windykacja wyłączona - brak akcji');
    process.exit(0);
  }

  // 2. Daty
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const fourteenDaysAgo = new Date(today);
  fourteenDaysAgo.setDate(fourteenDaysAgo.getDate() - DAYS_BETWEEN_STEPS);

  console.log('\n📅 DATY:');
  console.log(`   Dzisiaj: ${today.toISOString().split('T')[0]}`);
  console.log(`   14 dni temu: ${fourteenDaysAgo.toISOString().split('T')[0]}`);

  // 3. Fetch invoices from Fakturownia
  console.log('\n🔄 Pobieram faktury z Fakturowni...');
  const invoices = await fakturowniaApi.getInvoicesByClientId(CLIENT_ID, 100);
  console.log(`   Znaleziono: ${invoices.length} faktur`);

  const plannedActions: any[] = [];

  for (const invoice of invoices) {
    const fiscalSync = parseFiscalSync(invoice.internal_note);

    console.log('\n' + '-'.repeat(60));
    console.log(`📄 FAKTURA: ${invoice.number}`);
    console.log(`   ID: ${invoice.id}`);
    console.log(`   Status: ${invoice.status}`);
    console.log(`   Kwota: ${invoice.price_gross} PLN`);
    console.log(`   Zapłacone: ${invoice.paid || 0} PLN`);
    console.log(`   Termin: ${invoice.payment_to}`);

    // Check: paid?
    if (invoice.status === 'paid') {
      console.log('   ⏭️  SKIP: Faktura opłacona');
      continue;
    }

    // Check: balance?
    const balance = parseFloat(invoice.price_gross || '0') - parseFloat(invoice.paid || '0');
    if (balance <= 0) {
      console.log('   ⏭️  SKIP: Brak salda');
      continue;
    }

    // Check: overdue?
    if (!invoice.payment_to) {
      console.log('   ⏭️  SKIP: Brak terminu płatności');
      continue;
    }

    const paymentDate = new Date(invoice.payment_to);
    paymentDate.setHours(0, 0, 0, 0);

    if (paymentDate >= today) {
      console.log('   ⏭️  SKIP: Nieprzeterminowana');
      continue;
    }

    const daysOverdue = Math.floor((today.getTime() - paymentDate.getTime()) / (1000 * 60 * 60 * 24));
    console.log(`   ⏰ Przeterminowana od: ${daysOverdue} dni`);

    // Check: STOP?
    if (fiscalSync?.STOP === true) {
      console.log('   ⏭️  SKIP: STOP włączony');
      continue;
    }

    console.log('   ✅ Faktura kwalifikuje się do windykacji');

    // Fiscal sync status
    console.log('\n   📊 STATUS [FISCAL_SYNC]:');
    if (fiscalSync) {
      console.log(`      EMAIL_1: ${fiscalSync.EMAIL_1 ? '✅' : '❌'} ${fiscalSync.EMAIL_1_DATE || ''}`);
      console.log(`      EMAIL_2: ${fiscalSync.EMAIL_2 ? '✅' : '❌'} ${fiscalSync.EMAIL_2_DATE || ''}`);
      console.log(`      EMAIL_3: ${fiscalSync.EMAIL_3 ? '✅' : '❌'} ${fiscalSync.EMAIL_3_DATE || ''}`);
      console.log(`      SMS_1: ${fiscalSync.SMS_1 ? '✅' : '❌'} ${fiscalSync.SMS_1_DATE || ''}`);
      console.log(`      SMS_2: ${fiscalSync.SMS_2 ? '✅' : '❌'} ${fiscalSync.SMS_2_DATE || ''}`);
    } else {
      console.log('      (brak bloku [FISCAL_SYNC])');
    }

    // Fakturownia email status
    console.log('\n   📧 STATUS FAKTUROWNI:');
    console.log(`      email_status: ${invoice.email_status || 'brak'}`);
    console.log(`      sent_time: ${invoice.sent_time || 'brak'}`);

    // Get E1 date
    const e1Date = getE1Date(invoice, fiscalSync);

    if (!e1Date) {
      console.log('\n   ⚠️  E1 nie wysłany - czeka na auto-send-overdue');
      continue;
    }

    const daysSinceE1 = Math.floor((today.getTime() - e1Date.getTime()) / (1000 * 60 * 60 * 24));
    const e1Source = fiscalSync?.EMAIL_1 ? 'nasz system' : 'Fakturownia';

    console.log('\n   📩 ANALIZA E1:');
    console.log(`      Źródło: ${e1Source}`);
    console.log(`      Data: ${e1Date.toISOString().split('T')[0]}`);
    console.log(`      Dni od E1: ${daysSinceE1}`);

    // Check sequence
    console.log('\n   🔄 SPRAWDZAM SEKWENCJĘ:');

    for (const step of SEQUENCE) {
      // Already done?
      if (fiscalSync?.[step.check] === true) {
        console.log(`      ${step.type.toUpperCase()}_${step.level}: ✅ już wysłane`);
        continue;
      }

      // Previous step done?
      if (step.prevCheck && fiscalSync?.[step.prevCheck] !== true) {
        if (step.check === 'EMAIL_2') {
          if (invoice.email_status !== 'sent') {
            console.log(`      ${step.type.toUpperCase()}_${step.level}: ⏭️ poprzedni krok nie wykonany`);
            continue;
          }
        } else {
          console.log(`      ${step.type.toUpperCase()}_${step.level}: ⏭️ poprzedni krok nie wykonany`);
          continue;
        }
      }

      // Get previous date
      let prevDate: Date | null = null;
      if (step.dateField === 'EMAIL_1_DATE') {
        prevDate = e1Date;
      } else if (fiscalSync) {
        const dateValue = fiscalSync[step.dateField];
        if (dateValue && dateValue !== 'NULL' && typeof dateValue === 'string') {
          prevDate = new Date(dateValue);
        }
      }

      if (!prevDate) {
        console.log(`      ${step.type.toUpperCase()}_${step.level}: ⏭️ brak daty poprzedniego kroku`);
        continue;
      }

      const daysSincePrev = Math.floor((today.getTime() - prevDate.getTime()) / (1000 * 60 * 60 * 24));

      if (prevDate > fourteenDaysAgo) {
        console.log(`      ${step.type.toUpperCase()}_${step.level}: ⏳ za ${DAYS_BETWEEN_STEPS - daysSincePrev} dni (${daysSincePrev}/${DAYS_BETWEEN_STEPS} dni)`);
        break;
      }

      // Ready to send!
      console.log(`      ${step.type.toUpperCase()}_${step.level}: 🚀 GOTOWY DO WYSYŁKI!`);
      console.log(`         Powód: poprzedni krok był ${daysSincePrev} dni temu (> ${DAYS_BETWEEN_STEPS})`);

      plannedActions.push({
        invoice_id: invoice.id,
        invoice_number: invoice.number,
        action: `${step.type.toUpperCase()}_${step.level}`,
        days_since_prev: daysSincePrev,
      });

      break; // Only one action per invoice
    }
  }

  // Summary
  console.log('\n' + '='.repeat(60));
  console.log('📊 PODSUMOWANIE');
  console.log('='.repeat(60));

  if (plannedActions.length === 0) {
    console.log('\n✅ Brak akcji do wykonania');
  } else {
    console.log(`\n🚀 PLANOWANE AKCJE (${plannedActions.length}):`);
    for (const action of plannedActions) {
      console.log(`\n   📧 ${action.action}`);
      console.log(`      Faktura: ${action.invoice_number} (ID: ${action.invoice_id})`);
      console.log(`      Powód: ${action.days_since_prev} dni od poprzedniej akcji`);
    }
  }

  console.log('\n' + '='.repeat(60));
  console.log('DRY-RUN ZAKOŃCZONY - żadne wiadomości nie zostały wysłane');
  console.log('='.repeat(60));
}

main().catch(console.error);
