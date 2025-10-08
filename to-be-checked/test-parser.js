// Test parsera
function updateListPoleconyIgnored(note, ignored) {
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

const testNote = '[WINDYKACJA]false[/WINDYKACJA] [LIST_POLECONY]true[/LIST_POLECONY]';
const result = updateListPoleconyIgnored(testNote, true);

console.log('INPUT:', testNote);
console.log('OUTPUT:', result);
console.log('CONTAINS NEWLINE:', result.includes('\n'));
