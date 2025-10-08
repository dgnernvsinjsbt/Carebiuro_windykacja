const fs = require('fs');

const invoices = JSON.parse(fs.readFileSync('invoices-filtered.json', 'utf-8'));
const paymentsLines = fs.readFileSync('payments.csv', 'utf-8').split('\n').filter(l => l.trim());

// Parse payments z CSV
const payments = paymentsLines.slice(1).map(line => {
  const parts = line.split('\t');
  const dateParts = parts[0]?.trim().split('.');
  const dateNormalized = dateParts ? `${dateParts[2]}-${dateParts[1].padStart(2, '0')}-${dateParts[0].padStart(2, '0')}` : null;
  const amount = parseFloat(parts[3]?.replace(',', '.')) || 0;
  return { date: dateNormalized, amount };
}).filter(p => p.date);

// Grupuj faktury po sell_date
const invoicesByDate = {};
invoices.forEach(inv => {
  const date = inv.sell_date;
  if (!date) return;
  if (!invoicesByDate[date]) {
    invoicesByDate[date] = { count: 0, sum: 0 };
  }
  invoicesByDate[date].count++;
  invoicesByDate[date].sum += parseFloat(inv.price_gross) || 0;
});

// Grupuj płatności po dacie
const paymentsByDate = {};
payments.forEach(pay => {
  const date = pay.date;
  if (!paymentsByDate[date]) {
    paymentsByDate[date] = { count: 0, sum: 0 };
  }
  paymentsByDate[date].count++;
  paymentsByDate[date].sum += pay.amount;
});

// Wszystkie daty (z faktur i płatności)
const allDates = new Set([...Object.keys(invoicesByDate), ...Object.keys(paymentsByDate)]);
const sortedDates = Array.from(allDates).sort();

// Filtruj tylko wrzesień 2025
const septemberDates = sortedDates.filter(d => d >= '2025-09-01' && d <= '2025-09-30');

// Analiza dzienna
const dailyAnalysis = [];
let totalInvoicesSum = 0;
let totalPaymentsSum = 0;

septemberDates.forEach(date => {
  const invoiceData = invoicesByDate[date] || { count: 0, sum: 0 };
  const paymentData = paymentsByDate[date] || { count: 0, sum: 0 };

  totalInvoicesSum += invoiceData.sum;
  totalPaymentsSum += paymentData.sum;

  const difference = paymentData.sum - invoiceData.sum;

  dailyAnalysis.push({
    date,
    invoices: {
      count: invoiceData.count,
      sum: Math.round(invoiceData.sum * 100) / 100
    },
    payments: {
      count: paymentData.count,
      sum: Math.round(paymentData.sum * 100) / 100
    },
    difference: Math.round(difference * 100) / 100
  });
});

// Zapisz raport JSON
const report = {
  period: '01-30.09.2025',
  summary: {
    totalInvoices: Math.round(totalInvoicesSum * 100) / 100,
    totalPayments: Math.round(totalPaymentsSum * 100) / 100,
    totalDifference: Math.round((totalPaymentsSum - totalInvoicesSum) * 100) / 100
  },
  dailyBreakdown: dailyAnalysis
};

fs.writeFileSync('daily-analysis-report.json', JSON.stringify(report, null, 2));

// Wyświetl w konsoli
console.log('\n📊 ANALIZA DZIENNA: FAKTURY vs PŁATNOŚCI (01-30.09.2025)\n');
console.log('Data       | Faktury (szt/€)    | Płatności (szt/€)  | Różnica (€)');
console.log('─'.repeat(80));

dailyAnalysis.forEach(day => {
  const dateStr = day.date;
  const invStr = `${day.invoices.count} szt / ${day.invoices.sum.toFixed(2)} €`.padEnd(18);
  const payStr = `${day.payments.count} szt / ${day.payments.sum.toFixed(2)} €`.padEnd(18);
  const diffStr = day.difference >= 0 ? `+${day.difference.toFixed(2)}` : day.difference.toFixed(2);

  console.log(`${dateStr} | ${invStr} | ${payStr} | ${diffStr}`);
});

console.log('─'.repeat(80));
console.log(`SUMA       | ${totalInvoicesSum.toFixed(2)} €`.padEnd(38) + ` | ${totalPaymentsSum.toFixed(2)} €`.padEnd(18) + ` | ${(totalPaymentsSum - totalInvoicesSum).toFixed(2)}`);
console.log('\n✅ Zapisano: daily-analysis-report.json\n');
