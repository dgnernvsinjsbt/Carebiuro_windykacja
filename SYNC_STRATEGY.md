# 🔄 Strategia Synchronizacji - Dokumentacja

## 📋 Przegląd

System synchronizuje dane z Fakturowni do Supabase **codziennie o północy** przez automatyczny cron job.

---

## 🎯 Główne założenia

### Co synchronizujemy?

✅ **Tylko faktury issued** (`status=issued, period=all`)
- Wystawione (nie zapłacone)
- Wszystkie okresy (dziś + 2 miesiące temu)
- **Nie pobieramy**: zapłacone, anulowane, draft

✅ **Tylko klienci z issued invoices**
- Wyciągamy unikalne `client_id` z pobranych faktur
- Pobieramy dane klientów **tylko dla tych ID**
- Oszczędność: ~3000 requestów (zamiast wszystkich klientów)

---

## 🔄 Proces synchronizacji (8 kroków)

### STEP 1: Wyczyść dane
```
DELETE FROM invoices WHERE id != 0
DELETE FROM clients WHERE id != 0
```
**Czas**: ~1 sekunda

### STEP 2: Pobierz issued invoices
```
GET /invoices.json?status=issued&period=all&page=1&per_page=100
GET /invoices.json?status=issued&period=all&page=2&per_page=100
...
GET /invoices.json?status=issued&period=all&page=65&per_page=100
```
**Przykład**: 6500 faktur = 65 stron × 2s = **130 sekund**

### STEP 3: Transformuj faktury
Mapowanie z Fakturownia schema → Supabase schema
**Czas**: ~1 sekunda (w pamięci)

### STEP 4: Wyciągnij unikalne client_id
```javascript
const uniqueClientIds = [...new Set(invoices.map(inv => inv.client_id).filter(Boolean))]
```
**Przykład**: 6500 faktur → ~2000 unikalnych klientów
**Czas**: ~1 sekunda (w pamięci)

### STEP 5: Pobierz dane klientów
```
GET /clients/123.json
GET /clients/456.json
...
(dla każdego unikalnego client_id)
```
**Przykład**: ~2000 klientów × 2s = **~67 sekund**

### STEP 6: Transformuj klientów
Mapowanie z Fakturownia schema → Supabase schema
**Czas**: ~1 sekunda (w pamięci)

### STEP 7: Oblicz total_unpaid
Dla każdego klienta sumujemy wartości jego issued invoices
**Czas**: ~1 sekunda (w pamięci)

### STEP 8: Wstaw do Supabase
```
INSERT INTO clients (bulk upsert)
INSERT INTO invoices (bulk upsert)
```
**Czas**: ~5-10 sekund (zależnie od bazy)

---

## ⏱️ Czasy wykonania

### Scenariusz 1: Mniejsza liczba klientów (~935 lub mniej)

Bez przekroczenia limitu 1000 req/h (65 faktur + 935 klientów = 1000):

| Krok | Operacja | Czas |
|------|----------|------|
| 1 | Clear data | ~1s |
| 2 | Fetch 6500 invoices (65 stron) | **~130s (2.2 min)** |
| 3 | Transform invoices | ~1s |
| 4 | Extract unique client_ids | ~1s |
| 5 | Fetch 935 clients | **~31 min** |
| 6 | Transform clients | ~1s |
| 7 | Calculate totals | ~1s |
| 8 | Insert to Supabase | ~5s |
| **TOTAL** | | **~33 min** |

### Scenariusz 2: Duża liczba klientów (~2500) - TWÓJ PRZYPADEK

**PRZEKROCZENIE LIMITU 1000 req/h** - automatyczne pauzy:

| Krok | Operacja | Requestów | Czas |
|------|----------|-----------|------|
| 1 | Clear data | 0 | ~1s |
| 2 | Fetch 6500 invoices | **65** | **~130s** |
| 3 | Transform invoices | 0 | ~1s |
| 4 | Extract client_ids | 0 | ~1s |
| **5a** | **Fetch 935 clients (batch 1)** | **935** | **~31 min** |
| | **🛑 PAUZA (limit 1000/h)** | | **~27 min** |
| **5b** | **Fetch 935 clients (batch 2)** | **935** | **~31 min** |
| | **🛑 PAUZA (limit 1000/h)** | | **~27 min** |
| **5c** | **Fetch 630 clients (batch 3)** | **630** | **~21 min** |
| 6 | Transform clients | 0 | ~1s |
| 7 | Calculate totals | 0 | ~1s |
| 8 | Insert to Supabase | 0 | ~5s |
| **TOTAL** | | **2565** | **~2h 18min** |

**Breakdown**:
- **65 requestów** (faktury) + **2500 requestów** (klienci) = **2565 requestów**
- **Batch 1**: 1000 req (65 faktur + 935 klientów) → osiąga limit → pauza ~27 min
- **Batch 2**: 935 klientów → osiąga limit → pauza ~27 min
- **Batch 3**: 630 klientów → koniec

**Automatyczne pauzy**: System SAM zatrzyma się i wznowi po godzinie

---

## 🔒 Rate Limiting

### Limity Fakturowni API:
- **1 request per second** (oficjalny limit)
- **1000 requests per hour** (hard limit)

### Nasze ustawienia:
- **2 sekundy między requestami** (extra safe)
- Automatyczna blokada przy osiągnięciu 1000 req/h
- Paginacja: 100 rekordów/stronę

### Szybkość:
- **30 requestów/minutę** (60s / 2s)
- **3000 faktur/minutę** (30 × 100)

---

## 📊 Oszczędności

### Przed optymalizacją:
```
Wszystkie faktury: ~30000+ (300+ stron × 2s) = ~600 sekund
Wszyscy klienci: ~5000 (50 stron × 2s) = ~100 sekund
RAZEM: ~700 sekund (~12 minut)
```

### Po optymalizacji:
```
Issued invoices: 6500 (65 stron × 2s) = ~130 sekund
Tylko klienci z fakturami: ~2000 × 2s = ~67 sekund
RAZEM: ~207 sekund (~3.5 minuty)
```

**Oszczędność**: ~8.5 minuty (~72% szybciej!) 🚀

---

## 🛡️ Bezpieczeństwo

### Endpoint `/api/sync` jest zabezpieczony:

```bash
curl -X POST http://localhost:3000/api/sync \
  -H "X-Cron-Secret: <wartość-z-env>"
```

Bez `X-Cron-Secret` → `401 Unauthorized`

### Konfiguracja (`.env.local`):
```env
CRON_SECRET=<wygeneruj: openssl rand -base64 32>
APP_URL=http://localhost:3000
```

---

## 📅 Harmonogram

### Automatyczny cron:
```cron
0 0 * * * /workspaces/Carebiuro_windykacja/scripts/sync-cron.sh
```

**Kiedy**: Codziennie o **00:00** (północ)

**Instalacja**:
```bash
./scripts/setup-cron.sh
```

---

## 🧪 Testowanie

### Ręczne uruchomienie:
```bash
./scripts/sync-cron.sh
```

### Sprawdź logi:
```bash
tail -f /var/log/carebiuro-sync.log
```

### Przykładowy sukces:
```
[2025-10-05 00:00:01] Starting nightly sync...
[2025-10-05 00:03:28] Sync completed successfully: {"synced_clients":2000,"synced_invoices":6500,"duration_seconds":207}
```

---

## 🔍 Monitoring

### Sprawdź status crona:
```bash
crontab -l
```

### Sprawdź ostatnie logi:
```bash
tail -20 /var/log/carebiuro-sync.log
```

### Sprawdź dane w Supabase:
```sql
SELECT COUNT(*) FROM invoices;  -- Powinno być ~6500
SELECT COUNT(*) FROM clients;   -- Powinno być ~2000
```

---

## ❓ FAQ

### Czy synchronizacja usuwa moje dane?
**Tak** - strategia CLEAR → FETCH → INSERT usuwa wszystkie dane przed synchronizacją. To gwarantuje 100% spójność z Fakturownią.

### Co jeśli synchronizacja się nie powiedzie?
System automatycznie zaloguje błąd w `/var/log/carebiuro-sync.log`. Dane pozostaną puste do następnej udanej synchronizacji.

### Czy mogę uruchomić synchronizację ręcznie?
**Nie przez UI** - przycisk został usunięty celowo (bezpieczeństwo). Możesz uruchomić przez:
```bash
./scripts/sync-cron.sh
```

### Dlaczego tylko issued invoices?
Bo system służy do windykacji - potrzebujemy tylko **nieopłaconych faktur**. Zapłacone/anulowane są zbędne.

### Co jeśli mam więcej faktur?
System automatycznie dostosuje się:
- 10000 faktur → ~5 minut
- 20000 faktur → ~10 minut
- 50000 faktur → ~25 minut

Rate limiter zadba o limity API.

---

**Ostatnia aktualizacja**: 2025-10-05
**Wersja**: 1.1.0
