/**
 * 🔒 PRZYKŁAD BEZPIECZNEGO TESTU
 *
 * Ten plik pokazuje JAK PRAWIDŁOWO pisać testy
 * z zabezpieczeniami przed modyfikacją produkcyjnych danych
 */

import { test, expect } from '@playwright/test';
import {
  testModeGuard,
  TEST_CLIENT_ID,
  assertTestClient,
  assertSafeUrl,
  SAFE_TEST_URLS,
} from '../lib/safe-test-helper';

// ===================================
// ✅ PRZYKŁAD 1: Test strony klienta
// ===================================

test('Testowy klient - strona ładuje się poprawnie', async ({ page }) => {
  // 🔒 ZAWSZE zacznij od safety guard
  testModeGuard('Test strony klienta', TEST_CLIENT_ID);

  // Przejdź na stronę testowego klienta
  const url = SAFE_TEST_URLS.testClient;
  assertSafeUrl(url); // Dodatkowa walidacja

  await page.goto(url);

  // Sprawdź czy strona się załadowała
  await expect(page).toHaveTitle(/Klient/);

  // Sprawdź czy jest tabela faktur
  await expect(page.locator('table')).toBeVisible();

  console.log('✅ Test zakończony - żadne dane nie zostały zmodyfikowane');
});

// ===================================
// ✅ PRZYKŁAD 2: Test dashboard (read-only)
// ===================================

test('Dashboard wyświetla listę klientów', async ({ page }) => {
  testModeGuard('Test dashboard');

  await page.goto(SAFE_TEST_URLS.dashboard);

  // Sprawdź czy jest tabela
  const table = page.locator('table');
  await expect(table).toBeVisible();

  // Policz wiersze (bez modyfikacji danych)
  const rows = await table.locator('tbody tr').count();
  console.log(`📊 Znaleziono ${rows} klientów`);

  expect(rows).toBeGreaterThan(0);
});

// ===================================
// ✅ PRZYKŁAD 3: Test z dodatkową walidacją
// ===================================

test('Historia - sprawdź czy działa filtrowanie', async ({ page }) => {
  testModeGuard('Test historii');

  await page.goto(SAFE_TEST_URLS.historia);

  // Read-only operation - sprawdź czy filtry działają
  const dateFilter = page.locator('input[type="date"]').first();
  await dateFilter.fill('2025-01-01');

  // Poczekaj na przeładowanie
  await page.waitForTimeout(1000);

  // Sprawdź czy są wyniki
  const results = page.locator('tbody tr');
  const count = await results.count();

  console.log(`📅 Wyników dla daty 2025-01-01: ${count}`);
});

// ===================================
// ❌ PRZYKŁAD 4: CO NIE WOLNO ROBIĆ
// ===================================

test.skip('❌ ZŁY PRZYKŁAD - NIE UŻYWAJ!', async ({ page }) => {
  // ❌ Brak safety guard
  // ❌ Hardcoded inny client_id
  const PRODUCTION_CLIENT_ID = 12345678; // ❌ NIEBEZPIECZNE!

  // To rzuci błąd:
  // assertTestClient(PRODUCTION_CLIENT_ID); // 🚨 SECURITY ERROR

  // ❌ Nie testuj wysyłki na produkcyjnych klientach!
  // await page.goto(`/client/${PRODUCTION_CLIENT_ID}`);
  // await page.click('button:has-text("Wyślij SMS")'); // ❌ WYSŁAŁOBY SMS!
});

// ===================================
// ✅ PRZYKŁAD 5: Test API endpoint (read-only)
// ===================================

test('API debug-invoices zwraca dane', async ({ request }) => {
  testModeGuard('Test API debug');

  const response = await request.get(SAFE_TEST_URLS.debugInvoices);

  expect(response.ok()).toBeTruthy();

  const data = await response.json();
  console.log(`📋 Zwrócono ${data.count} faktur dla testowego klienta`);

  expect(data.success).toBe(true);
  expect(data.client_id).toBe(TEST_CLIENT_ID);
});

// ===================================
// 📝 NOTES:
// ===================================

/**
 * ZASADY BEZPIECZEŃSTWA:
 *
 * 1. ✅ ZAWSZE używaj testModeGuard() na początku testu
 * 2. ✅ ZAWSZE używaj TEST_CLIENT_ID zamiast hardcoded ID
 * 3. ✅ ZAWSZE waliduj URL przez assertSafeUrl()
 * 4. ✅ Używaj SAFE_TEST_URLS zamiast pisać URL ręcznie
 * 5. ❌ NIGDY nie testuj wysyłki SMS/Email bez potwierdzenia
 * 6. ❌ NIGDY nie modyfikuj danych innych klientów
 * 7. ❌ NIGDY nie commituj testów które używają production client_id
 *
 * W RAZIE WĄTPLIWOŚCI:
 * - Zapytaj przed uruchomieniem testu
 * - Sprawdź SAFETY_CONFIG.md
 * - Lepiej przesadzić z safeguardami niż za mało!
 */
