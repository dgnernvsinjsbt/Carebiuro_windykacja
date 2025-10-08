/**
 * Find Missing Invoices
 *
 * Szuka płatności bez odpowiadających faktur
 * Sprawdza też faktury poza okresem 15-30.09, które mogły być wystawione z błędnym sell_date
 */

const fs = require('fs');
const path = require('path');

const INVOICES_FILE = path.join(__dirname, '../invoices-filtered.json');
const PAYMENTS_FILE = path.join(__dirname, '../payments.json');

console.log('🔎 SZUKANIE BRAKUJĄCYCH FAKTUR\n');

// Wczytaj dane
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

// === KLUCZOWE KWOTY BEZ FAKTUR ===

console.log('🔴 KLUCZOWE PŁATNOŚCI BEZ FAKTUR:\n');

// Największe niedopasowania z głębokiej analizy
const suspiciousAmounts = [
  { amount: 4740, date: '2025-09-26', description: 'NAJWIĘKSZA BRAKUJĄCA FAKTURA' },
  { amount: 440, date: '2025-09-19', description: '5x powtórzona kwota' },
  { amount: 340, date: '2025-09-15' },
  { amount: 280, date: '2025-09-25' },
  { amount: 260, date: '2025-09-24' },
  { amount: 236.04, date: '2025-09-26' },
];

suspiciousAmounts.forEach(({ amount, date, description }) => {
  // Sprawdź czy jest faktura z taką kwotą w tym dniu
  const invoicesThisDay = allInvoices.filter(inv => inv.sell_date === date);
  const matchingInvoice = invoicesThisDay.find(inv =>
    Math.abs(parseFloat(inv.paid || 0) - amount) < 1
  );

  // Sprawdź też płatności
  const matchingPayment = paymentsFiltered.find(p =>
    p.dateNormalized === date && Math.abs(p.amount - amount) < 1
  );

  console.log(`💰 ${amount} EUR (${date})`);
  if (description) console.log(`   ${description}`);
  console.log(`   Faktura: ${matchingInvoice ? '✓ ZNALEZIONO' : '❌ BRAK'}`);

  if (matchingPayment) {
    console.log(`   Płatność: ✓`);
    console.log(`   Klient: ${matchingPayment.name.substring(0, 50)}`);
    console.log(`   Opis: ${matchingPayment.description.substring(0, 60)}`);
  }
  console.log('');
});

// === SZUKAJ FAKTUR Z BŁĘDNYM SELL_DATE ===

console.log('\n🔍 FAKTURY Z POTENCJALNIE BŁĘDNYM SELL_DATE:\n');

// Szukaj faktur z issue_date w okresie 15-30.09, ale sell_date poza tym okresem
const invoicesWrongSellDate = allInvoices.filter(inv => {
  const issueDate = inv.issue_date;
  const sellDate = inv.sell_date;

  if (!issueDate || !sellDate) return false;

  const issueInPeriod = issueDate >= START_DATE && issueDate <= END_DATE;
  const sellNotInPeriod = sellDate < START_DATE || sellDate > END_DATE;

  return issueInPeriod && sellNotInPeriod;
});

console.log(`Znaleziono ${invoicesWrongSellDate.length} faktur z issue_date w okresie, ale sell_date poza okresem:\n`);

invoicesWrongSellDate.slice(0, 20).forEach(inv => {
  console.log(`ID: ${inv.id} | Kwota: ${inv.paid} EUR | issue_date: ${inv.issue_date} | sell_date: ${inv.sell_date}`);
});

// Suma tych faktur
const sumWrongSellDate = invoicesWrongSellDate.reduce((sum, inv) => sum + parseFloat(inv.paid || 0), 0);
console.log(`\n💡 Suma faktur z potencjalnie błędnym sell_date: ${sumWrongSellDate.toFixed(2)} EUR\n`);

// === FAKTURY WYSTAWIONE PO 30.09 Z SELL_DATE W OKRESIE ===

console.log('\n📅 FAKTURY WYSTAWIONE PÓŹ NO (issue_date po 30.09), ale sell_date w okresie:\n');

const invoicesLateIssue = allInvoices.filter(inv => {
  const issueDate = inv.issue_date;
  const sellDate = inv.sell_date;

  if (!issueDate || !sellDate) return false;

  const issueAfter = issueDate > END_DATE;
  const sellInPeriod = sellDate >= START_DATE && sellDate <= END_DATE;

  return issueAfter && sellInPeriod;
});

console.log(`Znaleziono ${invoicesLateIssue.length} faktur wystawionych po okresie:\n`);

invoicesLateIssue.slice(0, 20).forEach(inv => {
  console.log(`ID: ${inv.id} | Kwota: ${inv.paid} EUR | issue_date: ${inv.issue_date} | sell_date: ${inv.sell_date}`);
});

const sumLateIssue = invoicesLateIssue.reduce((sum, inv) => sum + parseFloat(inv.paid || 0), 0);
console.log(`\n💡 Suma faktur wystawionych późno: ${sumLateIssue.toFixed(2)} EUR\n`);

// === PODSUMOWANIE ===

console.log('\n📊 PODSUMOWANIE MOŻLIWYCH PRZYCZYN:\n');
console.log(`1. Faktury z błędnym sell_date (powinny być w okresie): ${sumWrongSellDate.toFixed(2)} EUR`);
console.log(`2. Faktury wystawione późno (issue_date po 30.09): ${sumLateIssue.toFixed(2)} EUR`);
console.log(`3. Całkowicie brakujące faktury: ~${(7415 - sumWrongSellDate - sumLateIssue).toFixed(2)} EUR`);

console.log('\n✅ Analiza zakończona!');
