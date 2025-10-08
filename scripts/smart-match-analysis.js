/**
 * Smart Payment-Invoice Matching
 *
 * Dopasowuje płatności do faktur używając:
 * 1. buyer_name (kluczowe!)
 * 2. Data (sell_date vs data płatności)
 * 3. Kwota (z tolerancją)
 *
 * Rozpoznaje płatności grupowe (np. 200 EUR = 3x 65 EUR faktury)
 */

const fs = require('fs');
const path = require('path');

const INVOICES_FILE = path.join(__dirname, '../invoices-filtered.json');
const PAYMENTS_FILE = path.join(__dirname, '../payments.json');
const SMART_REPORT_FILE = path.join(__dirname, '../smart-match-report.json');

console.log('🧠 INTELIGENTNE DOPASOWANIE PŁATNOŚCI DO FAKTUR\n');

// === 1. WCZYTANIE DANYCH ===

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

console.log(`📊 Okres: ${START_DATE} do ${END_DATE}`);
console.log(`   Płatności: ${paymentsFiltered.length}`);
console.log(`   Faktury: ${allInvoices.length}\n`);

// === 2. FUNKCJE POMOCNICZE ===

// Normalizuj nazwę klienta (usuń znaki specjalne, spacje, lowercase)
function normalizeName(name) {
  if (!name) return '';
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '')
    .trim();
}

// Sprawdź czy nazwy są podobne
function namesMatch(paymentName, invoiceName, threshold = 0.6) {
  const p = normalizeName(paymentName);
  const i = normalizeName(invoiceName);

  if (!p || !i) return false;

  // Dokładne dopasowanie
  if (p === i) return true;

  // Sprawdź czy jedno zawiera drugie
  if (p.includes(i) || i.includes(p)) return true;

  // Sprawdź podobieństwo (co najmniej 60% wspólnych znaków)
  const common = [...p].filter(c => i.includes(c)).length;
  const similarity = common / Math.max(p.length, i.length);

  return similarity >= threshold;
}

// === 3. DOPASOWANIE PŁATNOŚCI DO FAKTUR ===

const matchResults = [];
const unmatchedPayments = [];

paymentsFiltered.forEach(payment => {
  const paymentDate = payment.dateNormalized;
  const paymentAmount = payment.amount;
  const paymentName = payment.name;

  // Szukaj faktur z tego samego dnia
  const invoicesThisDay = allInvoices.filter(inv => inv.sell_date === paymentDate);

  // Szukaj faktur z podobną nazwą klienta
  const invoicesSameName = invoicesThisDay.filter(inv =>
    namesMatch(paymentName, inv.buyer_name)
  );

  // === STRATEGIA 1: Dokładne dopasowanie (nazwa + kwota) ===
  const exactMatch = invoicesSameName.find(inv =>
    Math.abs(parseFloat(inv.paid || 0) - paymentAmount) <= 2
  );

  if (exactMatch) {
    matchResults.push({
      type: 'exact',
      payment,
      invoices: [exactMatch],
      confidence: 'high',
    });
    return;
  }

  // === STRATEGIA 2: Płatność grupowa (nazwa + suma faktur) ===
  if (invoicesSameName.length > 1) {
    // Spróbuj znaleźć kombinację faktur, której suma pasuje do płatności
    const combinations = findInvoiceCombinations(invoicesSameName, paymentAmount, 5);

    if (combinations.length > 0) {
      matchResults.push({
        type: 'group',
        payment,
        invoices: combinations,
        confidence: 'medium',
      });
      return;
    }
  }

  // === STRATEGIA 3: Dopasowanie po nazwie (bez kwoty) ===
  if (invoicesSameName.length > 0) {
    matchResults.push({
      type: 'name_only',
      payment,
      invoices: invoicesSameName,
      confidence: 'low',
    });
    return;
  }

  // === BRAK DOPASOWANIA ===
  unmatchedPayments.push(payment);
});

// Funkcja do znajdowania kombinacji faktur
function findInvoiceCombinations(invoices, targetSum, tolerance = 5) {
  const amounts = invoices.map(inv => parseFloat(inv.paid || 0));
  const result = [];

  // Sprawdź wszystkie kombinacje (brute force dla małych zbiorów)
  for (let i = 0; i < invoices.length; i++) {
    let sum = amounts[i];
    const combo = [invoices[i]];

    if (Math.abs(sum - targetSum) <= tolerance) {
      return combo;
    }

    for (let j = i + 1; j < invoices.length; j++) {
      sum += amounts[j];
      combo.push(invoices[j]);

      if (Math.abs(sum - targetSum) <= tolerance) {
        return combo;
      }

      if (sum > targetSum + tolerance) break;
    }
  }

  return [];
}

// === 4. WYNIKI ===

console.log('📊 WYNIKI DOPASOWANIA:\n');

const exactMatches = matchResults.filter(m => m.type === 'exact').length;
const groupMatches = matchResults.filter(m => m.type === 'group').length;
const nameOnlyMatches = matchResults.filter(m => m.type === 'name_only').length;

console.log(`✅ Dopasowane dokładnie (nazwa + kwota):     ${exactMatches}`);
console.log(`🔄 Dopasowane grupowo (nazwa + suma):       ${groupMatches}`);
console.log(`⚠️  Dopasowane tylko po nazwie:             ${nameOnlyMatches}`);
console.log(`❌ Niedopasowane:                           ${unmatchedPayments.length}`);
console.log('');

// Pokaż płatności bez dopasowania
if (unmatchedPayments.length > 0) {
  console.log('🔴 PŁATNOŚCI BEZ DOPASOWANIA:\n');

  unmatchedPayments
    .sort((a, b) => b.amount - a.amount)
    .slice(0, 20)
    .forEach((p, idx) => {
      console.log(`${(idx + 1).toString().padStart(2)}. ${p.amount.toFixed(2).padStart(10)} EUR | ${p.dateNormalized} | ${p.name.substring(0, 40)}`);
    });

  const totalUnmatched = unmatchedPayments.reduce((sum, p) => sum + p.amount, 0);
  console.log(`\n💰 Suma niedopasowanych: ${totalUnmatched.toFixed(2)} EUR\n`);
}

// Pokaż dopasowania grupowe
const groupMatchesDetails = matchResults.filter(m => m.type === 'group');
if (groupMatchesDetails.length > 0) {
  console.log('\n🔄 PŁATNOŚCI GRUPOWE (kilka faktur na jedną płatność):\n');

  groupMatchesDetails.slice(0, 10).forEach((match, idx) => {
    const p = match.payment;
    const invoicesCount = match.invoices.length;
    const invoicesSum = match.invoices.reduce((s, inv) => s + parseFloat(inv.paid || 0), 0);

    console.log(`${idx + 1}. ${p.amount} EUR → ${invoicesCount} faktur (suma: ${invoicesSum.toFixed(2)} EUR)`);
    console.log(`   ${p.dateNormalized} | ${p.name.substring(0, 50)}`);
    match.invoices.forEach(inv => {
      console.log(`      - ${inv.paid} EUR (ID: ${inv.id}) - ${inv.buyer_name}`);
    });
    console.log('');
  });
}

// === 5. ZAPISZ RAPORT ===

const report = {
  summary: {
    period: { start: START_DATE, end: END_DATE },
    totalPayments: paymentsFiltered.length,
    matched: {
      exact: exactMatches,
      group: groupMatches,
      nameOnly: nameOnlyMatches,
    },
    unmatched: unmatchedPayments.length,
    unmatchedSum: parseFloat(unmatchedPayments.reduce((sum, p) => sum + p.amount, 0).toFixed(2)),
  },
  unmatchedPayments: unmatchedPayments.sort((a, b) => b.amount - a.amount),
  groupMatches: groupMatchesDetails,
  allMatches: matchResults,
};

fs.writeFileSync(SMART_REPORT_FILE, JSON.stringify(report, null, 2), 'utf-8');

console.log(`\n💾 Raport zapisany do: ${SMART_REPORT_FILE}`);
console.log('\n✅ Analiza zakończona!');
