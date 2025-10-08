/**
 * Deep Payment-Invoice Analysis
 *
 * Szczegółowa analiza problematycznych dni
 */

const fs = require('fs');
const path = require('path');

const ANALYSIS_FILE = path.join(__dirname, '../analysis-results.json');
const DEEP_ANALYSIS_OUTPUT = path.join(__dirname, '../deep-analysis-results.json');

const analysis = JSON.parse(fs.readFileSync(ANALYSIS_FILE, 'utf-8'));

console.log('🔬 GŁĘBOKA ANALIZA PROBLEMATYCZNYCH DNI\n');

const deepAnalysis = analysis.anomalyDays.map(day => {
  const { date, paymentsDetails, invoicesDetails, difference } = day;

  // Ekstraktuj kwoty
  const paymentAmounts = paymentsDetails.map(p => p.amount).sort((a, b) => b - a);
  const invoiceAmounts = invoicesDetails.map(inv => parseFloat(inv.paid || 0)).sort((a, b) => b - a);

  // Znajdź potencjalne dopasowania (kwoty zbliżone ±5 EUR)
  const matches = [];
  const unmatchedPayments = [];
  const unmatchedInvoices = [];

  const usedInvoices = new Set();

  paymentAmounts.forEach(payAmount => {
    let matched = false;

    for (let i = 0; i < invoiceAmounts.length; i++) {
      if (usedInvoices.has(i)) continue;

      const invAmount = invoiceAmounts[i];
      const diff = Math.abs(payAmount - invAmount);

      if (diff <= 5) { // Tolerancja 5 EUR
        matches.push({
          payment: payAmount,
          invoice: invAmount,
          diff: parseFloat(diff.toFixed(2)),
        });
        usedInvoices.add(i);
        matched = true;
        break;
      }
    }

    if (!matched) {
      unmatchedPayments.push(payAmount);
    }
  });

  invoiceAmounts.forEach((invAmount, i) => {
    if (!usedInvoices.has(i)) {
      unmatchedInvoices.push(invAmount);
    }
  });

  const unmatchedPaymentsSum = unmatchedPayments.reduce((s, v) => s + v, 0);
  const unmatchedInvoicesSum = unmatchedInvoices.reduce((s, v) => s + v, 0);

  return {
    date,
    difference: parseFloat(difference.toFixed(2)),
    stats: {
      paymentsCount: paymentsDetails.length,
      invoicesCount: invoicesDetails.length,
      matchedPairs: matches.length,
      unmatchedPayments: unmatchedPayments.length,
      unmatchedInvoices: unmatchedInvoices.length,
    },
    unmatchedPaymentsSum: parseFloat(unmatchedPaymentsSum.toFixed(2)),
    unmatchedInvoicesSum: parseFloat(unmatchedInvoicesSum.toFixed(2)),
    potentialMissingInvoices: unmatchedPayments.length > 0,
    unmatchedPayments,
    unmatchedInvoices,
    topUnmatchedPayments: unmatchedPayments.slice(0, 10),
    topUnmatchedInvoices: unmatchedInvoices.slice(0, 10),
  };
});

// Sortuj według różnicy
deepAnalysis.sort((a, b) => Math.abs(b.difference) - Math.abs(a.difference));

console.log('📊 TOP PROBLEMATYCZNE DNI:\n');

deepAnalysis.forEach((day, idx) => {
  console.log(`${idx + 1}. ${day.date} (różnica: ${day.difference} EUR)`);
  console.log(`   Dopasowano par: ${day.stats.matchedPairs}`);
  console.log(`   Niedopasowane płatności: ${day.stats.unmatchedPayments} (suma: ${day.unmatchedPaymentsSum} EUR)`);
  console.log(`   Niedopasowane faktury: ${day.stats.unmatchedInvoices} (suma: ${day.unmatchedInvoicesSum} EUR)`);

  if (day.topUnmatchedPayments.length > 0) {
    console.log(`   🔴 Płatności bez faktur (top 5):`);
    day.topUnmatchedPayments.slice(0, 5).forEach(amount => {
      console.log(`      - ${amount} EUR`);
    });
  }

  if (day.topUnmatchedInvoices.length > 0) {
    console.log(`   🟡 Faktury bez płatności (top 5):`);
    day.topUnmatchedInvoices.slice(0, 5).forEach(amount => {
      console.log(`      - ${amount} EUR`);
    });
  }

  console.log('');
});

// KLUCZOWE WNIOSKI
console.log('🎯 KLUCZOWE WNIOSKI:\n');

const totalUnmatchedPayments = deepAnalysis.reduce((s, d) => s + d.unmatchedPaymentsSum, 0);
const totalUnmatchedInvoices = deepAnalysis.reduce((s, d) => s + d.unmatchedInvoicesSum, 0);

console.log(`💡 Łączna suma niedopasowanych płatności: ${totalUnmatchedPayments.toFixed(2)} EUR`);
console.log(`💡 Łączna suma niedopasowanych faktur: ${totalUnmatchedInvoices.toFixed(2)} EUR`);
console.log(`💡 Różnica netto: ${(totalUnmatchedInvoices - totalUnmatchedPayments).toFixed(2)} EUR\n`);

if (totalUnmatchedInvoices > totalUnmatchedPayments) {
  console.log(`⚠️  BRAKUJE FAKTUR NA KWOTĘ: ~${(totalUnmatchedInvoices - totalUnmatchedPayments).toFixed(2)} EUR\n`);
} else {
  console.log(`⚠️  NADMIAR PŁATNOŚCI (prawdopodobnie za faktury poza okresem): ~${(totalUnmatchedPayments - totalUnmatchedInvoices).toFixed(2)} EUR\n`);
}

// Zapisz wyniki
fs.writeFileSync(DEEP_ANALYSIS_OUTPUT, JSON.stringify(deepAnalysis, null, 2), 'utf-8');

console.log(`💾 Głęboka analiza zapisana do: ${DEEP_ANALYSIS_OUTPUT}`);
