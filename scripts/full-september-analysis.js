/**
 * Full September Analysis (01-30.09.2025)
 *
 * Inteligentne dopasowanie płatności do faktur
 */

const fs = require('fs');
const path = require('path');

const INVOICES_FILE = path.join(__dirname, '../invoices-filtered.json');
const PAYMENTS_FILE = path.join(__dirname, '../payments.csv');
const REPORT_FILE = path.join(__dirname, '../full-september-report.json');

console.log('🧠 ANALIZA PEŁNEGO WRZEŚNIA (01-30.09.2025)\n');

// === WCZYTANIE DANYCH ===

const allInvoices = JSON.parse(fs.readFileSync(INVOICES_FILE, 'utf-8'));

const paymentsLines = fs.readFileSync(PAYMENTS_FILE, 'utf-8').split('\n').filter(line => line.trim());

// Pomiń nagłówek (pierwszy wiersz)
const paymentsRaw = paymentsLines.slice(1).map(line => {
  const parts = line.split('\t');
  if (parts.length < 6) return null;

  // Format CSV: Data transakcji | Data księgowania | Typ | Kwota | Waluta | Kontrahent | Numer konta | Cel płatności | Ref No
  const date = parts[0]?.trim(); // Data transakcji
  const amount = parseFloat(parts[3]?.replace(',', '.')) || 0; // Kwota
  const name = parts[5]?.trim() || ''; // Kontrahent
  const description = parts[7]?.trim() || ''; // Cel płatności
  const refNo = parts[8]?.trim() || ''; // Ref No (identyfikator transakcji)

  return { date, amount, name, description, refNo };
}).filter(p => p && p.amount > 0);

function parsePaymentDate(dateStr) {
  if (!dateStr) return null;

  // Format: DD.MM.YYYY
  const parts = dateStr.split('.');
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

const START_DATE = '2025-09-01';
const END_DATE = '2025-09-30';

const paymentsFiltered = payments.filter(p =>
  p.dateNormalized >= START_DATE && p.dateNormalized <= END_DATE
);

const invoicesFiltered = allInvoices.filter(inv =>
  inv.sell_date && inv.sell_date >= START_DATE && inv.sell_date <= END_DATE
);

console.log(`📊 Okres: ${START_DATE} do ${END_DATE}`);
console.log(`   Płatności: ${paymentsFiltered.length}`);
console.log(`   Faktury (sell_date): ${invoicesFiltered.length}\n`);

// === FUNKCJE DOPASOWANIA ===

function normalizeName(name) {
  if (!name) return '';
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '')
    .trim();
}

function namesMatch(paymentName, invoiceName) {
  const p = normalizeName(paymentName);
  const i = normalizeName(invoiceName);

  if (!p || !i) return false;
  if (p === i) return true;
  if (p.includes(i) || i.includes(p)) return true;

  const common = [...p].filter(c => i.includes(c)).length;
  const similarity = common / Math.max(p.length, i.length);

  return similarity >= 0.6;
}

function findInvoiceCombinations(invoices, targetSum, tolerance = 5) {
  const amounts = invoices.map(inv => parseFloat(inv.paid || 0));

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

// === DOPASOWANIE ===

const matchResults = [];
const unmatchedPayments = [];

paymentsFiltered.forEach(payment => {
  const paymentDate = payment.dateNormalized;
  const paymentAmount = payment.amount;
  const paymentName = payment.name;

  const invoicesThisDay = invoicesFiltered.filter(inv => inv.sell_date === paymentDate);
  const invoicesSameName = invoicesThisDay.filter(inv => namesMatch(paymentName, inv.buyer_name));

  // Dokładne dopasowanie
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

  // Płatność grupowa
  if (invoicesSameName.length > 1) {
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

  // Dopasowanie po nazwie
  if (invoicesSameName.length > 0) {
    matchResults.push({
      type: 'name_only',
      payment,
      invoices: invoicesSameName,
      confidence: 'low',
    });
    return;
  }

  // Brak dopasowania
  unmatchedPayments.push(payment);
});

// === WYNIKI ===

console.log('📊 WYNIKI DOPASOWANIA:\n');

const exactMatches = matchResults.filter(m => m.type === 'exact').length;
const groupMatches = matchResults.filter(m => m.type === 'group').length;
const nameOnlyMatches = matchResults.filter(m => m.type === 'name_only').length;

const totalPaymentsSum = paymentsFiltered.reduce((s, p) => s + p.amount, 0);
const totalInvoicesSum = invoicesFiltered.reduce((s, inv) => s + parseFloat(inv.paid || 0), 0);
const unmatchedSum = unmatchedPayments.reduce((s, p) => s + p.amount, 0);

console.log(`✅ Dopasowane dokładnie (nazwa + kwota):     ${exactMatches}`);
console.log(`🔄 Dopasowane grupowo (nazwa + suma):       ${groupMatches}`);
console.log(`⚠️  Dopasowane tylko po nazwie:             ${nameOnlyMatches}`);
console.log(`❌ Niedopasowane:                           ${unmatchedPayments.length}`);
console.log('');

console.log('💰 KWOTY:');
console.log(`   Suma płatności:        ${totalPaymentsSum.toFixed(2)} EUR`);
console.log(`   Suma faktur:           ${totalInvoicesSum.toFixed(2)} EUR`);
console.log(`   Niedopasowane:         ${unmatchedSum.toFixed(2)} EUR`);
console.log(`   Różnica:               ${(totalPaymentsSum - totalInvoicesSum).toFixed(2)} EUR`);
console.log('');

// TOP niedopasowane
if (unmatchedPayments.length > 0) {
  console.log('🔴 TOP 20 NIEDOPASOWANYCH PŁATNOŚCI:\n');

  unmatchedPayments
    .sort((a, b) => b.amount - a.amount)
    .slice(0, 20)
    .forEach((p, idx) => {
      console.log(`${(idx + 1).toString().padStart(2)}. ${p.amount.toFixed(2).padStart(10)} EUR | ${p.dateNormalized} | ${p.name.substring(0, 40)}`);
      if (p.description) {
        console.log(`   ${' '.repeat(17)}${p.description.substring(0, 60)}`);
      }
    });

  console.log(`\n💰 Suma niedopasowanych: ${unmatchedSum.toFixed(2)} EUR\n`);
}

// Płatności grupowe
const groupMatchesDetails = matchResults.filter(m => m.type === 'group');
if (groupMatchesDetails.length > 0) {
  console.log(`\n🔄 PŁATNOŚCI GRUPOWE (${groupMatchesDetails.length}):\n`);

  groupMatchesDetails.slice(0, 10).forEach((match, idx) => {
    const p = match.payment;
    const invoicesSum = match.invoices.reduce((s, inv) => s + parseFloat(inv.paid || 0), 0);

    console.log(`${(idx + 1).toString().padStart(2)}. ${p.amount} EUR → ${match.invoices.length} faktur (suma: ${invoicesSum.toFixed(2)} EUR)`);
    console.log(`   ${p.dateNormalized} | ${p.name.substring(0, 50)}`);
  });

  if (groupMatchesDetails.length > 10) {
    console.log(`   ... i ${groupMatchesDetails.length - 10} więcej`);
  }
}

// === ZAPISZ RAPORT ===

const report = {
  period: { start: START_DATE, end: END_DATE },
  summary: {
    totalPayments: paymentsFiltered.length,
    totalInvoices: invoicesFiltered.length,
    paymentsSum: parseFloat(totalPaymentsSum.toFixed(2)),
    invoicesSum: parseFloat(totalInvoicesSum.toFixed(2)),
    difference: parseFloat((totalPaymentsSum - totalInvoicesSum).toFixed(2)),
    matched: {
      exact: exactMatches,
      group: groupMatches,
      nameOnly: nameOnlyMatches,
      total: matchResults.length,
    },
    unmatched: unmatchedPayments.length,
    unmatchedSum: parseFloat(unmatchedSum.toFixed(2)),
    matchPercentage: parseFloat((((paymentsFiltered.length - unmatchedPayments.length) / paymentsFiltered.length) * 100).toFixed(2)),
  },
  unmatchedPayments: unmatchedPayments.sort((a, b) => b.amount - a.amount),
  groupMatches: groupMatchesDetails,
  allMatches: matchResults,
};

fs.writeFileSync(REPORT_FILE, JSON.stringify(report, null, 2), 'utf-8');

console.log(`\n💾 Raport zapisany do: ${REPORT_FILE}`);
console.log('\n✅ Analiza zakończona!');
