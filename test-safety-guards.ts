#!/usr/bin/env node
/**
 * 🔒 MANUAL SAFETY GUARD TESTS
 *
 * Prosty skrypt testujący system bezpieczeństwa.
 * Uruchom: npx tsx test-safety-guards.ts
 */

import {
  isTestClient,
  assertTestClient,
  isSafeUrl,
  assertSafeUrl,
  testModeGuard,
  TEST_CLIENT_ID,
  ALLOWED_TEST_CLIENT_IDS,
} from './lib/safe-test-helper';

let passed = 0;
let failed = 0;

function test(name: string, fn: () => void) {
  try {
    fn();
    console.log(`✅ ${name}`);
    passed++;
  } catch (error) {
    console.error(`❌ ${name}`);
    console.error(`   Error: ${error instanceof Error ? error.message : String(error)}`);
    failed++;
  }
}

function assert(condition: boolean, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function assertThrows(fn: () => void, expectedMessage?: string) {
  try {
    fn();
    throw new Error('Expected function to throw, but it did not');
  } catch (error) {
    if (error instanceof Error && error.message === 'Expected function to throw, but it did not') {
      throw error;
    }
    if (expectedMessage && error instanceof Error) {
      assert(
        error.message.includes(expectedMessage),
        `Expected error message to include "${expectedMessage}", but got: ${error.message}`
      );
    }
  }
}

console.log('\n🔒 TESTING SAFETY GUARD SYSTEM\n');

// Test 1: Client ID Validation
test('Test client 211779362 should be allowed', () => {
  assert(isTestClient(211779362), 'isTestClient(211779362) should return true');
  assertTestClient(211779362); // Should not throw
});

test('Production client IDs should be blocked', () => {
  assert(!isTestClient(123456789), 'isTestClient(123456789) should return false');
  assertThrows(() => assertTestClient(123456789), 'SECURITY ERROR');
});

test('Random client IDs should be blocked', () => {
  assert(!isTestClient(999999999), 'isTestClient(999999999) should return false');
  assertThrows(() => assertTestClient(999999999), 'PRODUCTION CLIENT');
});

// Test 2: URL Validation
test('Safe URLs without client ID should be allowed', () => {
  assert(isSafeUrl('/'), 'Root URL should be safe');
  assert(isSafeUrl('/historia'), '/historia should be safe');
  assert(isSafeUrl('/list-polecony'), '/list-polecony should be safe');
});

test('Test client URL should be allowed', () => {
  assert(isSafeUrl(`/client/${TEST_CLIENT_ID}`), 'Test client URL should be safe');
  assertSafeUrl(`/client/${TEST_CLIENT_ID}`); // Should not throw
});

test('Production client URLs should be blocked', () => {
  assert(!isSafeUrl('/client/123456789'), 'Production client URL should not be safe');
  assertThrows(() => assertSafeUrl('/client/123456789'), 'SECURITY ERROR');
});

test('Dangerous API endpoints should be blocked', () => {
  assert(!isSafeUrl('/api/windykacja/auto-send'), 'auto-send should be blocked');
  assert(!isSafeUrl('/api/reminder'), 'reminder should be blocked');
  assert(!isSafeUrl('/api/sync'), 'sync should be blocked');
  assert(!isSafeUrl('/api/list-polecony/generate'), 'list-polecony/generate should be blocked');
});

// Test 3: Test Mode Guard
test('Test mode guard should pass for test client', () => {
  testModeGuard('Test with test client', TEST_CLIENT_ID); // Should not throw
});

test('Test mode guard should throw for production client', () => {
  assertThrows(() => testModeGuard('Test with production client', 123456789), 'SECURITY ERROR');
});

test('Test mode guard should allow without client ID', () => {
  testModeGuard('General test without client ID'); // Should not throw
});

// Test 4: Constants
test('TEST_CLIENT_ID should be 211779362', () => {
  assert(TEST_CLIENT_ID === 211779362, 'TEST_CLIENT_ID should equal 211779362');
});

test('ALLOWED_TEST_CLIENT_IDS should contain test client', () => {
  assert(
    ALLOWED_TEST_CLIENT_IDS.includes(211779362),
    'ALLOWED_TEST_CLIENT_IDS should include 211779362'
  );
  assert(
    ALLOWED_TEST_CLIENT_IDS.length === 1,
    'ALLOWED_TEST_CLIENT_IDS should have exactly 1 entry'
  );
});

// Summary
console.log('\n' + '='.repeat(50));
console.log(`RESULTS: ${passed} passed, ${failed} failed`);
console.log('='.repeat(50) + '\n');

if (failed > 0) {
  console.error('❌ Some tests failed! Safety system may not be working correctly.');
  process.exit(1);
} else {
  console.log('✅ All tests passed! Safety system is working correctly.');
  console.log('\n🔒 Production data is PROTECTED from accidental modification.');
  console.log(`   Only client ${TEST_CLIENT_ID} can be used for testing.\n`);
  process.exit(0);
}
