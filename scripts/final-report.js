/**
 * Final Report - Wszystkie płatności bez faktur
 */

const fs = require('fs');
const path = require('path');

const INVOICES_FILE = path.join(__dirname, '../invoices-filtered.json');
const PAYMENTS_FILE = path.join(__dirname, '../payments.json');
const REPORT_FILE = path.join(__dirname, '../missing-invoices-report.json');

const allInvoices = JSON.parse(fs.readFileSync(INVOICES_FILE, 'utf-8'));

const paymentsRaw = fs.readFileSync(PAYMENTS_FILE, 'utf-8')
  .split('\n')
  .filter(line => line.trim())
  .map(line => {
    const parts = line.split('\t');
    if (parts.length < 2) return null;

    const date = parts[0]?.trim();
    const amount = parseFloat(parts[1]?.replace(',', '.')) || 0;
    const name = parts[2]?.trim() || '';
    const description = parts[3]?.trim() || '';

    return { date, amount, name, description };
  })
  .filter(p => p && p.amount > 0);

function parsePaymentDate(dateStr) {
  if (!dateStr) return null;
  const parts = dateStr.split('/');
  if (parts.length !== 3) return null;

  const day = parts[0].padStart(2, '0');
  const month = parts[1].padStart(2, '0');
  const year = parts[2];

  return `${year}-${month}-${day}`;
}

const payments = paymentsRaw.map(p => ({
  ...p,
  dateNormalized: parsePaymentDate(p.date),
})).filter(p => p.dateNormalized);

const START_DATE = '2025-09-15';
const END_DATE = '2025-09-30';

const paymentsFiltered = payments.filter(p =>
  p.dateNormalized >= START_DATE && p.dateNormalized <= END_DATE
);

console.log('📝 RAPORT KOŃCOWY - PŁATNOŚCI BEZ FAKTUR\n');

// Dla każdej płatności szukaj dokładnej faktury
const paymentsWithoutInvoice = [];

paymentsFiltered.forEach(payment => {
  // Szukaj faktury z tym samym sell_date i podobną kwotą (±2 EUR)
  const matchingInvoice = allInvoices.find(inv => {
    const sameDate = inv.sell_date === payment.dateNormalized;
    const similarAmount = Math.abs(parseFloat(inv.paid || 0) - payment.amount) <= 2;

    return sameDate && similarAmount;
  });

  if (!matchingInvoice) {
    paymentsWithoutInvoice.push({
      date: payment.dateNormalized,
      amount: payment.amount,
      client: payment.name,
      description: payment.description,
    });
  }
});

console.log(`🔴 Znaleziono ${paymentsWithoutInvoice.length} płatności bez odpowiadających faktur:\n`);

// Sortuj po dacie i kwocie
paymentsWithoutInvoice.sort((a, b) => {
  if (a.date !== b.date) return a.date.localeCompare(b.date);
  return b.amount - a.amount;
});

// Grupuj po dniach
const byDay = {};
paymentsWithoutInvoice.forEach(p => {
  if (!byDay[p.date]) byDay[p.date] = [];
  byDay[p.date].push(p);
});

Object.keys(byDay).sort().forEach(date => {
  const dayPayments = byDay[date];
  const dayTotal = dayPayments.reduce((sum, p) => sum + p.amount, 0);

  console.log(`\n📅 ${date} (${dayPayments.length} płatności, suma: ${dayTotal.toFixed(2)} EUR):`);

  dayPayments.forEach(p => {
    console.log(`   ${p.amount.toFixed(2).padStart(10)} EUR | ${p.client.substring(0, 45)}`);
    if (p.description) {
      console.log(`   ${''.padStart(17)}${p.description.substring(0, 60)}`);
    }
  });
});

const totalMissing = paymentsWithoutInvoice.reduce((sum, p) => sum + p.amount, 0);

console.log(`\n\n💰 ŁĄCZNA SUMA PŁATNOŚCI BEZ FAKTUR: ${totalMissing.toFixed(2)} EUR\n`);

// Top 20 największych
console.log('\n🔴 TOP 20 NAJWIĘKSZYCH PŁATNOŚCI BEZ FAKTUR:\n');

const top20 = [...paymentsWithoutInvoice]
  .sort((a, b) => b.amount - a.amount)
  .slice(0, 20);

top20.forEach((p, idx) => {
  console.log(`${(idx + 1).toString().padStart(2)}. ${p.amount.toFixed(2).padStart(10)} EUR | ${p.date} | ${p.client.substring(0, 40)}`);
});

// Zapisz raport
fs.writeFileSync(REPORT_FILE, JSON.stringify({
  summary: {
    period: { start: START_DATE, end: END_DATE },
    totalPayments: paymentsFiltered.length,
    paymentsWithoutInvoice: paymentsWithoutInvoice.length,
    totalMissing: parseFloat(totalMissing.toFixed(2)),
  },
  missingInvoices: paymentsWithoutInvoice,
  top20: top20,
}, null, 2), 'utf-8');

console.log(`\n\n💾 Raport zapisany do: ${REPORT_FILE}`);
console.log('\n✅ Analiza zakończona!');
