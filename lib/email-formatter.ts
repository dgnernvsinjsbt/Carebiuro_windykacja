/**
 * Konwertuje plain text na profesjonalny HTML email
 *
 * Obsługuje:
 * - Automatyczne akapity (podwójne \n)
 * - Pogrubienie dla nazwy firmy (Carebiuro)
 * - Zachowanie placeholderów {{...}}
 * - Profesjonalny styling
 */
export function plainTextToHtml(plainText: string): string {
  // Split na akapity (podwójne newline)
  const paragraphs = plainText
    .trim()
    .split(/\n\n+/) // Split po 2+ newline
    .filter(p => p.trim().length > 0);

  // Konwertuj każdy akapit
  const htmlParagraphs = paragraphs.map(paragraph => {
    let html = paragraph
      .trim()
      .replace(/\n/g, '<br>'); // Pojedyncze \n → <br>

    // Pogrubienie dla Carebiuro
    html = html.replace(/\bCarebiuro\b/g, '<strong>Carebiuro</strong>');

    // Pogrubienie dla placeholderów z wartościami
    html = html.replace(/\{\{invoice_number\}\}/g, '<strong>{{invoice_number}}</strong>');
    html = html.replace(/\{\{amount\}\}/g, '<strong>{{amount}}</strong>');
    html = html.replace(/\{\{due_date\}\}/g, '<strong>{{due_date}}</strong>');

    // Specjalne formatowanie dla słów kluczowych
    html = html.replace(/\bOSTATECZNE przypomnienie\b/gi, '<strong style="color: #d32f2f;">OSTATECZNE przypomnienie</strong>');
    html = html.replace(/\bDrugie przypomnienie\b/gi, '<strong>Drugie przypomnienie</strong>');

    // Użyj DIV zamiast P - Gmail lepiej respektuje
    return `<div style="margin-bottom: 20px;">${html}</div>`;
  });

  // Owinięcie w HTML z profesjonalnym stylingiem
  // Dodaj także spacing przez <br> między paragrafami jako backup
  return `<html><body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px;">${htmlParagraphs.join('<br>')}</body></html>`;
}

/**
 * Konwertuje plain text na body_text (fallback bez HTML)
 */
export function plainTextToText(plainText: string): string {
  return plainText.trim();
}