/**
 * Test: Czy przyciski zachowują flagę WINDYKACJA na kliencie
 */

import { setListPoleconyStatusSent, setListPoleconyStatusIgnore } from '../lib/invoice-flags';

// Przykładowy note klienta z WINDYKACJA
const clientNote = '[WINDYKACJA]true[/WINDYKACJA] [LIST_POLECONY_STATUS]sent[/LIST_POLECONY_STATUS]';

console.log('Original note:', clientNote);
console.log('Has WINDYKACJA:', clientNote.includes('[WINDYKACJA]true'));
console.log('');

// Test 1: Ignore button
console.log('Test 1: Ignore button (sent → ignore)');
const afterIgnore = setListPoleconyStatusIgnore(clientNote, '2025-10-08');
console.log('After ignore:', afterIgnore);
console.log('Still has WINDYKACJA:', afterIgnore.includes('[WINDYKACJA]true'));
console.log('Has status=ignore:', afterIgnore.includes('[LIST_POLECONY_STATUS]ignore'));
console.log('');

// Test 2: Restore button
console.log('Test 2: Restore button (ignore → sent)');
const afterRestore = setListPoleconyStatusSent(afterIgnore, '2025-09-01');
console.log('After restore:', afterRestore);
console.log('Still has WINDYKACJA:', afterRestore.includes('[WINDYKACJA]true'));
console.log('Has status=sent:', afterRestore.includes('[LIST_POLECONY_STATUS]sent'));
console.log('');

// Test 3: Multiple cycles
console.log('Test 3: Multiple ignore/restore cycles');
let cycleNote = clientNote;
for (let i = 0; i < 3; i++) {
  cycleNote = setListPoleconyStatusIgnore(cycleNote, '2025-10-08');
  cycleNote = setListPoleconyStatusSent(cycleNote, '2025-09-01');
}
console.log('After 3 cycles:', cycleNote);
console.log('Still has WINDYKACJA:', cycleNote.includes('[WINDYKACJA]true'));

if (!afterIgnore.includes('[WINDYKACJA]true') || !afterRestore.includes('[WINDYKACJA]true') || !cycleNote.includes('[WINDYKACJA]true')) {
  console.error('\n❌ FAIL: WINDYKACJA flag was removed!');
  process.exit(1);
} else {
  console.log('\n✅ PASS: WINDYKACJA flag preserved in all tests');
}
