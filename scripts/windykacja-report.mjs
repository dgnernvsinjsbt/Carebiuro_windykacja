import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
dotenv.config();

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

console.log('📊 RAPORT WINDYKACJA\n');
console.log('='.repeat(80));

// 1. Pobierz wszystkich klientów z windykacja=true
const { data: windykacjaClients, error: clientsError } = await supabase
  .from('clients')
  .select('*')
  .ilike('note', '%[WINDYKACJA]true%')
  .order('name');

if (clientsError) {
  console.error('Błąd:', clientsError);
  process.exit(1);
}

console.log(`\n✅ Znaleziono ${windykacjaClients.length} klientów z flagą windykacja=true\n`);

// 2. Dla każdego klienta pobierz faktury
let totalInvoices = 0;
let unpaidInvoices = 0;
let unpaidAmount = 0;
let notSentCount = 0;

const report = [];

for (const client of windykacjaClients) {
  const { data: invoices, error: invError } = await supabase
    .from('invoices')
    .select('*')
    .eq('client_id', client.id)
    .order('issue_date', { ascending: false });

  if (invError) {
    console.error(`Błąd dla klienta ${client.id}:`, invError);
    continue;
  }

  // Filtruj faktury: tylko te które są nieopłacone i nie są korektami
  const relevantInvoices = invoices.filter(inv => {
    const isUnpaid = inv.status !== 'paid';
    const isNotCorrection = !inv.number || !inv.number.startsWith('FK');
    const hasBalance = (inv.total - (inv.paid || 0)) > 0;
    return isUnpaid && isNotCorrection && hasBalance;
  });

  // Sprawdź które nie zostały wysłane
  const notSent = relevantInvoices.filter(inv => {
    return !inv.sent_time && !inv.email_status;
  });

  if (relevantInvoices.length > 0) {
    const clientUnpaid = relevantInvoices.reduce((sum, inv) =>
      sum + (inv.total - (inv.paid || 0)), 0
    );

    totalInvoices += relevantInvoices.length;
    unpaidInvoices += relevantInvoices.length;
    unpaidAmount += clientUnpaid;
    notSentCount += notSent.length;

    report.push({
      client,
      invoices: relevantInvoices,
      notSent,
      unpaidAmount: clientUnpaid
    });
  }
}

console.log('\n📈 STATYSTYKI:');
console.log('='.repeat(80));
console.log(`Klienci windykacja:           ${windykacjaClients.length}`);
console.log(`Nieopłacone faktury:          ${unpaidInvoices}`);
console.log(`Kwota do odzyskania:          ${unpaidAmount.toFixed(2)} PLN`);
console.log(`Faktury bez wysyłki:          ${notSentCount}`);

console.log('\n\n📋 SZCZEGÓŁY KLIENTÓW:');
console.log('='.repeat(80));

for (const item of report) {
  const c = item.client;
  console.log(`\n👤 ${c.name} (ID: ${c.id})`);
  console.log(`   Email: ${c.email || 'BRAK'}`);
  console.log(`   Telefon: ${c.phone || c.mobile_phone || 'BRAK'}`);
  console.log(`   Kwota do zapłaty: ${item.unpaidAmount.toFixed(2)} PLN`);

  console.log(`\n   📄 Nieopłacone faktury (${item.invoices.length}):`);
  for (const inv of item.invoices) {
    const outstanding = inv.total - (inv.paid || 0);
    const sentStatus = inv.sent_time ? '✅ Wysłana' : '❌ NIE wysłana';
    const overdue = inv.payment_to && new Date(inv.payment_to) < new Date() ? '⚠️ PO TERMINIE' : '';

    console.log(`      ${inv.number} | ${inv.issue_date} | ${outstanding.toFixed(2)} PLN | ${sentStatus} ${overdue}`);
  }

  if (item.notSent.length > 0) {
    console.log(`\n   ⚠️  UWAGA: ${item.notSent.length} faktur NIE zostało wysłanych!`);
  }

  console.log('   ' + '-'.repeat(75));
}

console.log('\n\n🎯 PODSUMOWANIE:');
console.log('='.repeat(80));

const clientsWithNotSent = report.filter(r => r.notSent.length > 0);
if (clientsWithNotSent.length > 0) {
  console.log(`\n❌ ${clientsWithNotSent.length} klientów ma faktury które nie zostały wysłane:`);
  for (const item of clientsWithNotSent) {
    console.log(`   - ${item.client.name}: ${item.notSent.length} faktur bez wysyłki`);
  }
} else {
  console.log('\n✅ Wszystkie faktury zostały wysłane!');
}

console.log('\n');
