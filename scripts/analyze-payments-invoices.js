/**
 * Payment-Invoice Reconciliation Analysis
 *
 * Cel: Znaleźć niezgodności między płatnościami (15-30.09) a wystawionymi fakturami
 *
 * Strategia:
 * 1. Analiza dzienna - suma płatności vs suma faktur per dzień
 * 2. Identyfikacja dni z anomaliami (różnica > próg)
 * 3. Szczegółowa analiza problematycznych dni
 */

const fs = require('fs');
const path = require('path');

// Ścieżki
const INVOICES_FILE = path.join(__dirname, '../invoices-filtered.json');
const PAYMENTS_FILE = path.join(__dirname, '../payments.json');
const ANALYSIS_OUTPUT = path.join(__dirname, '../analysis-results.json');

console.log('🔍 Analiza płatności vs faktury (15-30.09.2025)\n');

// === 1. WCZYTANIE DANYCH ===

// Faktury
const invoices = JSON.parse(fs.readFileSync(INVOICES_FILE, 'utf-8'));

// Płatności - parsuj CSV-like format
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

console.log(`📄 Wczytano ${invoices.length} faktur`);
console.log(`💰 Wczytano ${paymentsRaw.length} płatności\n`);

// === 2. PARSOWANIE DAT ===

// Konwertuj datę z formatu "15/9/2025" na "2025-09-15"
function parsePaymentDate(dateStr) {
  if (!dateStr) return null;
  const parts = dateStr.split('/');
  if (parts.length !== 3) return null;

  const day = parts[0].padStart(2, '0');
  const month = parts[1].padStart(2, '0');
  const year = parts[2];

  return `${year}-${month}-${day}`;
}

// Normalizuj płatności
const payments = paymentsRaw.map(p => ({
  ...p,
  dateNormalized: parsePaymentDate(p.date),
})).filter(p => p.dateNormalized);

console.log(`📅 Znormalizowano ${payments.length} dat płatności\n`);

// === 3. FILTROWANIE OKRESU 15-30.09.2025 ===

const START_DATE = '2025-09-15';
const END_DATE = '2025-09-30';

const paymentsFiltered = payments.filter(p =>
  p.dateNormalized >= START_DATE && p.dateNormalized <= END_DATE
);

const invoicesFiltered = invoices.filter(inv =>
  inv.sell_date && inv.sell_date >= START_DATE && inv.sell_date <= END_DATE
);

console.log(`📊 Okres analizy: ${START_DATE} do ${END_DATE}`);
console.log(`   - Płatności: ${paymentsFiltered.length}`);
console.log(`   - Faktury (sell_date): ${invoicesFiltered.length}\n`);

// === 4. ANALIZA DZIENNA ===

// Grupuj po dniach
const dailyPayments = {};
const dailyInvoices = {};

paymentsFiltered.forEach(p => {
  if (!dailyPayments[p.dateNormalized]) {
    dailyPayments[p.dateNormalized] = { total: 0, count: 0, items: [] };
  }
  dailyPayments[p.dateNormalized].total += p.amount;
  dailyPayments[p.dateNormalized].count += 1;
  dailyPayments[p.dateNormalized].items.push(p);
});

invoicesFiltered.forEach(inv => {
  const date = inv.sell_date;
  if (!dailyInvoices[date]) {
    dailyInvoices[date] = { total: 0, count: 0, items: [] };
  }
  const amount = parseFloat(inv.paid || 0);
  dailyInvoices[date].total += amount;
  dailyInvoices[date].count += 1;
  dailyInvoices[date].items.push(inv);
});

// Wszystkie unikalne daty
const allDates = new Set([
  ...Object.keys(dailyPayments),
  ...Object.keys(dailyInvoices)
]);

// Analiza per dzień
const dailyAnalysis = Array.from(allDates).sort().map(date => {
  const paymentsTotal = dailyPayments[date]?.total || 0;
  const invoicesTotal = dailyInvoices[date]?.total || 0;
  const difference = paymentsTotal - invoicesTotal;
  const percentDiff = invoicesTotal > 0
    ? ((difference / invoicesTotal) * 100).toFixed(1)
    : (paymentsTotal > 0 ? 100 : 0);

  return {
    date,
    payments: {
      total: parseFloat(paymentsTotal.toFixed(2)),
      count: dailyPayments[date]?.count || 0,
    },
    invoices: {
      total: parseFloat(invoicesTotal.toFixed(2)),
      count: dailyInvoices[date]?.count || 0,
    },
    difference: parseFloat(difference.toFixed(2)),
    percentDiff: parseFloat(percentDiff),
    isAnomaly: Math.abs(difference) > 50, // Anomalia jeśli różnica > 50 EUR
  };
});

// === 5. WYNIKI ===

console.log('📊 ANALIZA DZIENNA:\n');
console.log('Data       | Płatności (€) | Faktury (€) | Różnica (€) | % diff | Status');
console.log('-----------|---------------|-------------|-------------|--------|--------');

dailyAnalysis.forEach(day => {
  const statusIcon = day.isAnomaly ? '⚠️ ' : '✓';
  const diff = day.difference >= 0 ? `+${day.difference}` : `${day.difference}`;
  console.log(
    `${day.date} | ${day.payments.total.toString().padEnd(13)} | ${day.invoices.total.toString().padEnd(11)} | ${diff.padEnd(11)} | ${day.percentDiff.toString().padEnd(6)}% | ${statusIcon}`
  );
});

// Podsumowanie
const totalPayments = paymentsFiltered.reduce((sum, p) => sum + p.amount, 0);
const totalInvoices = invoicesFiltered.reduce((sum, inv) => sum + parseFloat(inv.paid || 0), 0);
const totalDifference = totalPayments - totalInvoices;

console.log('\n📈 PODSUMOWANIE:');
console.log(`   Suma płatności:  ${totalPayments.toFixed(2)} EUR`);
console.log(`   Suma faktur:     ${totalInvoices.toFixed(2)} EUR`);
console.log(`   Różnica:         ${totalDifference.toFixed(2)} EUR`);
console.log(`   % różnicy:       ${((totalDifference / totalPayments) * 100).toFixed(2)}%\n`);

// Dni z anomaliami
const anomalyDays = dailyAnalysis.filter(d => d.isAnomaly);

if (anomalyDays.length > 0) {
  console.log(`⚠️  WYKRYTO ${anomalyDays.length} DNI Z ANOMALIAMI (różnica > 50 EUR):\n`);

  anomalyDays.forEach(day => {
    console.log(`📅 ${day.date}:`);
    console.log(`   Płatności: ${day.payments.total} EUR (${day.payments.count} wpłat)`);
    console.log(`   Faktury:   ${day.invoices.total} EUR (${day.invoices.count} faktur)`);
    console.log(`   Różnica:   ${day.difference} EUR\n`);

    // Pokaż szczegóły płatności dla tego dnia
    if (dailyPayments[day.date]) {
      console.log('   💰 Płatności:');
      dailyPayments[day.date].items.slice(0, 5).forEach(p => {
        console.log(`      - ${p.amount} EUR | ${p.name.substring(0, 40)}`);
      });
      if (dailyPayments[day.date].items.length > 5) {
        console.log(`      ... i ${dailyPayments[day.date].items.length - 5} więcej`);
      }
      console.log('');
    }
  });
}

// === 6. ZAPISZ WYNIKI ===

const results = {
  period: { start: START_DATE, end: END_DATE },
  summary: {
    totalPayments: parseFloat(totalPayments.toFixed(2)),
    totalInvoices: parseFloat(totalInvoices.toFixed(2)),
    difference: parseFloat(totalDifference.toFixed(2)),
    percentDiff: parseFloat(((totalDifference / totalPayments) * 100).toFixed(2)),
  },
  dailyAnalysis,
  anomalyDays: anomalyDays.map(day => ({
    ...day,
    paymentsDetails: dailyPayments[day.date]?.items || [],
    invoicesDetails: dailyInvoices[day.date]?.items || [],
  })),
};

fs.writeFileSync(ANALYSIS_OUTPUT, JSON.stringify(results, null, 2), 'utf-8');

console.log(`\n💾 Szczegółowa analiza zapisana do: ${ANALYSIS_OUTPUT}`);
console.log('\n✅ Analiza zakończona!');
