/**
 * 🔒 SAFETY GUARD TESTS
 *
 * Te testy weryfikują, że system bezpieczeństwa działa poprawnie
 * i blokuje dostęp do danych produkcyjnych.
 */

import { describe, it, expect } from '@jest/globals';
import {
  isTestClient,
  assertTestClient,
  isSafeUrl,
  assertSafeUrl,
  testModeGuard,
  TEST_CLIENT_ID,
  ALLOWED_TEST_CLIENT_IDS,
} from '../lib/safe-test-helper';

describe('🔒 Safety Guard System', () => {
  describe('Client ID Validation', () => {
    it('should allow test client 211779362', () => {
      expect(isTestClient(211779362)).toBe(true);
      expect(() => assertTestClient(211779362)).not.toThrow();
    });

    it('should block production client IDs', () => {
      expect(isTestClient(123456789)).toBe(false);
      expect(() => assertTestClient(123456789)).toThrow('SECURITY ERROR');
      expect(() => assertTestClient(123456789)).toThrow('NOT allowed for testing');
    });

    it('should block random client IDs', () => {
      expect(isTestClient(999999999)).toBe(false);
      expect(() => assertTestClient(999999999)).toThrow('PRODUCTION CLIENT');
    });
  });

  describe('URL Validation', () => {
    it('should allow safe URLs without client ID', () => {
      expect(isSafeUrl('/')).toBe(true);
      expect(isSafeUrl('/historia')).toBe(true);
      expect(isSafeUrl('/list-polecony')).toBe(true);
    });

    it('should allow test client URL', () => {
      expect(isSafeUrl(`/client/${TEST_CLIENT_ID}`)).toBe(true);
      expect(() => assertSafeUrl(`/client/${TEST_CLIENT_ID}`)).not.toThrow();
    });

    it('should block production client URLs', () => {
      expect(isSafeUrl('/client/123456789')).toBe(false);
      expect(() => assertSafeUrl('/client/123456789')).toThrow('SECURITY ERROR');
    });

    it('should block dangerous API endpoints', () => {
      expect(isSafeUrl('/api/windykacja/auto-send')).toBe(false);
      expect(isSafeUrl('/api/reminder')).toBe(false);
      expect(isSafeUrl('/api/sync')).toBe(false);
      expect(isSafeUrl('/api/list-polecony/generate')).toBe(false);
    });

    it('should block URLs with production client IDs even in subpaths', () => {
      expect(isSafeUrl('/client/999999/invoices')).toBe(false);
      expect(isSafeUrl('/api/client/888888/sync')).toBe(false);
    });
  });

  describe('Test Mode Guard', () => {
    it('should pass guard for test client', () => {
      expect(() => testModeGuard('Test name', TEST_CLIENT_ID)).not.toThrow();
    });

    it('should throw for production client', () => {
      expect(() => testModeGuard('Test name', 123456789)).toThrow('SECURITY ERROR');
    });

    it('should allow guard without client ID', () => {
      expect(() => testModeGuard('General test')).not.toThrow();
    });

    it('should block in production environment', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'production';

      expect(() => testModeGuard('Test')).toThrow('Tests CANNOT run in production');

      process.env.NODE_ENV = originalEnv;
    });
  });

  describe('Constants Export', () => {
    it('should export correct test client ID', () => {
      expect(TEST_CLIENT_ID).toBe(211779362);
    });

    it('should export allowed client IDs array', () => {
      expect(ALLOWED_TEST_CLIENT_IDS).toContain(211779362);
      expect(ALLOWED_TEST_CLIENT_IDS).toHaveLength(1);
    });
  });
});
