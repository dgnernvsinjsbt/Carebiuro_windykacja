/**
 * Parser dla flagi [LIST_POLECONY_SENT]data[/LIST_POLECONY_SENT] w komentarzach faktur
 *
 * Przykład:
 * [LIST_POLECONY_SENT]2025-01-15[/LIST_POLECONY_SENT]
 */

/**
 * Parsuje datę wysłania listu poleconego z komentarza faktury
 *
 * @param comment - komentarz faktury z Fakturowni (internal_note)
 * @returns Data wysłania lub null jeśli brak flagi
 */
export function parseListPoleconyDate(comment: string | null | undefined): Date | null {
  if (!comment) return null;

  const match = comment.match(/\[LIST_POLECONY_SENT\]([\d-]+)\[\/LIST_POLECONY_SENT\]/);
  if (!match) return null;

  const dateStr = match[1];
  const date = new Date(dateStr);

  // Sprawdź czy data jest poprawna
  if (isNaN(date.getTime())) return null;

  return date;
}

/**
 * Ustawia lub aktualizuje flagę [LIST_POLECONY_SENT] w komentarzu
 *
 * @param comment - aktualny komentarz faktury
 * @param date - data wysłania (domyślnie dzisiaj)
 * @returns Zaktualizowany komentarz z flagą
 */
export function setListPoleconyDate(
  comment: string | null | undefined,
  date: Date = new Date()
): string {
  const dateStr = date.toISOString().split('T')[0]; // Format: YYYY-MM-DD
  const newFlag = `[LIST_POLECONY_SENT]${dateStr}[/LIST_POLECONY_SENT]`;

  if (!comment) {
    return newFlag;
  }

  // Jeśli flaga już istnieje, zamień ją
  if (comment.includes('[LIST_POLECONY_SENT]')) {
    return comment.replace(
      /\[LIST_POLECONY_SENT\].*?\[\/LIST_POLECONY_SENT\]/,
      newFlag
    );
  }

  // Dodaj flagę na końcu
  return comment + '\n' + newFlag;
}

/**
 * Sprawdza czy minęło N dni od wysłania listu poleconego
 *
 * @param comment - komentarz faktury
 * @param days - liczba dni (domyślnie 31)
 * @returns true jeśli minęło >= N dni
 */
export function hasPassedDaysSinceSent(
  comment: string | null | undefined,
  days: number = 31
): boolean {
  const sentDate = parseListPoleconyDate(comment);
  if (!sentDate) return false;

  const today = new Date();
  const diffTime = today.getTime() - sentDate.getTime();
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

  return diffDays >= days;
}
