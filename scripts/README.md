# 🔄 Synchronizacja - Skrypty Cron

Ten katalog zawiera skrypty do automatycznej synchronizacji danych z Fakturowni do Supabase.

## 📋 Wymagania

- Skonfigurowany plik `.env.local` z następującymi zmiennymi:
  - `FAKTUROWNIA_API_TOKEN`
  - `FAKTUROWNIA_ACCOUNT`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `CRON_SECRET` (wygeneruj: `openssl rand -base64 32`)
  - `APP_URL` (np. `http://localhost:3000` lub `https://twoja-domena.com`)

## 🚀 Instalacja

### 1. Wygeneruj sekret crona

```bash
openssl rand -base64 32
```

Dodaj wynik do `.env.local`:

```env
CRON_SECRET=twój-wygenerowany-sekret
APP_URL=http://localhost:3000
```

### 2. Zainstaluj cron job

```bash
cd /workspaces/Carebiuro_windykacja
./scripts/setup-cron.sh
```

To zainstaluje zadanie cron, które będzie uruchamiać synchronizację **codziennie o północy (00:00)**.

### 3. Sprawdź zainstalowane zadania

```bash
crontab -l
```

Powinieneś zobaczyć:

```
0 0 * * * /workspaces/Carebiuro_windykacja/scripts/sync-cron.sh
```

## 🔒 Limity API Fakturowni

System przestrzega limitów API Fakturowni:

- ✅ **2 sekundy między requestami** (extra safe, oficjalny limit: 1s)
- ✅ **Maksymalnie 1000 requestów na godzinę** (enforced)
- ✅ **Paginacja**: 100 rekordów na stronę

Jeśli podczas synchronizacji zostanie osiągnięty limit 1000 req/h, system automatycznie wstrzyma się do końca okna godzinowego.

### Strategia synchronizacji:

1. **Wyczyść** wszystkie dane z Supabase
2. **Pobierz** wszystkie **issued invoices** z Fakturowni (`status=issued, period=all`)
3. **Zgrupuj** faktury po `client_id` → wyciągnij unikalne ID klientów
4. **Pobierz** dane klientów **tylko dla unikalnych client_id**
5. **Wstaw** wszystkie dane do Supabase

**🎯 Optymalizacja**: Zamiast pobierać wszystkich klientów (~5000+), pobieramy **tylko tych z issued invoices** (~2000)!

### Przykładowy czas trwania pełnej synchronizacji (delay 2s):

**Szybkość**: 30 requestów/min (60s / 2s delay)

#### ⚠️ WAŻNE: Limit 1000 requestów/godzinę

System **automatycznie zatrzyma się** po osiągnięciu 1000 requestów i wznowi po ~58 minutach.

**Twój przypadek** (6500 faktur + 2500 klientów):

| Etap | Requestów | Czas aktywny | Pauza | Czas total |
|------|-----------|--------------|-------|------------|
| **Faktury** | 65 | ~2 min | - | ~2 min |
| **Klienci batch 1** | 935 | ~31 min | ~27 min | ~58 min |
| **Klienci batch 2** | 935 | ~31 min | ~27 min | ~58 min |
| **Klienci batch 3** | 630 | ~21 min | - | ~21 min |
| **RAZEM** | **2565** | **~85 min** | **~54 min** | **~2h 19min** |

**Podsumowanie**:
- 65 requestów (faktury) + 2500 requestów (klienci) = **2565 requestów total**
- **2 automatyczne pauzy** (po osiągnięciu limitu 1000/h)
- Całkowity czas: **~2h 19min** (w nocy, w tle, zero problemu! 🌙)

**Oszczędność**: Zamiast wszystkich klientów (~5000), pobieramy tylko tych z fakturami (~2500)!

## 📊 Monitorowanie

### Sprawdź logi synchronizacji

```bash
tail -f /var/log/carebiuro-sync.log
```

### Przykładowy log sukcesu:

```
[2025-10-05 00:00:01] Starting nightly sync...
[2025-10-05 00:17:23] Sync completed successfully: {"success":true,"data":{"synced_clients":450,"synced_invoices":1000,"duration_seconds":1041.23}}
```

### Przykładowy log błędu:

```
[2025-10-05 00:00:01] Starting nightly sync...
[2025-10-05 00:00:02] Sync failed with HTTP 401: {"success":false,"error":"Unauthorized"}
```

## 🧪 Testowanie

### Ręczne uruchomienie synchronizacji (bez czekania na północ):

```bash
./scripts/sync-cron.sh
```

### Test bezpośredni przez API:

```bash
curl -X POST http://localhost:3000/api/sync \
  -H "Content-Type: application/json" \
  -H "X-Cron-Secret: twój-sekret-z-env"
```

**⚠️ UWAGA**:
- Bez prawidłowego `X-Cron-Secret` otrzymasz błąd `401 Unauthorized`
- **WAŻNE**: Ten endpoint USUWA wszystkie dane z Supabase i pobiera je na nowo!
- Używaj tylko w testach lub gdy masz pewność, że chcesz pełną synchronizację

## 🛑 Usuwanie crona

Jeśli chcesz wyłączyć automatyczną synchronizację:

```bash
crontab -e
```

Usuń linię z `sync-cron.sh`, zapisz i wyjdź.

Lub usuń wszystkie zadania cron:

```bash
crontab -r
```

## ⚙️ Zmiana harmonogramu

Domyślnie synchronizacja odbywa się **codziennie o północy** (`0 0 * * *`).

Aby zmienić godzinę:

1. Edytuj crontab:

```bash
crontab -e
```

2. Zmień harmonogram (format: `minuta godzina dzień miesiąc dzień_tygodnia`):

```cron
# Codziennie o 3:00 w nocy
0 3 * * * /workspaces/Carebiuro_windykacja/scripts/sync-cron.sh

# Dwa razy dziennie (00:00 i 12:00)
0 0,12 * * * /workspaces/Carebiuro_windykacja/scripts/sync-cron.sh

# Tylko w dni robocze (pn-pt) o 1:00
0 1 * * 1-5 /workspaces/Carebiuro_windykacja/scripts/sync-cron.sh
```

## 🔐 Bezpieczeństwo

### Dlaczego `CRON_SECRET`?

Endpoint `/api/sync` wykonuje kosztowną operację (może trwać nawet godzinę przy dużej liczbie faktur).

Bez zabezpieczenia każdy mógłby wywołać pełną synchronizację, co mogłoby:

- Przeciążyć serwer
- Osiągnąć limity API Fakturowni
- Zablokować dostęp do danych

`CRON_SECRET` zapewnia, że tylko autoryzowane zadanie cron może uruchomić synchronizację.

### Best Practices:

1. ✅ Używaj silnego, losowego sekretu (min. 32 znaki)
2. ✅ Nie commituj `.env.local` do git
3. ✅ Regularnie zmieniaj sekret (np. co 3 miesiące)
4. ✅ Monitoruj logi pod kątem nieautoryzowanych prób dostępu

## 📞 Wsparcie

Jeśli synchronizacja nie działa:

1. Sprawdź logi: `tail -50 /var/log/carebiuro-sync.log`
2. Sprawdź zmienne środowiskowe: `cat .env.local`
3. Uruchom ręcznie: `./scripts/sync-cron.sh`
4. Sprawdź logi aplikacji Next.js

## 🎯 Przydatne komendy

```bash
# Sprawdź czy aplikacja działa
curl http://localhost:3000

# Sprawdź aktywne zadania cron
crontab -l

# Sprawdź ostatnie logi cron
grep CRON /var/log/syslog | tail -20

# Sprawdź logi synchronizacji
tail -20 /var/log/carebiuro-sync.log

# Test rate limitera (nie uruchomi pełnej synchronizacji)
curl -X GET http://localhost:3000/api/sync?type=incremental
```

---

**Aktualizacja**: 2025-10-05
**Wersja**: 1.0
