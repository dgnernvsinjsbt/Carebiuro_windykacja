/**
 * Windykacja Parser
 *
 * Parsuje i aktualizuje tag [WINDYKACJA]true/false[/WINDYKACJA] w komentarzu klienta (note)
 *
 * Logika:
 * - Brak tagu [WINDYKACJA] = windykacja wyłączona (false)
 * - [WINDYKACJA]false[/WINDYKACJA] = windykacja wyłączona
 * - [WINDYKACJA]true[/WINDYKACJA] = windykacja włączona
 */

/**
 * Parse WINDYKACJA status from client note
 * @param note - Komentarz klienta z Fakturowni
 * @returns true jeśli windykacja włączona, false jeśli wyłączona lub brak tagu
 */
export function parseWindykacja(note: string | null | undefined): boolean {
  if (!note) return false;

  const match = note.match(/\[WINDYKACJA\](true|false)\[\/WINDYKACJA\]/);
  if (!match) return false; // Brak tagu = wyłączona

  return match[1] === 'true';
}

/**
 * Update WINDYKACJA tag in client note
 * @param note - Obecny komentarz klienta
 * @param enabled - Czy windykacja ma być włączona (true) czy wyłączona (false)
 * @returns Zaktualizowany komentarz z tagiem [WINDYKACJA]
 */
export function updateWindykacja(
  note: string | null | undefined,
  enabled: boolean
): string {
  const currentNote = note || '';
  const newTag = `[WINDYKACJA]${enabled}[/WINDYKACJA]`;

  // Jeśli tag już istnieje, zamień go
  if (currentNote.match(/\[WINDYKACJA\](true|false)\[\/WINDYKACJA\]/)) {
    return currentNote.replace(
      /\[WINDYKACJA\](true|false)\[\/WINDYKACJA\]/,
      newTag
    );
  }

  // Jeśli tag nie istnieje, dodaj go na końcu
  return currentNote.trim() ? `${currentNote.trim()}\n${newTag}` : newTag;
}

/**
 * Remove WINDYKACJA tag from client note
 * @param note - Komentarz klienta
 * @returns Komentarz bez tagu [WINDYKACJA]
 */
export function removeWindykacja(note: string | null | undefined): string {
  if (!note) return '';

  return note
    .replace(/\[WINDYKACJA\](true|false)\[\/WINDYKACJA\]/, '')
    .replace(/\n\n+/g, '\n') // Usuń podwójne nowe linie
    .trim();
}
