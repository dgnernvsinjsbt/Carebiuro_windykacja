/**
 * Centralna funkcja do zarządzania flagami klienta - V2 (nowy format)
 *
 * WINDYKACJA - osobna flaga boolean
 * LIST_POLECONY_STATUS - jedna flaga z wartościami: sent/ignore/null
 * LIST_POLECONY_STATUS_DATE - data ostatniej zmiany statusu
 *
 * Format:
 * [WINDYKACJA]true[/WINDYKACJA] [LIST_POLECONY_STATUS]sent[/LIST_POLECONY_STATUS] [LIST_POLECONY_STATUS_DATE]2025-09-01[/LIST_POLECONY_STATUS_DATE]
 */

export type ListPoleconyStatus = 'sent' | 'ignore' | null;

export interface ClientFlagsV2 {
  windykacja: boolean;
  listPoleconyStatus: ListPoleconyStatus;
  listPoleconyStatusDate: string | null;
}

/**
 * Parsuje flagi z note klienta (nowy format)
 */
export function parseClientFlags(note: string | null | undefined): ClientFlagsV2 {
  const noteStr = note || '';

  // WINDYKACJA
  const windykacja = /\[WINDYKACJA\]true\[\/WINDYKACJA\]/.test(noteStr);

  // LIST_POLECONY_STATUS
  const statusMatch = noteStr.match(/\[LIST_POLECONY_STATUS\](sent|ignore)\[\/LIST_POLECONY_STATUS\]/);
  const listPoleconyStatus: ListPoleconyStatus = statusMatch ? (statusMatch[1] as ListPoleconyStatus) : null;

  // LIST_POLECONY_STATUS_DATE
  const dateMatch = noteStr.match(/\[LIST_POLECONY_STATUS_DATE\](.*?)\[\/LIST_POLECONY_STATUS_DATE\]/);
  const listPoleconyStatusDate = dateMatch && dateMatch[1] ? dateMatch[1] : null;

  return {
    windykacja,
    listPoleconyStatus,
    listPoleconyStatusDate,
  };
}

/**
 * Aktualizuje flagi klienta (nowy format)
 */
export function updateClientFlags(
  note: string | null | undefined,
  updates: Partial<ClientFlagsV2>
): string {
  let noteStr = note || '';

  // ZAWSZE usuń stare flagi LIST_POLECONY przy jakiejkolwiek aktualizacji (auto-migracja)
  noteStr = noteStr.replace(/\[LIST_POLECONY\](true|false|sent|ignore)\[\/LIST_POLECONY\]\s*/g, '');
  noteStr = noteStr.replace(/\[LIST_POLECONY_IGNORED\](true|false)\[\/LIST_POLECONY_IGNORED\]\s*/g, '');
  noteStr = noteStr.replace(/\[LIST_POLECONY_SENT_DATE\].*?\[\/LIST_POLECONY_SENT_DATE\]\s*/g, '');
  noteStr = noteStr.replace(/\[LIST_POLECONY_IGNORED_DATE\].*?\[\/LIST_POLECONY_IGNORED_DATE\]\s*/g, '');

  // 1. WINDYKACJA
  if (updates.windykacja !== undefined) {
    // Usuń starą flagę
    noteStr = noteStr.replace(/\[WINDYKACJA\](true|false)\[\/WINDYKACJA\]\n?/g, '');

    // Dodaj nową flagę na początku
    noteStr = `[WINDYKACJA]${updates.windykacja}[/WINDYKACJA]\n${noteStr}`;
  }

  // 2. LIST_POLECONY_STATUS
  if (updates.listPoleconyStatus !== undefined) {
    // Usuń stare flagi (migracja)
    noteStr = noteStr.replace(/\[LIST_POLECONY\](true|false|sent|ignore)\[\/LIST_POLECONY\]\n?/g, '');
    noteStr = noteStr.replace(/\[LIST_POLECONY_IGNORED\](true|false)\[\/LIST_POLECONY_IGNORED\]\n?/g, '');
    noteStr = noteStr.replace(/\[LIST_POLECONY_SENT_DATE\].*?\[\/LIST_POLECONY_SENT_DATE\]\n?/g, '');
    noteStr = noteStr.replace(/\[LIST_POLECONY_IGNORED_DATE\].*?\[\/LIST_POLECONY_IGNORED_DATE\]\n?/g, '');

    if (updates.listPoleconyStatus === null) {
      // Usuń status jeśli null
      noteStr = noteStr.replace(/\[LIST_POLECONY_STATUS\](sent|ignore)\[\/LIST_POLECONY_STATUS\]\n?/g, '');
    } else {
      // Usuń istniejący status
      noteStr = noteStr.replace(/\[LIST_POLECONY_STATUS\](sent|ignore)\[\/LIST_POLECONY_STATUS\]\n?/g, '');
      // Dodaj nowy status (po WINDYKACJA)
      const windMatch = noteStr.match(/\[WINDYKACJA\](true|false)\[\/WINDYKACJA\]\n?/);
      if (windMatch) {
        noteStr = noteStr.replace(
          /(\[WINDYKACJA\](true|false)\[\/WINDYKACJA\]\n?)/,
          `$1[LIST_POLECONY_STATUS]${updates.listPoleconyStatus}[/LIST_POLECONY_STATUS]\n`
        );
      } else {
        noteStr = `[LIST_POLECONY_STATUS]${updates.listPoleconyStatus}[/LIST_POLECONY_STATUS]\n${noteStr}`;
      }
    }
  }

  // 3. LIST_POLECONY_STATUS_DATE
  if (updates.listPoleconyStatusDate !== undefined) {
    if (updates.listPoleconyStatusDate === null) {
      // Usuń datę jeśli null
      noteStr = noteStr.replace(/\[LIST_POLECONY_STATUS_DATE\].*?\[\/LIST_POLECONY_STATUS_DATE\]\n?/g, '');
    } else {
      // Usuń istniejącą datę
      noteStr = noteStr.replace(/\[LIST_POLECONY_STATUS_DATE\].*?\[\/LIST_POLECONY_STATUS_DATE\]\n?/g, '');
      // Dodaj nową datę (po STATUS)
      const statusMatch = noteStr.match(/\[LIST_POLECONY_STATUS\](sent|ignore)\[\/LIST_POLECONY_STATUS\]\n?/);
      if (statusMatch) {
        noteStr = noteStr.replace(
          /(\[LIST_POLECONY_STATUS\](sent|ignore)\[\/LIST_POLECONY_STATUS\]\n?)/,
          `$1[LIST_POLECONY_STATUS_DATE]${updates.listPoleconyStatusDate}[/LIST_POLECONY_STATUS_DATE]\n`
        );
      } else {
        noteStr = `[LIST_POLECONY_STATUS_DATE]${updates.listPoleconyStatusDate}[/LIST_POLECONY_STATUS_DATE]\n${noteStr}`;
      }
    }
  }

  // Wyczyść wielokrotne newline'y i trim
  noteStr = noteStr.replace(/\n\n+/g, '\n').trim();

  return noteStr;
}

/**
 * Wygodne funkcje dla konkretnych akcji
 */

export function setWindykacja(note: string | null | undefined, value: boolean): string {
  return updateClientFlags(note, { windykacja: value });
}

export function setListPoleconyStatusSent(note: string | null | undefined, sentDate: string): string {
  return updateClientFlags(note, {
    listPoleconyStatus: 'sent',
    listPoleconyStatusDate: sentDate,
  });
}

export function setListPoleconyStatusIgnore(note: string | null | undefined, ignoredDate: string): string {
  return updateClientFlags(note, {
    listPoleconyStatus: 'ignore',
    listPoleconyStatusDate: ignoredDate,
  });
}

export function clearListPoleconyStatus(note: string | null | undefined): string {
  return updateClientFlags(note, {
    listPoleconyStatus: null,
    listPoleconyStatusDate: null,
  });
}
