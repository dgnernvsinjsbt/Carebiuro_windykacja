/**
 * Centralna funkcja do zarządzania flagami klienta
 *
 * WSZYSTKIE flagi są zawsze w JEDNEJ LINII:
 * [WINDYKACJA]true[/WINDYKACJA] [LIST_POLECONY]true[/LIST_POLECONY] [LIST_POLECONY_IGNORED]false[/LIST_POLECONY_IGNORED]
 */

export interface ClientFlags {
  windykacja: boolean;
  listPolecony: boolean;
  listPoleconyIgnored: boolean;
}

/**
 * Parsuje flagi z note klienta
 */
export function parseClientFlags(note: string | null | undefined): ClientFlags {
  const noteStr = note || '';

  return {
    windykacja: /\[WINDYKACJA\]true\[\/WINDYKACJA\]/.test(noteStr),
    listPolecony: /\[LIST_POLECONY\]true\[\/LIST_POLECONY\]/.test(noteStr),
    listPoleconyIgnored: /\[LIST_POLECONY_IGNORED\]true\[\/LIST_POLECONY_IGNORED\]/.test(noteStr),
  };
}

/**
 * Aktualizuje flagi klienta - ZAWSZE w jednej linii
 *
 * @param note - obecny note klienta
 * @param updates - które flagi zaktualizować (pozostałe zostają bez zmian)
 * @returns nowy note z zaktualizowanymi flagami w jednej linii
 */
export function updateClientFlags(
  note: string | null | undefined,
  updates: Partial<ClientFlags>
): string {
  const currentNote = note || '';

  // Parsuj obecne flagi
  const currentFlags = parseClientFlags(currentNote);

  // Zmerguj z updates
  const newFlags: ClientFlags = {
    windykacja: updates.windykacja !== undefined ? updates.windykacja : currentFlags.windykacja,
    listPolecony: updates.listPolecony !== undefined ? updates.listPolecony : currentFlags.listPolecony,
    listPoleconyIgnored: updates.listPoleconyIgnored !== undefined ? updates.listPoleconyIgnored : currentFlags.listPoleconyIgnored,
  };

  // Wygeneruj nowe flagi w jednej linii
  const newFlagsStr = [
    `[WINDYKACJA]${newFlags.windykacja}[/WINDYKACJA]`,
    `[LIST_POLECONY]${newFlags.listPolecony}[/LIST_POLECONY]`,
    `[LIST_POLECONY_IGNORED]${newFlags.listPoleconyIgnored}[/LIST_POLECONY_IGNORED]`,
  ].join(' ');

  // Usuń wszystkie stare flagi z note
  let cleanedNote = currentNote
    .replace(/\[WINDYKACJA\](true|false)\[\/WINDYKACJA\]/g, '')
    .replace(/\[LIST_POLECONY\](true|false)\[\/LIST_POLECONY\]/g, '')
    .replace(/\[LIST_POLECONY_IGNORED\](true|false)\[\/LIST_POLECONY_IGNORED\]/g, '')
    .trim();

  // Dodaj nowe flagi na początku (jeśli był jakiś inny tekst, zachowaj go)
  return cleanedNote ? `${newFlagsStr} ${cleanedNote}` : newFlagsStr;
}

/**
 * Wygodne funkcje dla konkretnych akcji
 */

export function setWindykacja(note: string | null | undefined, value: boolean): string {
  return updateClientFlags(note, { windykacja: value });
}

export function setListPolecony(note: string | null | undefined, value: boolean): string {
  return updateClientFlags(note, { listPolecony: value });
}

export function setListPoleconyIgnored(note: string | null | undefined, value: boolean): string {
  return updateClientFlags(note, { listPoleconyIgnored: value });
}
