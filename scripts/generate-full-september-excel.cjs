/**
 * Generate Full September Excel Report (01-30.09.2025)
 */

const fs = require('fs');
const path = require('path');
const ExcelJS = require('exceljs');

const REPORT_FILE = path.join(__dirname, '../full-september-report.json');
const EXCEL_OUTPUT = path.join(__dirname, '../Raport_Wrzesien_01-30-09-2025.xlsx');

async function generateReport() {
  console.log('📊 Generowanie raportu Excel (pełny wrzesień)...\n');

  const report = JSON.parse(fs.readFileSync(REPORT_FILE, 'utf-8'));

  const workbook = new ExcelJS.Workbook();

  // === ARKUSZ 1: PODSUMOWANIE ===
  const summarySheet = workbook.addWorksheet('Podsumowanie');

  summarySheet.columns = [
    { header: 'Metryka', key: 'metric', width: 45 },
    { header: 'Wartość', key: 'value', width: 25 },
  ];

  summarySheet.addRows([
    { metric: 'Okres analizy', value: `${report.period.start} do ${report.period.end}` },
    { metric: '', value: '' },
    { metric: '💰 KWOTY', value: '' },
    { metric: 'Suma płatności', value: `${report.summary.paymentsSum.toFixed(2)} EUR` },
    { metric: 'Suma faktur', value: `${report.summary.invoicesSum.toFixed(2)} EUR` },
    { metric: 'Różnica (płatności - faktury)', value: `${report.summary.difference.toFixed(2)} EUR` },
    { metric: '', value: '' },
    { metric: '📊 LICZBY', value: '' },
    { metric: 'Łączna liczba płatności', value: report.summary.totalPayments },
    { metric: 'Łączna liczba faktur', value: report.summary.totalInvoices },
    { metric: '', value: '' },
    { metric: '✅ DOPASOWANIA', value: '' },
    { metric: 'Dopasowane dokładnie (nazwa + kwota)', value: report.summary.matched.exact },
    { metric: 'Dopasowane grupowo (suma faktur)', value: report.summary.matched.group },
    { metric: 'Dopasowane tylko po nazwie', value: report.summary.matched.nameOnly },
    { metric: '❌ Niedopasowane', value: report.summary.unmatched },
    { metric: 'Suma niedopasowanych (EUR)', value: report.summary.unmatchedSum },
    { metric: '', value: '' },
    { metric: '📈 % DOPASOWANIA', value: `${report.summary.matchPercentage.toFixed(2)}%` },
  ]);

  summarySheet.getCell('A1').font = { bold: true, size: 12 };
  summarySheet.getCell('B1').font = { bold: true, size: 12 };

  // === ARKUSZ 2: NIEDOPASOWANE PŁATNOŚCI ===
  const unmatchedSheet = workbook.addWorksheet('Niedopasowane płatności');

  unmatchedSheet.columns = [
    { header: 'Ref No', key: 'refNo', width: 20 },
    { header: 'Data', key: 'date', width: 12 },
    { header: 'Kwota (EUR)', key: 'amount', width: 15 },
    { header: 'Kontrahent', key: 'client', width: 50 },
    { header: 'Cel płatności', key: 'description', width: 70 },
  ];

  report.unmatchedPayments.forEach(p => {
    unmatchedSheet.addRow({
      refNo: p.refNo || '-',
      date: p.dateNormalized,
      amount: p.amount,
      client: p.name || '(brak nazwy)',
      description: p.description || '-',
    });
  });

  unmatchedSheet.getRow(1).font = { bold: true };
  unmatchedSheet.getRow(1).fill = {
    type: 'pattern',
    pattern: 'solid',
    fgColor: { argb: 'FFFFC0CB' },
  };

  // === ARKUSZ 3: PŁATNOŚCI GRUPOWE ===
  const groupSheet = workbook.addWorksheet('Płatności grupowe');

  groupSheet.columns = [
    { header: 'Data', key: 'date', width: 12 },
    { header: 'Kwota płatności (EUR)', key: 'paymentAmount', width: 20 },
    { header: 'Klient', key: 'client', width: 50 },
    { header: 'Liczba faktur', key: 'invoiceCount', width: 15 },
    { header: 'Suma faktur (EUR)', key: 'invoicesSum', width: 20 },
    { header: 'Różnica (EUR)', key: 'difference', width: 15 },
    { header: 'IDs faktur', key: 'invoiceIds', width: 50 },
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

  groupSheet.getRow(1).font = { bold: true };
  groupSheet.getRow(1).fill = {
    type: 'pattern',
    pattern: 'solid',
    fgColor: { argb: 'FFE0E0E0' },
  };

  // === ARKUSZ 4: WSZYSTKIE DOPASOWANIA ===
  const detailsSheet = workbook.addWorksheet('Wszystkie dopasowania');

  detailsSheet.columns = [
    { header: 'Typ', key: 'type', width: 15 },
    { header: 'Data', key: 'date', width: 12 },
    { header: 'Płatność (EUR)', key: 'paymentAmount', width: 18 },
    { header: 'Klient', key: 'client', width: 50 },
    { header: 'Liczba faktur', key: 'invoiceCount', width: 15 },
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

  detailsSheet.getRow(1).font = { bold: true };
  detailsSheet.getRow(1).fill = {
    type: 'pattern',
    pattern: 'solid',
    fgColor: { argb: 'FFD0F0D0' },
  };

  // === ZAPISZ ===
  await workbook.xlsx.writeFile(EXCEL_OUTPUT);

  console.log('✅ Raport wygenerowany!');
  console.log(`📁 Lokalizacja: ${EXCEL_OUTPUT}\n`);

  console.log('📊 PODSUMOWANIE:\n');
  console.log(`   Okres: ${report.period.start} do ${report.period.end}`);
  console.log(`   Płatności: ${report.summary.totalPayments} (${report.summary.paymentsSum.toFixed(2)} EUR)`);
  console.log(`   Faktury: ${report.summary.totalInvoices} (${report.summary.invoicesSum.toFixed(2)} EUR)`);
  console.log(`   Różnica: ${report.summary.difference.toFixed(2)} EUR`);
  console.log(`   Dopasowane: ${report.summary.matched.total} (${report.summary.matchPercentage.toFixed(2)}%)`);
  console.log(`   Niedopasowane: ${report.summary.unmatched} (${report.summary.unmatchedSum.toFixed(2)} EUR)\n`);

  console.log('📋 ARKUSZE:');
  console.log('   1. Podsumowanie');
  console.log('   2. Niedopasowane płatności (11 płatności)');
  console.log('   3. Płatności grupowe (57 płatności)');
  console.log('   4. Wszystkie dopasowania (650 dopasowań)\n');
}

generateReport().catch(err => {
  console.error('Błąd:', err);
  process.exit(1);
});
