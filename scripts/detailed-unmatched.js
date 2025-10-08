/**
 * Detailed Unmatched Payments Report
 */

const fs = require('fs');
const path = require('path');

const REPORT_FILE = path.join(__dirname, '../full-september-report.json');

const report = JSON.parse(fs.readFileSync(REPORT_FILE, 'utf-8'));

console.log('🔴 SZCZEGÓŁOWY RAPORT NIEDOPASOWANYCH PŁATNOŚCI\n');
console.log(`Okres: ${report.period.start} do ${report.period.end}`);
console.log(`Niedopasowanych płatności: ${report.unmatchedPayments.length}\n`);
console.log('═'.repeat(100));
console.log('');

report.unmatchedPayments.forEach((payment, idx) => {
  console.log(`${idx + 1}. PŁATNOŚĆ #${idx + 1}`);
  console.log('─'.repeat(100));
  console.log(`   Ref No:              ${payment.refNo || '(brak)'}`);
  console.log(`   Data:                ${payment.dateNormalized} (${payment.date})`);
  console.log(`   Kwota:               ${payment.amount.toFixed(2)} EUR`);
  console.log(`   Kontrahent:          ${payment.name || '(brak nazwy)'}`);
  console.log(`   Cel płatności:       ${payment.description || '(brak opisu)'}`);
  console.log('');
});

console.log('═'.repeat(100));
console.log(`\nŁączna suma niedopasowanych: ${report.summary.unmatchedSum.toFixed(2)} EUR`);

// Analiza typów niedopasowanych
const zwroty = report.unmatchedPayments.filter(p =>
  p.description && p.description.toUpperCase().includes('ZWROT')
);

const bezNazwy = report.unmatchedPayments.filter(p => !p.name || p.name.trim() === '');

console.log('\n📊 KATEGORIE NIEDOPASOWANYCH:');
console.log(`   - ZWROTY: ${zwroty.length} (${zwroty.reduce((s, p) => s + p.amount, 0).toFixed(2)} EUR)`);
console.log(`   - Bez nazwy kontrahenta: ${bezNazwy.length} (${bezNazwy.reduce((s, p) => s + p.amount, 0).toFixed(2)} EUR)`);
console.log(`   - Inne: ${report.unmatchedPayments.length - zwroty.length - bezNazwy.length + zwroty.filter(p => !p.name).length}`);
