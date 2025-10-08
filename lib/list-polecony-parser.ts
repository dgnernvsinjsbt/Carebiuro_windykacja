/**
 * List Polecony Parser
 *
 * Parsuje i aktualizuje tag [LIST_POLECONY]true/false[/LIST_POLECONY] w komentarzu klienta (note)
 *
 * Logika:
 * - Brak tagu [LIST_POLECONY] = list polecony wyłączony (false)
 * - [LIST_POLECONY]false[/LIST_POLECONY] = list polecony wyłączony
 * - [LIST_POLECONY]true[/LIST_POLECONY] = list polecony włączony (klient kwalifikuje się do eskalacji)
 */

/**
 * Parse LIST_POLECONY status from client note
 * @param note - Komentarz klienta z Fakturowni
 * @returns true jeśli list polecony włączony, false jeśli wyłączony lub brak tagu
 */
export function parseListPolecony(note: string | null | undefined): boolean {
  if (!note) return false;

  const match = note.match(/\[LIST_POLECONY\](true|false)\[\/LIST_POLECONY\]/);
  if (!match) return false; // Brak tagu = wyłączony

  return match[1] === 'true';
}

/**
 * Update LIST_POLECONY tag in client note
 * @param note - Obecny komentarz klienta
 * @param enabled - Czy list polecony ma być włączony (true) czy wyłączony (false)
 * @returns Zaktualizowany komentarz z tagiem [LIST_POLECONY]
 */
export function updateListPolecony(
  note: string | null | undefined,
  enabled: boolean
): string {
  const currentNote = note || '';
  const newTag = `[LIST_POLECONY]${enabled}[/LIST_POLECONY]`;

  // Jeśli tag już istnieje, zamień go
  if (currentNote.match(/\[LIST_POLECONY\](true|false)\[\/LIST_POLECONY\]/)) {
    return currentNote.replace(
      /\[LIST_POLECONY\](true|false)\[\/LIST_POLECONY\]/,
      newTag
    );
  }

  // Jeśli tag nie istnieje, dodaj go w TEJ SAMEJ LINII (bez \n)
  return currentNote.trim() ? `${currentNote.trim()} ${newTag}` : newTag;
}

/**
 * Remove LIST_POLECONY tag from client note
 * @param note - Komentarz klienta
 * @returns Komentarz bez tagu [LIST_POLECONY]
 */
export function removeListPolecony(note: string | null | undefined): string {
  if (!note) return '';

  return note
    .replace(/\[LIST_POLECONY\](true|false)\[\/LIST_POLECONY\]/, '')
    .replace(/\n\n+/g, '\n') // Usuń podwójne nowe linie
    .trim();
}

/**
 * Parse LIST_POLECONY_IGNORED status from client note
 * @param note - Komentarz klienta z Fakturowni
 * @returns true jeśli klient jest ignorowany
 */
export function parseListPoleconyIgnored(note: string | null | undefined): boolean {
  if (!note) return false;

  const match = note.match(/\[LIST_POLECONY_IGNORED\](true|false)\[\/LIST_POLECONY_IGNORED\]/);
  if (!match) return false;

  return match[1] === 'true';
}

/**
 * Update LIST_POLECONY_IGNORED tag in client note
 * @param note - Obecny komentarz klienta
 * @param ignored - Czy klient ma być ignorowany
 * @returns Zaktualizowany komentarz z tagiem [LIST_POLECONY_IGNORED]
 */
export function updateListPoleconyIgnored(
  note: string | null | undefined,
  ignored: boolean
): string {
  const currentNote = note || '';
  const newTag = `[LIST_POLECONY_IGNORED]${ignored}[/LIST_POLECONY_IGNORED]`;

  // Jeśli tag już istnieje, zamień go
  if (currentNote.match(/\[LIST_POLECONY_IGNORED\](true|false)\[\/LIST_POLECONY_IGNORED\]/)) {
    return currentNote.replace(
      /\[LIST_POLECONY_IGNORED\](true|false)\[\/LIST_POLECONY_IGNORED\]/,
      newTag
    );
  }

  // Jeśli tag nie istnieje, dodaj go w TEJ SAMEJ LINII (bez \n)
  return currentNote.trim() ? `${currentNote.trim()} ${newTag}` : newTag;
}
