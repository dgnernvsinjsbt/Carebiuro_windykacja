import { readFileSync } from 'fs';

const report = JSON.parse(readFileSync('full-september-report.json', 'utf-8'));

console.log('\n11 NIEDOPASOWANYCH PŁATNOŚCI:\n');
console.log('Data         Ref No');
console.log('─'.repeat(50));

report.unmatchedPayments.forEach(payment => {
  const date = payment.dateNormalized || payment.date;
  const refNo = payment.refNo || '(brak)';
  console.log(`${date}   ${refNo}`);
});

console.log('\n');
