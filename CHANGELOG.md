# Changelog - Carebiuro Windykacja

## [1.3.0] - 2025-10-07

### 📊 Nowa zakładka: Historia wysyłek

#### Kompletna historia wszystkich wiadomości

**Nowa zakładka "Historia"** między "Klienci" a "List Polecony".

**Funkcje**:
- ✅ Wszystkie wysłane wiadomości (Email, SMS, WhatsApp) w jednym miejscu
- ✅ Inteligentne grupowanie: Data → Klient → Faktura → Wiadomości
- ✅ Kompaktowy widok (Klient X, 2 faktury, 6 wiadomości)
- ✅ Statystyki na żywo (total, email, sms, whatsapp)
- ✅ Filtry: zakres dat, typ wiadomości
- ✅ Status: ✓ Sukces, ✗ Błąd
- ✅ Emoji 🤖 dla automatycznych wysyłek (E1/S1/W1 o 8:00)
- ✅ Czas wysyłki przy każdej wiadomości

**Przykład widoku**:
```
┌─ 07.10.2025 ────────────────────── 24 wiadomości ─┐
│  👤 Klient X                  2 faktury • 6 wiadomości│
│      📄 FV/2025/001  130 EUR                         │
│      [E1 ✓ 08:00 🤖] [S1 ✓ 08:00 🤖] [W1 ✓ 08:00 🤖]│
│                                                       │
│      📄 FV/2025/002  65 EUR                          │
│      [E1 ✓ 08:01 🤖] [S1 ✓ 08:01 🤖] [W1 ✓ 08:01 🤖]│
└───────────────────────────────────────────────────────┘
```

#### Nowe pliki

**Baza danych**:
- Tabela `message_history` w [`supabase-schema.sql`](supabase-schema.sql)
- Indeksy dla wydajności

**Backend**:
- [`lib/supabase.ts`](lib/supabase.ts) - funkcje `messageHistoryDb.*`
- [`app/api/historia/route.ts`](app/api/historia/route.ts) - endpoint GET
- [`app/api/historia/stats/route.ts`](app/api/historia/stats/route.ts) - statystyki
- [`app/api/reminder/route.ts`](app/api/reminder/route.ts) - zaktualizowany (loguje wiadomości)

**Frontend**:
- [`app/historia/page.tsx`](app/historia/page.tsx) - strona Historia
- [`components/Sidebar.tsx`](components/Sidebar.tsx) - dodano link "Historia"

**Dokumentacja**:
- [`HISTORIA_WYSILEK.md`](HISTORIA_WYSILEK.md) - pełna dokumentacja

#### API Endpoints

**`GET /api/historia`**
- Pobiera historię wiadomości
- Filtry: `startDate`, `endDate`, `clientId`, `messageType`, `limit`
- Zwraca dane zgrupowane: Data → Klient → Faktury

**`GET /api/historia/stats`**
- Statystyki wysyłek
- Filtry: `startDate`, `endDate`, `days`
- Zwraca: total, sent, failed, byType, byLevel, daily

#### Struktura tabeli `message_history`

```sql
CREATE TABLE message_history (
  id BIGINT PRIMARY KEY,
  client_id BIGINT REFERENCES clients(id),
  invoice_id BIGINT REFERENCES invoices(id),
  invoice_number TEXT NOT NULL,
  client_name TEXT NOT NULL,

  message_type TEXT ('email' | 'sms' | 'whatsapp'),
  level INTEGER (1 | 2 | 3),

  status TEXT ('sent' | 'failed'),
  error_message TEXT,

  sent_at TIMESTAMP DEFAULT now(),
  sent_by TEXT DEFAULT 'system',
  is_auto_initial BOOLEAN DEFAULT false,

  invoice_total NUMERIC,
  invoice_currency TEXT
);
```

#### Automatyczne logowanie

Wszystkie wiadomości są automatycznie logowane:
- ✅ Endpoint `/api/reminder` (ręczne + auto)
- ✅ Auto-send E1/S1/W1 o 8:00
- ✅ Auto-send windykacja

#### Use Cases

1. **Sprawdzenie automatycznych wysyłek**
   - "Czy dzisiaj o 8:00 wysłały się E1/S1/W1?"
   - Zobacz wiadomości z 🤖 i ~08:00

2. **Historia klienta**
   - "Co wysłaliśmy do Klienta X w ostatnim miesiącu?"
   - Filtr daty + rozwiń sekcję klienta

3. **Identyfikacja błędów**
   - "Które SMS-y się nie wysłały?"
   - Filtr: SMS → szukaj czerwonych ✗

4. **Statystyki miesięczne**
   - "Ile wiadomości wysłaliśmy w październiku?"
   - Filtr daty → karty statystyk na górze

#### UI/UX

**Kolory badge'ów**:
- Email: 💜 Fioletowy
- SMS: 💚 Zielony
- WhatsApp: 💚 Ciemnozielony
- Błąd: 🔴 Czerwony

**Ikony**:
- ✓ Wysłane
- ✗ Błąd
- 🤖 Automatyczne
- 📧 Email
- 📱 SMS
- 💬 WhatsApp

**Nawigacja**:
```
Klienci        (/)
Historia       (/historia)  ← NOWA
List Polecony  (/list-polecony)
Kaczmarski     (/kaczmarski)
```

---

## [1.2.0] - 2025-10-07

### 🤖 Automatyczne wysyłanie wiadomości informacyjnych (E1/S1/W1)

#### Nowa funkcja: Auto-send dla nowo wystawionych faktur

**Wiadomości informacyjne** o wystawieniu faktury (E1, S1, W1) są teraz wysyłane **automatycznie o 8:00 rano**.

**Kluczowe cechy**:
- ✅ **Ignorują** flagę `STOP` (faktura)
- ✅ **Ignorują** flagę `WINDYKACJA` (klient)
- ✅ Tylko dla faktur wystawionych **w ostatnich 3 dniach**
- ✅ Nie wysyłają się ponownie (sprawdzają `E1/S1/W1` w `[FISCAL_SYNC]`)

**Nowe pliki**:
- `app/api/windykacja/auto-send-initial/route.ts` - endpoint automatycznego wysyłania
- `scripts/test-auto-send-initial.ts` - skrypt testowy
- `CRON_AUTO_SEND.md` - pełna dokumentacja
- `vercel.json` - konfiguracja crona dla Vercel

#### Różnica: wiadomości informacyjne vs windykacyjne

| Typ | E1/S1/W1 (informacyjne) | E2/S2/W2, E3/S3/W3 (windykacja) |
|-----|-------------------------|----------------------------------|
| **Cel** | Informacja o wystawieniu faktury | Przypomnienie o płatności |
| **Warunek STOP** | ❌ Ignoruje | ✅ Respektuje |
| **Warunek WINDYKACJA** | ❌ Ignoruje | ✅ Respektuje |
| **Kiedy** | Auto o 8:00 (ostatnie 3 dni) | Ręcznie lub auto (windykacja) |
| **Endpoint** | `/api/windykacja/auto-send-initial` | `/api/windykacja/auto-send` |

#### Harmonogram cron

**Vercel Cron Jobs** (rekomendowane):
```json
{
  "crons": [
    {
      "path": "/api/windykacja/auto-send-initial",
      "schedule": "0 8 * * *"
    }
  ]
}
```

**GitHub Actions**:
```yaml
on:
  schedule:
    - cron: '0 7 * * *'  # 8:00 CET (7:00 UTC)
```

**n8n Workflow**:
- Schedule Trigger: `0 8 * * *`
- HTTP Request: POST `/api/windykacja/auto-send-initial`

#### Testowanie

**Ręcznie przez API**:
```bash
curl -X POST http://localhost:3000/api/windykacja/auto-send-initial
```

**Przez skrypt testowy**:
```bash
npx ts-node scripts/test-auto-send-initial.ts
```

#### Response API

```json
{
  "success": true,
  "message": "Auto-send completed: 15 messages sent, 2 failed",
  "sent": {
    "email": 5,
    "sms": 7,
    "whatsapp": 3,
    "total": 15
  },
  "failed": 2,
  "results": [
    {
      "invoice_id": 12345,
      "invoice_number": "FV/2025/001",
      "sent": ["E1", "S1"],
      "failed": [{ "type": "W1", "error": "No WhatsApp number" }]
    }
  ]
}
```

#### Logi

```
[AutoSendInitial] Starting auto-send for E1/S1/W1...
[AutoSendInitial] Found 12 eligible invoices out of 234
[AutoSendInitial] ✓ E1 sent for invoice 12345
[AutoSendInitial] ✓ S1 sent for invoice 12345
[AutoSendInitial] Completed: 24 total sent (E1: 8, S1: 10, W1: 6), 3 failed
```

#### Dokumentacja

- ✅ `CRON_AUTO_SEND.md` - kompletna instrukcja konfiguracji
- ✅ `vercel.json` - gotowa konfiguracja crona
- ✅ `scripts/test-auto-send-initial.ts` - skrypt testowy

### 📊 Monitorowanie

**Zalecenia**:
1. Sprawdzaj logi przez pierwsze 7 dni
2. Monitoruj limity API (SMS Planet: 1000 req/h)
3. Upewnij się, że wiadomości idą poprawnie

---

## [1.1.0] - 2025-10-05

### 🔒 Bezpieczeństwo

#### Usunięto przycisk pełnej synchronizacji z UI
- ❌ Usunięto `components/SyncButton.tsx`
- ✅ Pełna synchronizacja możliwa **tylko przez cron** (o północy)
- ✅ Endpoint `/api/sync` zabezpieczony przez `X-Cron-Secret`

**Powód**: Przypadkowe uruchomienie pełnej synchronizacji mogło:
- Przeciążyć API Fakturowni (limity: 1000 req/h)
- Zablokować system na dziesiątki minut
- Usunąć i ponownie załadować wszystkie dane

### 🔄 Zmiana strategii synchronizacji

#### Nowa strategia: CLEAR → FETCH → INSERT

**Poprzednio** (UPSERT + CLEANUP):
1. Pobierz dane z Fakturowni
2. Aktualizuj istniejące rekordy (upsert)
3. Usuń rekordy, których nie ma w Fakturowni

**Teraz** (CLEAR → FETCH ISSUED → GROUP → FETCH CLIENTS → INSERT):
1. **Usuń wszystkie** dane z Supabase
2. **Pobierz tylko issued invoices** (`status=issued, period=all`)
3. **Zgrupuj faktury po `client_id`** → wyciągnij unikalne ID
4. **Pobierz tylko klientów z unikalnych `client_id`** (oszczędność ~3000 requestów!)
5. **Wstaw wszystkie** dane do Supabase

**Zalety**:
- Gwarantowana spójność (brak starych rekordów)
- **Tylko potrzebne dane** (issued invoices, nie zapłacone/anulowane)
- **Mniej requestów** (tylko klienci z fakturami, nie wszyscy)
- Prostszy kod (brak skomplikowanej logiki cleanup)
- Lepsze dla nocnej pełnej synchronizacji

### ⏱️ Rate Limiting

#### Zwiększono delay między requestami

| Parametr | Poprzednio | Teraz |
|----------|-----------|-------|
| Delay między requestami | 1.2s | **2s** (extra safe) |
| Paginacja | 100/page | **100/page** |
| Limit godzinowy | 1000 req/h | **1000 req/h** |
| Filtr faktur | wszystkie | **tylko issued** |

**Szybkość**: 30 requestów/min × 100 faktur = **3000 faktur/minutę**

**Przykładowy czas synchronizacji** (2s delay):
- 100 faktur → ~2 sekundy
- 500 faktur → ~10 sekund
- 1000 faktur → ~20 sekund
- **6500 faktur (issued)** → **~2 minuty 10 sekund** ⚡
- 10000 faktur → ~3 minuty 20 sekund

### 🤖 Automatyzacja Cron

#### Dodano skrypty automatycznej synchronizacji

**Nowe pliki**:
- `scripts/sync-cron.sh` - wykonuje synchronizację
- `scripts/setup-cron.sh` - instaluje zadanie cron
- `scripts/README.md` - pełna dokumentacja

**Harmonogram**: Codziennie o **00:00** (północ)

**Instalacja**:
```bash
./scripts/setup-cron.sh
```

### 🔐 Bezpieczeństwo API

#### Endpoint `/api/sync` zabezpieczony

**Wymaga nagłówka**:
```
X-Cron-Secret: <wartość z .env.local>
```

**Bez sekretu**: `401 Unauthorized`

**Konfiguracja** (`.env.local`):
```env
CRON_SECRET=<wygeneruj: openssl rand -base64 32>
APP_URL=http://localhost:3000
```

### 📊 Nowe funkcje Supabase

#### Dodano metody `deleteAll()`

**`clientsDb.deleteAll()`**
- Usuwa wszystkich klientów z bazy

**`invoicesDb.deleteAll()`**
- Usuwa wszystkie faktury z bazy

**Użycie**: Tylko podczas pełnej synchronizacji

### 📝 Dokumentacja

#### Zaktualizowano

- ✅ `scripts/README.md` - instrukcja crona
- ✅ `.env.example` - nowe zmienne (`CRON_SECRET`, `APP_URL`)
- ✅ `CHANGELOG.md` - ten plik

### ⚠️ Breaking Changes

#### Usunięto komponent `SyncButton`

Jeśli Twój kod importował `SyncButton`, usuń te importy.

**Poprzednio**:
```tsx
import SyncButton from '@/components/SyncButton';
```

**Teraz**:
❌ Komponent nie istnieje - użyj crona

#### Zmieniono działanie `/api/sync`

**Poprzednio**: Upsert + cleanup
**Teraz**: **USUWA wszystkie dane**, następnie pobiera na nowo

⚠️ **NIE WYWOŁUJ** tego endpointa ręcznie, chyba że chcesz pełnej synchronizacji!

### 🧪 Testowanie

#### Test ręczny (z poziomu crona)

```bash
./scripts/sync-cron.sh
```

#### Test przez API (wymaga CRON_SECRET)

```bash
curl -X POST http://localhost:3000/api/sync \
  -H "X-Cron-Secret: twój-sekret"
```

#### Sprawdź logi

```bash
tail -f /var/log/carebiuro-sync.log
```

### 🎯 Następne kroki

- [ ] Dodać powiadomienia o błędach synchronizacji (email/Slack)
- [ ] Monitorować logi przez pierwsze 7 dni
- [ ] Rozważyć backup przed `deleteAll()` (opcjonalnie)

---

## [1.0.0] - 2025-10-04

### Początkowa wersja

- Synchronizacja z Fakturowni
- Tabele: `clients`, `invoices`, `invoice_comments`
- UI do zarządzania klientami i fakturami
- Integracja z n8n (webhooks)

---

**Legenda**:
- 🔒 Bezpieczeństwo
- 🔄 Synchronizacja
- ⏱️ Performance
- 🤖 Automatyzacja
- 📊 Funkcjonalności
- 📝 Dokumentacja
- ⚠️ Breaking Changes
- 🧪 Testowanie
