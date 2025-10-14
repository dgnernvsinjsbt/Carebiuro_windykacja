/**
 * PDF Generator - List Polecony
 *
 * Generuje HTML dla "Przedsądowego Wezwania do Zapłaty"
 * używając szablonu z bazy danych (message_templates)
 */

import { Client, Invoice } from '@/types';
import {
  getInvoicesWithThirdReminder,
  calculateTotalDebt,
  calculateDelayDays,
  formatDate,
} from './list-polecony-logic';

export interface ListPoleconyData {
  client: Client;
  invoices: Invoice[];
}

export interface LetterTemplate {
  body_top: string | null;
  body_bottom: string | null;
}

/**
 * Zamienia placeholdery {{nazwa}} na wartości rzeczywiste
 */
function replacePlaceholders(text: string, client: Client, invoices: Invoice[]): string {
  const relevantInvoices = getInvoicesWithThirdReminder(invoices);
  const totalDebt = calculateTotalDebt(invoices);
  const currency = relevantInvoices[0]?.currency || 'EUR';

  const placeholders: Record<string, string> = {
    '{{nazwa_klienta}}': client.name || 'Szanowni Państwo',
    '{{numer_faktury}}': relevantInvoices[0]?.number || '-',
    '{{kwota}}': totalDebt.toFixed(2),
    '{{waluta}}': currency,
    '{{termin}}': relevantInvoices[0]?.payment_to ? formatDate(relevantInvoices[0].payment_to) : '-',
  };

  let result = text;
  for (const [key, value] of Object.entries(placeholders)) {
    result = result.replace(new RegExp(key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'), value);
  }

  return result;
}

/**
 * Generuje HTML dla listu poleconego
 */
export function generateListPoleconyHTML(
  data: ListPoleconyData,
  template?: LetterTemplate
): string {
  const { client, invoices } = data;

  // Pobierz tylko faktury z trzecim upomnieniem
  const relevantInvoices = getInvoicesWithThirdReminder(invoices);

  // Przygotuj dane klienta
  const clientName = client.name || 'Brak nazwy';

  // Adres klienta (z pierwszej faktury lub z danych klienta)
  let clientAddress = clientName;
  if (relevantInvoices.length > 0 && relevantInvoices[0].buyer_street) {
    const invoice = relevantInvoices[0];
    clientAddress = `${clientName}<br>
${invoice.buyer_street || '[Kod], [Miasto]'}<br>
${invoice.buyer_post_code || ''} ${invoice.buyer_city || ''}, ${invoice.buyer_country || ''}`;
  }

  // Całkowita kwota zadłużenia
  const totalDebt = calculateTotalDebt(invoices);
  const currency = relevantInvoices[0]?.currency || 'EUR';

  // Generuj wiersze tabeli
  const tableRows = relevantInvoices
    .map((invoice) => {
      const delayDays = calculateDelayDays(invoice.issue_date); // Zmieniono z payment_to na issue_date
      return `<tr>
        <td>${invoice.number || '-'}</td>
        <td>${formatDate(invoice.issue_date)}</td>
        <td>${formatDate(invoice.payment_to)}</td>
        <td>${(invoice.total || 0).toFixed(2)} ${invoice.currency || 'EUR'}</td>
        <td>${delayDays}</td>
      </tr>`;
    })
    .join('');

  // Domyślny tekst NAD tabelą
  const defaultBodyTop = `${clientName}

Niniejszym wzywamy Państwa do natychmiastowej zapłaty zaległych należności wynikających z niżej wymienionych faktur. Pomimo wcześniejszych przypomnień, należności nie zostały uregulowane.`;

  // Domyślny tekst POD tabelą
  const defaultBodyBottom = `Prosimy o uregulowanie powyższej kwoty w terminie 30 dni od daty otrzymania niniejszego wezwania.

Brak wpłaty w wyznaczonym terminie spowoduje skierowanie sprawy na drogę postępowania sądowego oraz wpis do Krajowego Rejestru Dłużników, co wiąże się z dodatkowymi kosztami postępowania, odsetkami oraz opłatami egzekucyjnymi, którymi zostaniecie Państwo obciążeni.`;

  // Użyj szablonu z bazy lub domyślnego tekstu
  const bodyTop = template?.body_top
    ? replacePlaceholders(template.body_top, client, invoices)
    : defaultBodyTop;

  const bodyBottom = template?.body_bottom
    ? replacePlaceholders(template.body_bottom, client, invoices)
    : defaultBodyBottom;

  // Przekształć newline na <br> dla HTML (zachowaj akapity)
  const bodyTopHtml = bodyTop.split('\n\n').map(para =>
    `<div class="content">${para.replace(/\n/g, '<br>')}</div>`
  ).join('');

  const bodyBottomHtml = bodyBottom.split('\n\n').map(para =>
    `<div class="content">${para.replace(/\n/g, '<br>')}</div>`
  ).join('');

  // Szablon HTML
  const html = `<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <title>Przedsądowe Wezwanie do Zapłaty</title>
    <style>
        body {
            font-family: 'Times New Roman', serif;
            font-size: 11pt;
            margin: 1.5cm;
            line-height: 1.3;
        }
        .header {
            text-align: right;
            margin-bottom: 25px;
            font-size: 10pt;
        }
        .recipient {
            margin: 25px 0;
        }
        .title {
            text-align: center;
            font-size: 14pt;
            font-weight: bold;
            text-transform: uppercase;
            margin: 25px 0;
            text-decoration: underline;
        }
        .content {
            text-align: justify;
            margin-bottom: 15px;
            font-size: 11pt;
        }
        .invoice-table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 9pt;
        }
        .invoice-table th, .invoice-table td {
            border: 1px solid #000;
            padding: 4px;
            text-align: left;
        }
        .invoice-table th {
            background-color: #f0f0f0;
            font-weight: bold;
            text-align: center;
            font-size: 9pt;
        }
        .total-amount {
            text-align: center;
            font-size: 12pt;
            font-weight: bold;
            margin: 10px 0;
            padding: 6px;
            border: 2px solid #000;
        }
        .footer {
            margin-top: 25px;
            text-align: right;
        }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <strong>CBB-OFFICE GmbH</strong><br>
            Brunów 43, 59-140 Chocianów, Polska<br>
            NIP PL5020122714<br>
            poczta@cbb-office.pl<br>
            https://cbb-office.pl<br>
            Telefon: +48517765655
        </div>
    </div>

    <div class="recipient">
        ${clientAddress}
    </div>

    <div class="title">Przedsądowe Wezwanie do Zapłaty</div>

    ${bodyTopHtml}

    <div class="content"><strong>Szczegóły zaległości:</strong></div>

    <table class="invoice-table">
        <thead>
            <tr>
                <th>Numer faktury</th>
                <th>Data wystawienia</th>
                <th>Termin płatności</th>
                <th>Kwota</th>
                <th>Dni zwłoki</th>
            </tr>
        </thead>
        <tbody>
            ${tableRows}
        </tbody>
    </table>

    <div class="total-amount">
        CAŁKOWITA KWOTA ZALEGŁOŚCI: ${totalDebt.toFixed(2)} ${currency}
    </div>

    ${bodyBottomHtml}

    <div class="footer">
        Z poważaniem,<br><br>
        CBB-OFFICE GmbH
    </div>
</body>
</html>`;

  return html;
}
