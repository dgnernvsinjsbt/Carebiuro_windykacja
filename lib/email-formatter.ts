/**
 * Konwertuje plain text na profesjonalny HTML email
 *
 * Używa table-based layout (enterprise standard):
 * - Kompatybilny z Gmail, Outlook, Apple Mail
 * - Inline styles (nie external CSS)
 * - 600px szerokość kontenera
 * - Sensowne odstępy między paragrafami (12px)
 */
export function plainTextToHtml(plainText: string): string {
  // Split na akapity (podwójne newline)
  const paragraphs = plainText
    .trim()
    .split(/\n\n+/)
    .filter(p => p.trim().length > 0);

  // Konwertuj każdy akapit
  const htmlParagraphs = paragraphs.map((paragraph, index) => {
    let html = paragraph
      .trim()
      .replace(/\n/g, '<br>'); // Pojedyncze \n → <br>

    // Pogrubienie dla Carebiuro
    html = html.replace(/\bCarebiuro\b/g, '<strong>Carebiuro</strong>');

    // Pogrubienie dla placeholderów
    html = html.replace(/\{\{invoice_number\}\}/g, '<strong>{{invoice_number}}</strong>');
    html = html.replace(/\{\{amount\}\}/g, '<strong>{{amount}}</strong>');
    html = html.replace(/\{\{due_date\}\}/g, '<strong>{{due_date}}</strong>');

    // Specjalne formatowanie
    html = html.replace(/\bOSTATECZNE przypomnienie\b/gi, '<strong style="color: #d32f2f;">OSTATECZNE przypomnienie</strong>');
    html = html.replace(/\bDrugie przypomnienie\b/gi, '<strong>Drugie przypomnienie</strong>');

    // Spacing logic:
    // - Normalny spacing między paragrafami: 12px
    // - Przed ostatnim paragrafem (podpis): 24px - wizualnie oddziela podpis od treści
    // - Ostatni paragraf: 0px
    let paddingBottom = '12px';
    if (index === paragraphs.length - 1) {
      paddingBottom = '0'; // Ostatni - bez spacing
    } else if (index === paragraphs.length - 2) {
      paddingBottom = '24px'; // Przedostatni - podwójny spacing przed podpisem
    }

    return `<tr>
      <td style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 16px; line-height: 1.6; color: #444444; padding-bottom: ${paddingBottom};">
        ${html}
      </td>
    </tr>`;
  });

  // Enterprise-grade email template (table-based)
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    @media only screen and (max-width: 600px) {
      .container { width: 100% !important; }
      .content { padding: 20px !important; }
    }
  </style>
</head>
<body style="margin: 0; padding: 0; background-color: #f5f6f7;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f5f6f7;">
    <tr>
      <td align="center" style="padding: 20px 0;">
        <table class="container" width="600" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff; border-radius: 8px;">
          <tr>
            <td class="content" style="padding: 30px 40px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                ${htmlParagraphs.join('\n                ')}
              </table>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;
}

/**
 * Konwertuje plain text na body_text (fallback bez HTML)
 */
export function plainTextToText(plainText: string): string {
  return plainText.trim();
}