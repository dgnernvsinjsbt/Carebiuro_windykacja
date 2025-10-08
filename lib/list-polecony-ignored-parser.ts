/**
 * Parser dla flagi [LIST_POLECONY_IGNORED]data[/LIST_POLECONY_IGNORED] w komentarzach faktur
 *
 * Przykład:
 * [LIST_POLECONY_IGNORED]2025-01-15[/LIST_POLECONY_IGNORED]
 */

/**
 * Parsuje datę ignorowania z komentarza faktury
 *
 * @param comment - komentarz faktury z Fakturowni (internal_note)
 * @returns Data ignorowania lub null jeśli brak flagi
 */
export function parseListPoleconyIgnoredDate(comment: string | null | undefined): Date | null {
  if (!comment) return null;

  const match = comment.match(/\[LIST_POLECONY_IGNORED\]([\d-]+)\[\/LIST_POLECONY_IGNORED\]/);
  if (!match) return null;

  const dateStr = match[1];
  const date = new Date(dateStr);

  // Sprawdź czy data jest poprawna
  if (isNaN(date.getTime())) return null;

  return date;
}

/**
 * Ustawia lub aktualizuje flagę [LIST_POLECONY_IGNORED] w komentarzu
 *
 * @param comment - aktualny komentarz faktury
 * @param date - data ignorowania (domyślnie dzisiaj)
 * @returns Zaktualizowany komentarz z flagą
 */
export function setListPoleconyIgnoredDate(
  comment: string | null | undefined,
  date: Date = new Date()
): string {
  const dateStr = date.toISOString().split('T')[0]; // Format: YYYY-MM-DD
  const newFlag = `[LIST_POLECONY_IGNORED]${dateStr}[/LIST_POLECONY_IGNORED]`;

  if (!comment) {
    return newFlag;
  }

  // Jeśli flaga już istnieje, zamień ją
  if (comment.includes('[LIST_POLECONY_IGNORED]')) {
    return comment.replace(
      /\[LIST_POLECONY_IGNORED\].*?\[\/LIST_POLECONY_IGNORED\]/,
      newFlag
    );
  }

  // Dodaj flagę w TEJ SAMEJ LINII (bez \n)
  return comment.trim() + ' ' + newFlag;
}
