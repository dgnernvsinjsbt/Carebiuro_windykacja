# 🔒 SAFETY CONFIGURATION - OCHRONA DANYCH KLIENTÓW

## ⚠️ KRYTYCZNE ZASADY BEZPIECZEŃSTWA

### 🎯 TESTOWY KLIENT (JEDYNY DOZWOLONY DO TESTÓW)

```typescript
// WHITELIST - TYLKO TE KLIENTY MOŻNA TESTOWAĆ
const ALLOWED_TEST_CLIENTS = [
  211779362,  // Testowy klient - używany w development
];

// ❌ NIGDY nie testuj na innych klientach!
// ❌ NIGDY nie używaj Playwright na produkcji bez whitelista!
```

---

## 🚫 CO JEST ZABRONIONE:

1. ❌ **Testy na prawdziwych klientach** (tylko ID: 211779362)
2. ❌ **Automatyczne wysyłki SMS/Email** bez potwierdzenia
3. ❌ **Bulk operations** bez whitelista
4. ❌ **Playwright na /client/[id]** gdzie id !== 211779362
5. ❌ **Modyfikacja faktur** poza testowym klientem

---

## ✅ CO JEST DOZWOLONE:

1. ✅ Read-only operations na wszystkich klientach
2. ✅ Testy E2E na kliencie 211779362
3. ✅ Screenshots (bez modyfikacji danych)
4. ✅ SQL SELECT queries (Supabase read-only)
5. ✅ API GET endpoints

---

## 🛡️ PLAYWRIGHT SAFEGUARDS

### Tylko te URL-e są dozwolone do testowania:

```typescript
const ALLOWED_TEST_URLS = [
  '/client/211779362',           // ✅ Strona testowego klienta
  '/api/debug-invoices',         // ✅ Debug endpoint
  '/api/test-update-client',     // ✅ Test endpoint
  '/api/test-import',            // ✅ Import test
  '/',                           // ✅ Dashboard (read-only)
  '/historia',                   // ✅ Historia (read-only)
  '/list-polecony',              // ✅ List polecony (read-only)
];

const FORBIDDEN_URLS = [
  '/client/*',                   // ❌ Inne klienty
  '/api/windykacja/auto-send',   // ❌ Auto-send
  '/api/reminder',               // ❌ Reminder send
  '/api/sync',                   // ❌ Full sync
];
```

---

## 🔐 SUPABASE MCP - READ-ONLY MODE

Konfiguracja Supabase MCP powinna używać **read-only** connection string:

```bash
# ❌ NIE używaj service role key dla MCP
# ✅ Używaj anon key (read-only) lub custom read-only user

SUPABASE_MCP_URL=https://gbylzdyyhnvmrgfgpfqh.supabase.co
SUPABASE_MCP_KEY=<ANON_KEY>  # Read-only!
```

---

## 📋 CHECKLIST PRZED TESTEM:

Przed uruchomieniem Playwright/testów:

- [ ] Sprawdź czy client_id === 211779362
- [ ] Sprawdź czy URL nie zawiera innego ID klienta
- [ ] Sprawdź czy test nie wysyła SMS/Email
- [ ] Sprawdź czy nie modyfikuje faktury prawdziwego klienta
- [ ] Przeczytaj kod testu i zrozum co robi

---

## 🚨 CO ZROBIĆ W RAZIE BŁĘDU:

Jeśli przypadkowo:

1. **Wysłano SMS/Email do prawdziwego klienta:**
   - Natychmiast sprawdź `message_history` table
   - Wyślij przeprosiny do klienta
   - Dodaj flagę `test_mode` do wszystkich testów

2. **Zmodyfikowano fakturę prawdziwego klienta:**
   - Sprawdź `git log` - ostatnie zmiany
   - Przywróć z backup (Fakturownia ma historię)
   - Sprawdź `comment` field - czy test dodał [FISCAL_SYNC]

3. **Uruchomiono bulk operation:**
   - STOP natychmiast (Ctrl+C)
   - Sprawdź logi
   - Rollback jeśli potrzebne

---

## 💡 JAK BEZPIECZNIE TESTOWAĆ:

### ✅ Dobry przykład (SAFE):

```typescript
// Test tylko na testowym kliencie
test('Wysyłka SMS - testowy klient', async () => {
  const TEST_CLIENT_ID = 211779362;

  await page.goto(`/client/${TEST_CLIENT_ID}`);

  // Sprawdź czy to na pewno testowy klient
  const clientName = await page.textContent('h1');
  expect(clientName).toContain('Test'); // lub inna nazwa testowego klienta

  // Teraz możesz testować
});
```

### ❌ Zły przykład (DANGEROUS):

```typescript
// ❌ Test na wszystkich klientach - NIEBEZPIECZNE!
test('Wysyłka SMS - wszyscy klienci', async () => {
  const clients = await getAllClients(); // ❌

  for (const client of clients) {
    await sendSMS(client.id); // ❌ WYŚLE SMS DO WSZYSTKICH!
  }
});
```

---

## 🎯 TESTOWY KLIENT - PEŁNE INFO:

```
ID: 211779362
Nazwa: [sprawdź w bazie]
Email: [testowy email]
Phone: [testowy numer - nie prawdziwy klient]

Faktury testowe:
- Możesz modyfikować komentarze
- Możesz dodawać [FISCAL_SYNC] flagi
- Możesz testować wysyłkę (jeśli email/SMS są testowe)
```

---

## 🔒 SECURITY RULES:

1. **Zawsze** sprawdzaj client_id przed testem
2. **Nigdy** nie commituj kluczy API do repo
3. **Zawsze** używaj `.env` dla secrets
4. **Nigdy** nie pushujesz `.env` do GitHuba
5. **Zawsze** testuj na staging przed production

---

## 📞 W RAZIE WĄTPLIWOŚCI:

**❓ "Czy mogę uruchomić ten test?"**
- Jeśli test używa client_id === 211779362 → ✅ TAK
- Jeśli test ma hardcoded inny ID → ❌ NIE
- Jeśli test pobiera wszystkich klientów → ❌ NIE (chyba że read-only)

**❓ "Czy mogę użyć Playwright?"**
- Na `/client/211779362` → ✅ TAK
- Na innych `/client/[id]` → ❌ NIE
- Na dashboard (read-only) → ✅ TAK

**❓ "Czy mogę wysłać SMS/Email?"**
- Do testowego klienta (211779362) → ✅ TAK (jeśli numer jest testowy)
- Do innych klientów → ❌ NIE BEZ POTWIERDZENIA

---

## ✅ PODSUMOWANIE:

🎯 **GOLDEN RULE**: Jeśli nie jesteś pewien → NIE URUCHAMIAJ testu!

🔒 **TEST ONLY**: client_id === 211779362

📖 **READ-ONLY**: Wszystkie inne operacje

🚫 **NO AUTO**: Nigdy nie wysyłaj automatycznie do prawdziwych klientów

---

_Last updated: $(date)_
_Maintainer: Bezpieczeństwo > Szybkość testowania_
