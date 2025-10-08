/**
 * 🔒 SAFE TEST HELPER
 * Zapewnia że testy działają TYLKO na testowym kliencie
 */

// ⚠️ WHITELIST - JEDYNY dozwolony klient do testów
export const ALLOWED_TEST_CLIENT_IDS = [
  211779362, // Testowy klient
] as const;

export const TEST_CLIENT_ID = 211779362;

/**
 * Sprawdź czy client_id jest na whiteliście
 */
export function isTestClient(clientId: number): boolean {
  return ALLOWED_TEST_CLIENT_IDS.includes(clientId as any);
}

/**
 * Waliduj client_id - rzuć błąd jeśli nie jest testowy
 */
export function assertTestClient(clientId: number): void {
  if (!isTestClient(clientId)) {
    throw new Error(
      `🚨 SECURITY ERROR: Client ID ${clientId} is NOT allowed for testing!\n` +
      `Only allowed IDs: ${ALLOWED_TEST_CLIENT_IDS.join(', ')}\n` +
      `This is a PRODUCTION CLIENT - tests are FORBIDDEN!`
    );
  }
}

/**
 * Bezpieczny URL dla testów - tylko testowy klient
 */
export function getSafeTestUrl(path: string, clientId?: number): string {
  if (clientId) {
    assertTestClient(clientId);
  }

  // Sprawdź czy URL nie zawiera innego client_id
  const urlClientIdMatch = path.match(/\/client\/(\d+)/);
  if (urlClientIdMatch) {
    const urlClientId = parseInt(urlClientIdMatch[1]);
    assertTestClient(urlClientId);
  }

  return path;
}

/**
 * URLs zabronione do testowania (zawsze rzuć błąd)
 */
const FORBIDDEN_PATHS = [
  '/api/windykacja/auto-send',
  '/api/reminder',
  '/api/sync',
  '/api/list-polecony/generate', // Może wysłać listy polecone!
];

/**
 * Sprawdź czy URL jest bezpieczny
 */
export function isSafeUrl(url: string): boolean {
  // Sprawdź blacklist
  for (const forbidden of FORBIDDEN_PATHS) {
    if (url.includes(forbidden)) {
      return false;
    }
  }

  // Jeśli zawiera client_id, sprawdź czy jest testowy
  const clientIdMatch = url.match(/\/client\/(\d+)/);
  if (clientIdMatch) {
    const clientId = parseInt(clientIdMatch[1]);
    return isTestClient(clientId);
  }

  // Inne URL są OK (read-only)
  return true;
}

/**
 * Waliduj URL przed testem
 */
export function assertSafeUrl(url: string): void {
  if (!isSafeUrl(url)) {
    throw new Error(
      `🚨 SECURITY ERROR: URL "${url}" is NOT safe for testing!\n` +
      `This URL may affect PRODUCTION data.\n` +
      `Tests are only allowed on test client ID: ${TEST_CLIENT_ID}`
    );
  }
}

/**
 * Test mode guard - dodaj do początku każdego testu
 */
export function testModeGuard(testName: string, clientId?: number): void {
  console.log(`\n🔒 [SAFETY CHECK] Test: "${testName}"`);

  if (clientId) {
    console.log(`   Client ID: ${clientId}`);
    assertTestClient(clientId);
    console.log(`   ✅ Client ID is SAFE (test client)`);
  }

  // Sprawdź czy jesteśmy w test environment
  if (process.env.NODE_ENV === 'production') {
    throw new Error(
      `🚨 SECURITY ERROR: Tests CANNOT run in production!\n` +
      `NODE_ENV: ${process.env.NODE_ENV}`
    );
  }

  console.log(`   ✅ Environment is SAFE (not production)\n`);
}

// Export constants
export const SAFE_TEST_URLS = {
  testClient: `/client/${TEST_CLIENT_ID}`,
  dashboard: '/',
  historia: '/historia',
  listPolecony: '/list-polecony',
  debugInvoices: '/api/debug-invoices',
} as const;
