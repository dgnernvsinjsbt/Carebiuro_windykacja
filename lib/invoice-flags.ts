/**
 * Funkcje do zarządzania flagami faktur w internal_note
 *
 * Flagi są zapisywane w formacie:
 * [LIST_POLECONY]true[/LIST_POLECONY]
 * [LIST_POLECONY_SENT_DATE]2025-09-01[/LIST_POLECONY_SENT_DATE]
 * [LIST_POLECONY_IGNORED]true[/LIST_POLECONY_IGNORED]
 * [LIST_POLECONY_IGNORED_DATE]2025-09-01[/LIST_POLECONY_IGNORED_DATE]
 */

export interface InvoiceFlags {
  listPolecony: boolean;
  listPoleconySentDate: string | null;
  listPoleconyIgnored: boolean;
  listPoleconyIgnoredDate: string | null;
}

/**
 * Parsuje flagi z internal_note faktury
 */
export function parseInvoiceFlags(internalNote: string | null | undefined): InvoiceFlags {
  const note = internalNote || '';

  // Parsuj flagę LIST_POLECONY (czytaj rzeczywistą wartość true/false)
  const listPoleconyMatch = note.match(/\[LIST_POLECONY\](true|false)\[\/LIST_POLECONY\]/);
  const listPolecony = listPoleconyMatch ? listPoleconyMatch[1] === 'true' : false;

  // Parsuj datę wysłania
  const sentDateMatch = note.match(/\[LIST_POLECONY_SENT_DATE\](.*?)\[\/LIST_POLECONY_SENT_DATE\]/);
  const listPoleconySentDate = sentDateMatch && sentDateMatch[1] ? sentDateMatch[1] : null;

  // Parsuj flagę IGNORED (czytaj rzeczywistą wartość true/false)
  const listPoleconyIgnoredMatch = note.match(/\[LIST_POLECONY_IGNORED\](true|false)\[\/LIST_POLECONY_IGNORED\]/);
  const listPoleconyIgnored = listPoleconyIgnoredMatch ? listPoleconyIgnoredMatch[1] === 'true' : false;

  // Parsuj datę ignorowania
  const ignoredDateMatch = note.match(/\[LIST_POLECONY_IGNORED_DATE\](.*?)\[\/LIST_POLECONY_IGNORED_DATE\]/);
  const listPoleconyIgnoredDate = ignoredDateMatch && ignoredDateMatch[1] ? ignoredDateMatch[1] : null;

  return {
    listPolecony,
    listPoleconySentDate,
    listPoleconyIgnored,
    listPoleconyIgnoredDate,
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

  // Aktualizuj TYLKO przekazane flagi, nie dotykaj innych!

  // 1. LIST_POLECONY
  if (updates.listPolecony !== undefined) {
    if (/\[LIST_POLECONY\](true|false)\[\/LIST_POLECONY\]/.test(note)) {
      note = note.replace(/\[LIST_POLECONY\](true|false)\[\/LIST_POLECONY\]/, `[LIST_POLECONY]${updates.listPolecony}[/LIST_POLECONY]`);
    } else {
      note = `[LIST_POLECONY]${updates.listPolecony}[/LIST_POLECONY]\n${note}`;
    }
  }

  // 2. LIST_POLECONY_SENT_DATE
  if (updates.listPoleconySentDate !== undefined) {
    if (updates.listPoleconySentDate === null) {
      // Usuń tag jeśli null
      note = note.replace(/\[LIST_POLECONY_SENT_DATE\].*?\[\/LIST_POLECONY_SENT_DATE\]\n?/g, '');
    } else {
      if (/\[LIST_POLECONY_SENT_DATE\]/.test(note)) {
        note = note.replace(/\[LIST_POLECONY_SENT_DATE\].*?\[\/LIST_POLECONY_SENT_DATE\]/, `[LIST_POLECONY_SENT_DATE]${updates.listPoleconySentDate}[/LIST_POLECONY_SENT_DATE]`);
      } else {
        note = `[LIST_POLECONY_SENT_DATE]${updates.listPoleconySentDate}[/LIST_POLECONY_SENT_DATE]\n${note}`;
      }
    }
  }

  // 3. LIST_POLECONY_IGNORED
  if (updates.listPoleconyIgnored !== undefined) {
    if (/\[LIST_POLECONY_IGNORED\](true|false)\[\/LIST_POLECONY_IGNORED\]/.test(note)) {
      note = note.replace(/\[LIST_POLECONY_IGNORED\](true|false)\[\/LIST_POLECONY_IGNORED\]/, `[LIST_POLECONY_IGNORED]${updates.listPoleconyIgnored}[/LIST_POLECONY_IGNORED]`);
    } else {
      note = `[LIST_POLECONY_IGNORED]${updates.listPoleconyIgnored}[/LIST_POLECONY_IGNORED]\n${note}`;
    }
  }

  // 4. LIST_POLECONY_IGNORED_DATE
  if (updates.listPoleconyIgnoredDate !== undefined) {
    if (updates.listPoleconyIgnoredDate === null) {
      // Usuń tag jeśli null
      note = note.replace(/\[LIST_POLECONY_IGNORED_DATE\].*?\[\/LIST_POLECONY_IGNORED_DATE\]\n?/g, '');
    } else {
      if (/\[LIST_POLECONY_IGNORED_DATE\]/.test(note)) {
        note = note.replace(/\[LIST_POLECONY_IGNORED_DATE\].*?\[\/LIST_POLECONY_IGNORED_DATE\]/, `[LIST_POLECONY_IGNORED_DATE]${updates.listPoleconyIgnoredDate}[/LIST_POLECONY_IGNORED_DATE]`);
      } else {
        note = `[LIST_POLECONY_IGNORED_DATE]${updates.listPoleconyIgnoredDate}[/LIST_POLECONY_IGNORED_DATE]\n${note}`;
      }
    }
  }

  // Wyczyść podwójne newline'y
  note = note.replace(/\n\n+/g, '\n').trim();

  return note;
}

/**
 * Ustawia flagę LIST_POLECONY i datę wysłania
 */
export function setListPoleconyOnInvoice(
  internalNote: string | null | undefined,
  sentDate: string
): string {
  return updateInvoiceFlags(internalNote, {
    listPolecony: true,
    listPoleconySentDate: sentDate,
  });
}

/**
 * Ustawia flagę LIST_POLECONY_IGNORED i datę ignorowania
 */
export function setListPoleconyIgnoredOnInvoice(
  internalNote: string | null | undefined,
  ignoredDate: string
): string {
  return updateInvoiceFlags(internalNote, {
    listPoleconyIgnored: true,
    listPoleconyIgnoredDate: ignoredDate,
  });
}

/**
 * Ustawia flagę IGNORED na false (przywraca fakturę)
 */
export function setListPoleconyIgnoredToFalse(
  internalNote: string | null | undefined
): string {
  return updateInvoiceFlags(internalNote, {
    listPoleconyIgnored: false,
    listPoleconyIgnoredDate: null,
  });
}

/**
 * @deprecated Użyj setListPoleconyIgnoredToFalse() - nazwa jest bardziej jasna
 */
export function removeListPoleconyIgnoredFromInvoice(
  internalNote: string | null | undefined
): string {
  return setListPoleconyIgnoredToFalse(internalNote);
}
