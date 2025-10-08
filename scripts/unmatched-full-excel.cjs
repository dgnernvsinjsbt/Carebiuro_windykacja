const ExcelJS = require('exceljs');
const fs = require('fs');

(async () => {
  const report = JSON.parse(fs.readFileSync('full-september-report.json', 'utf-8'));

  const workbook = new ExcelJS.Workbook();
  const worksheet = workbook.addWorksheet('Niedopasowane płatności');

  // Nagłówki
  worksheet.columns = [
    { header: 'Data', key: 'date', width: 15 },
    { header: 'Kwota', key: 'amount', width: 12 },
    { header: 'Nadawca', key: 'name', width: 30 },
    { header: 'Opis', key: 'description', width: 50 },
    { header: 'Ref No', key: 'refNo', width: 20 }
  ];

  // Dane
  report.unmatchedPayments.forEach(payment => {
    worksheet.addRow({
      date: payment.dateNormalized || payment.date,
      amount: payment.amount,
      name: payment.name || '(brak)',
      description: payment.description || '(brak)',
      refNo: payment.refNo || '(brak)'
    });
  });

  // Zapisz
  await workbook.xlsx.writeFile('niedopasowane-platnosci.xlsx');
  console.log('✅ Utworzono: niedopasowane-platnosci.xlsx');
})();
