/**
 * Test: Nowy format flag klienta z client-flags-v2
 */

import { setWindykacja, parseClientFlags } from '../lib/client-flags-v2';

// Test 1: Klient z LIST_POLECONY_STATUS (nie powinno się zmienić)
const note1 = '[WINDYKACJA]true[/WINDYKACJA]\n[LIST_POLECONY_STATUS]sent[/LIST_POLECONY_STATUS]\n[LIST_POLECONY_STATUS_DATE]2025-09-01[/LIST_POLECONY_STATUS_DATE]';

console.log('Test 1: Toggle windykacja (true → false)');
console.log('Before:', note1);
const after1 = setWindykacja(note1, false);
console.log('After:', after1);
console.log('Still has LIST_POLECONY_STATUS:', after1.includes('[LIST_POLECONY_STATUS]sent'));
console.log('Still has DATE:', after1.includes('[LIST_POLECONY_STATUS_DATE]2025-09-01'));
console.log('Has windykacja=false:', after1.includes('[WINDYKACJA]false'));
console.log('');

// Test 2: Toggle back
console.log('Test 2: Toggle windykacja (false → true)');
const after2 = setWindykacja(after1, true);
console.log('After:', after2);
console.log('Still has LIST_POLECONY_STATUS:', after2.includes('[LIST_POLECONY_STATUS]sent'));
console.log('Has windykacja=true:', after2.includes('[WINDYKACJA]true'));
console.log('');

// Test 3: Klient ze STARYMI flagami (powinno zmigrować)
const oldNote = '[WINDYKACJA]true[/WINDYKACJA] [LIST_POLECONY]true[/LIST_POLECONY] [LIST_POLECONY_IGNORED]false[/LIST_POLECONY_IGNORED]';
console.log('Test 3: Klient ze starymi flagami');
console.log('Before:', oldNote);
const after3 = setWindykacja(oldNote, false);
console.log('After:', after3);
console.log('Removed old LIST_POLECONY:', !after3.includes('[LIST_POLECONY]'));
console.log('Removed old LIST_POLECONY_IGNORED:', !after3.includes('[LIST_POLECONY_IGNORED]'));
console.log('');

// Test 4: Parser
console.log('Test 4: Parser');
const parsed = parseClientFlags(note1);
console.log('Parsed:', parsed);
console.log('windykacja:', parsed.windykacja);
console.log('listPoleconyStatus:', parsed.listPoleconyStatus);
console.log('listPoleconyStatusDate:', parsed.listPoleconyStatusDate);

if (!after1.includes('[LIST_POLECONY_STATUS]sent') || !after2.includes('[LIST_POLECONY_STATUS]sent')) {
  console.error('\n❌ FAIL: LIST_POLECONY_STATUS was removed!');
  process.exit(1);
}

if (after3.includes('[LIST_POLECONY]') || after3.includes('[LIST_POLECONY_IGNORED]')) {
  console.error('\n❌ FAIL: Old flags were not removed!');
  process.exit(1);
}

console.log('\n✅ PASS: All tests passed');
