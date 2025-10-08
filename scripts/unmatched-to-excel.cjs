const ExcelJS = require('exceljs');
const fs = require('fs');

(async () => {
  const report = JSON.parse(fs.readFileSync('full-september-report.json', 'utf-8'));

  const workbook = new ExcelJS.Workbook();
  const worksheet = workbook.addWorksheet('Niedopasowane płatności');

  // Nagłówki
  worksheet.columns = [
    { header: 'Data', key: 'date', width: 15 },
    { header: 'Ref No', key: 'refNo', width: 20 }
  ];

  // Dane
  report.unmatchedPayments.forEach(payment => {
    worksheet.addRow({
      date: payment.dateNormalized || payment.date,
      refNo: payment.refNo || '(brak)'
    });
  });

  // Zapisz
  await workbook.xlsx.writeFile('niedopasowane-platnosci.xlsx');
  console.log('✅ Utworzono: niedopasowane-platnosci.xlsx');
})();
