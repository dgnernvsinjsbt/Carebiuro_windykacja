/**
 * Funkcje do zarządzania flagami faktur w internal_note
 *
 * Flagi są zapisywane w formacie:
 * [LIST_POLECONY_STATUS]sent[/LIST_POLECONY_STATUS] - wysłany list polecony
 * [LIST_POLECONY_STATUS]ignore[/LIST_POLECONY_STATUS] - zignorowany
 * [LIST_POLECONY_STATUS_DATE]2025-09-01[/LIST_POLECONY_STATUS_DATE]
 */

export type ListPoleconyStatus = 'sent' | 'ignore' | null;

export interface InvoiceFlags {
  listPoleconyStatus: ListPoleconyStatus;
  listPoleconyStatusDate: string | null;
}

/**
 * Parsuje flagi z internal_note faktury
 */
export function parseInvoiceFlags(internalNote: string | null | undefined): InvoiceFlags {
  const note = internalNote || '';

  // Parsuj status LIST_POLECONY (sent/ignore)
  const statusMatch = note.match(/\[LIST_POLECONY_STATUS\](sent|ignore)\[\/LIST_POLECONY_STATUS\]/);
  const listPoleconyStatus: ListPoleconyStatus = statusMatch ? (statusMatch[1] as ListPoleconyStatus) : null;

  // Parsuj datę
  const dateMatch = note.match(/\[LIST_POLECONY_STATUS_DATE\](.*?)\[\/LIST_POLECONY_STATUS_DATE\]/);
  const listPoleconyStatusDate = dateMatch && dateMatch[1] ? dateMatch[1] : null;

  return {
    listPoleconyStatus,
    listPoleconyStatusDate,
  };
}

/**
 * Aktualizuje flagi w internal_note faktury
 * WAŻNE: Aktualizuje TYLKO przekazane flagi, nie usuwa innych!
 */
export function updateInvoiceFlags(
  internalNote: string | null | undefined,
  updates: Partial<InvoiceFlags>
): string {
  let note = internalNote || '';

  // 1. LIST_POLECONY_STATUS
  if (updates.listPoleconyStatus !== undefined) {
    // Usuń stare tagi (dla migracji ze starego formatu)
    note = note.replace(/\[LIST_POLECONY\](true|false)\[\/LIST_POLECONY\]\n?/g, '');
    note = note.replace(/\[LIST_POLECONY_IGNORED\](true|false)\[\/LIST_POLECONY_IGNORED\]\n?/g, '');
    note = note.replace(/\[LIST_POLECONY_SENT_DATE\].*?\[\/LIST_POLECONY_SENT_DATE\]\n?/g, '');
    note = note.replace(/\[LIST_POLECONY_IGNORED_DATE\].*?\[\/LIST_POLECONY_IGNORED_DATE\]\n?/g, '');

    if (updates.listPoleconyStatus === null) {
      // Usuń tag jeśli null
      note = note.replace(/\[LIST_POLECONY_STATUS\](sent|ignore)\[\/LIST_POLECONY_STATUS\]\n?/g, '');
    } else {
      if (/\[LIST_POLECONY_STATUS\](sent|ignore)\[\/LIST_POLECONY_STATUS\]/.test(note)) {
        note = note.replace(/\[LIST_POLECONY_STATUS\](sent|ignore)\[\/LIST_POLECONY_STATUS\]/, `[LIST_POLECONY_STATUS]${updates.listPoleconyStatus}[/LIST_POLECONY_STATUS]`);
      } else {
        note = `[LIST_POLECONY_STATUS]${updates.listPoleconyStatus}[/LIST_POLECONY_STATUS]\n${note}`;
      }
    }
  }

  // 2. LIST_POLECONY_STATUS_DATE
  if (updates.listPoleconyStatusDate !== undefined) {
    if (updates.listPoleconyStatusDate === null) {
      // Usuń tag jeśli null
      note = note.replace(/\[LIST_POLECONY_STATUS_DATE\].*?\[\/LIST_POLECONY_STATUS_DATE\]\n?/g, '');
    } else {
      if (/\[LIST_POLECONY_STATUS_DATE\]/.test(note)) {
        note = note.replace(/\[LIST_POLECONY_STATUS_DATE\].*?\[\/LIST_POLECONY_STATUS_DATE\]/, `[LIST_POLECONY_STATUS_DATE]${updates.listPoleconyStatusDate}[/LIST_POLECONY_STATUS_DATE]`);
      } else {
        note = `[LIST_POLECONY_STATUS_DATE]${updates.listPoleconyStatusDate}[/LIST_POLECONY_STATUS_DATE]\n${note}`;
      }
    }
  }

  // Wyczyść podwójne newline'y
  note = note.replace(/\n\n+/g, '\n').trim();

  return note;
}

/**
 * Ustawia status=sent (list polecony został wysłany)
 */
export function setListPoleconyStatusSent(
  internalNote: string | null | undefined,
  sentDate: string
): string {
  return updateInvoiceFlags(internalNote, {
    listPoleconyStatus: 'sent',
    listPoleconyStatusDate: sentDate,
  });
}

/**
 * Ustawia status=ignore (klient zignorowany)
 */
export function setListPoleconyStatusIgnore(
  internalNote: string | null | undefined,
  ignoredDate: string
): string {
  return updateInvoiceFlags(internalNote, {
    listPoleconyStatus: 'ignore',
    listPoleconyStatusDate: ignoredDate,
  });
}

/**
 * Usuwa status (przywraca do stanu początkowego)
 */
export function clearListPoleconyStatus(
  internalNote: string | null | undefined
): string {
  return updateInvoiceFlags(internalNote, {
    listPoleconyStatus: null,
    listPoleconyStatusDate: null,
  });
}
