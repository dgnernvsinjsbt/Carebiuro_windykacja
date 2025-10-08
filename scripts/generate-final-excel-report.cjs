/**
 * Generate Final Excel Report
 *
 * Podsumowanie analizy płatności vs faktury (15-30.09.2025)
 */

const fs = require('fs');
const path = require('path');
const ExcelJS = require('exceljs');

const SMART_REPORT = path.join(__dirname, '../smart-match-report.json');
const EXCEL_OUTPUT = path.join(__dirname, '../Raport_Platnosci_Faktury_15-30-09-2025.xlsx');

async function generateReport() {
console.log('📊 Generowanie raportu Excel...\n');

const report = JSON.parse(fs.readFileSync(SMART_REPORT, 'utf-8'));

const workbook = new ExcelJS.Workbook();

// === ARKUSZ 1: PODSUMOWANIE ===
const summarySheet = workbook.addWorksheet('Podsumowanie');

summarySheet.columns = [
  { header: 'Metryka', key: 'metric', width: 40 },
  { header: 'Wartość', key: 'value', width: 20 },
];

summarySheet.addRows([
  { metric: 'Okres analizy', value: `${report.summary.period.start} do ${report.summary.period.end}` },
  { metric: '', value: '' },
  { metric: 'Łączna liczba płatności', value: report.summary.totalPayments },
  { metric: '', value: '' },
  { metric: '✅ Dopasowane dokładnie (nazwa + kwota)', value: report.summary.matched.exact },
  { metric: '🔄 Dopasowane grupowo (suma faktur)', value: report.summary.matched.group },
  { metric: '⚠️ Dopasowane tylko po nazwie', value: report.summary.matched.nameOnly },
  { metric: '❌ Niedopasowane', value: report.summary.unmatched },
  { metric: '', value: '' },
  { metric: 'Suma niedopasowanych płatności (EUR)', value: report.summary.unmatchedSum },
  { metric: '', value: '' },
  { metric: '📈 % dopasowania', value: `${(((report.summary.totalPayments - report.summary.unmatched) / report.summary.totalPayments) * 100).toFixed(2)}%` },
]);

// Formatowanie
summarySheet.getCell('A1').font = { bold: true, size: 12 };
summarySheet.getCell('B1').font = { bold: true, size: 12 };

// === ARKUSZ 2: PŁATNOŚCI GRUPOWE ===
const groupSheet = workbook.addWorksheet('Płatności grupowe');

groupSheet.columns = [
  { header: 'Data', key: 'date', width: 12 },
  { header: 'Kwota płatności (EUR)', key: 'paymentAmount', width: 18 },
  { header: 'Klient', key: 'client', width: 45 },
  { header: 'Liczba faktur', key: 'invoiceCount', width: 15 },
  { header: 'Suma faktur (EUR)', key: 'invoicesSum', width: 18 },
  { header: 'Różnica (EUR)', key: 'difference', width: 15 },
  { header: 'IDs faktur', key: 'invoiceIds', width: 40 },
];

report.groupMatches.forEach(match => {
  const p = match.payment;
  const invoicesSum = match.invoices.reduce((s, inv) => s + parseFloat(inv.paid || 0), 0);
  const difference = p.amount - invoicesSum;

  groupSheet.addRow({
    date: p.dateNormalized,
    paymentAmount: p.amount,
    client: p.name,
    invoiceCount: match.invoices.length,
    invoicesSum: parseFloat(invoicesSum.toFixed(2)),
    difference: parseFloat(difference.toFixed(2)),
    invoiceIds: match.invoices.map(inv => inv.id).join(', '),
  });
});

// Formatowanie nagłówków
groupSheet.getRow(1).font = { bold: true };
groupSheet.getRow(1).fill = {
  type: 'pattern',
  pattern: 'solid',
  fgColor: { argb: 'FFE0E0E0' },
};

// === ARKUSZ 3: NIEDOPASOWANE PŁATNOŚCI ===
const unmatchedSheet = workbook.addWorksheet('Niedopasowane płatności');

unmatchedSheet.columns = [
  { header: 'Data', key: 'date', width: 12 },
  { header: 'Kwota (EUR)', key: 'amount', width: 15 },
  { header: 'Klient', key: 'client', width: 50 },
  { header: 'Opis', key: 'description', width: 60 },
];

report.unmatchedPayments.forEach(p => {
  unmatchedSheet.addRow({
    date: p.dateNormalized,
    amount: p.amount,
    client: p.name,
    description: p.description,
  });
});

// Formatowanie nagłówków
unmatchedSheet.getRow(1).font = { bold: true };
unmatchedSheet.getRow(1).fill = {
  type: 'pattern',
  pattern: 'solid',
  fgColor: { argb: 'FFFFC0CB' },
};

// === ARKUSZ 4: WSZYSTKIE DOPASOWANIA (szczegóły) ===
const detailsSheet = workbook.addWorksheet('Wszystkie dopasowania');

detailsSheet.columns = [
  { header: 'Typ', key: 'type', width: 12 },
  { header: 'Data', key: 'date', width: 12 },
  { header: 'Płatność (EUR)', key: 'paymentAmount', width: 15 },
  { header: 'Klient', key: 'client', width: 45 },
  { header: 'Liczba faktur', key: 'invoiceCount', width: 12 },
  { header: 'Pewność', key: 'confidence', width: 12 },
];

report.allMatches.forEach(match => {
  const p = match.payment;
  const typeLabel = {
    exact: '✅ Dokładne',
    group: '🔄 Grupowe',
    name_only: '⚠️ Nazwa',
  }[match.type] || match.type;

  detailsSheet.addRow({
    type: typeLabel,
    date: p.dateNormalized,
    paymentAmount: p.amount,
    client: p.name,
    invoiceCount: match.invoices.length,
    confidence: match.confidence,
  });
});

// Formatowanie nagłówków
detailsSheet.getRow(1).font = { bold: true };
detailsSheet.getRow(1).fill = {
  type: 'pattern',
  pattern: 'solid',
  fgColor: { argb: 'FFD0F0D0' },
};

// === ZAPISZ EXCEL ===
await workbook.xlsx.writeFile(EXCEL_OUTPUT);

console.log('✅ Raport wygenerowany!');
console.log(`📁 Lokalizacja: ${EXCEL_OUTPUT}\n`);

console.log('📊 PODSUMOWANIE RAPORTU:\n');
console.log(`   Okres: ${report.summary.period.start} do ${report.summary.period.end}`);
console.log(`   Płatności: ${report.summary.totalPayments}`);
console.log(`   Dopasowane: ${report.summary.totalPayments - report.summary.unmatched} (${(((report.summary.totalPayments - report.summary.unmatched) / report.summary.totalPayments) * 100).toFixed(2)}%)`);
console.log(`   Niedopasowane: ${report.summary.unmatched} (${report.summary.unmatchedSum} EUR)`);
console.log(`   Płatności grupowe: ${report.summary.matched.group}\n`);

console.log('📋 ARKUSZE W EXCELU:');
console.log('   1. Podsumowanie - ogólne statystyki');
console.log('   2. Płatności grupowe - szczegóły płatności za kilka faktur');
console.log('   3. Niedopasowane płatności - wymagają weryfikacji');
console.log('   4. Wszystkie dopasowania - pełna lista\n');
}

generateReport().catch(err => {
  console.error('Błąd:', err);
  process.exit(1);
});
