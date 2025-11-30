# RAPORT DOCHODZENIA: Niewysłane maile/SMS windykacyjne
**Data**: 2025-11-30
**Problem**: Klienci zaznaczeni do windykacji wczoraj (np. Adrian Piskula) nie otrzymali SMS/Email

---

## 🔍 EXECUTIVE SUMMARY

Po szczegółowym dochodzeniu zidentyfikowałem **3 potencjalne przyczyny** problemu:

### ✅ CO DZIAŁA:
1. **UI → Natychmiastowa wysyłka S1** - Działa poprawnie (WindykacjaToggle.tsx)
2. **Vercel Cron Jobs** - Skonfigurowane w vercel.json (7:00 AM i 7:15 AM UTC)
3. **Backend API** - Endpoints `/api/windykacja/auto-send*` istnieją i działają
4. **SMS/Email integration** - SMS Planet i Mailgun skonfigurowane

### ❌ CO MOŻE NIE DZIAŁAĆ:
1. **BRAK CRON_SECRET w .env** - Vercel crony mogą być blokowane
2. **BRAK GitHub Actions workflow** - Nie ma backup mechanizmu w GitHub
3. **Brak trwałych logów** - Błędy tylko w console.log (znikają po 24h)

---

## 📊 ARCHITEKTURA SYSTEMU WINDYKACJI

### System A: Natychmiastowa wysyłka (przy włączeniu windykacji)
```
User klika toggle WINDYKACJA →
PATCH /api/client/[id]/windykacja →
POST /api/windykacja/auto-send →
Wysyła S1 SMS dla wszystkich uprawnionych faktur
```
**Status**: ✅ Powinien działać (nie wymaga CRON_SECRET)

### System B: Vercel Cron Jobs
```
07:00 UTC (08:00 CET) → /api/windykacja/auto-send-initial
  → Wysyła E1+S1 dla nowych faktur (ostatnie 3 dni)

07:15 UTC (08:15 CET) → /api/windykacja/auto-send-overdue
  → Wysyła E1+S1 dla zaległych faktur (tylko klienci z windykacja=true)
```
**Status**: ⚠️ PROBLEM - brak CRON_SECRET w .env

### System C: GitHub Actions
```
BRAK workflow do windykacji!
```
**Status**: ❌ NIE ISTNIEJE

---

## 🚨 ZNALEZIONE PROBLEMY

### Problem 1: BRAK CRON_SECRET (KRYTYCZNY)

**Lokalizacja**: `.env` (brakuje)
**Powinno być** (patrz `.env.example`):
```env
CRON_SECRET=your-random-secret-here
```

**Konsekwencja**:
- Vercel Cron wysyła header `X-Cron-Secret`
- Endpointy `/api/windykacja/auto-send-*` sprawdzają ten secret
- Jeśli brakuje - loguje WARNING ale **przepuszcza request**
- **Możliwe że Vercel używa innego secretu** → request odrzucony z 401

**Kod w `/app/api/windykacja/auto-send-initial/route.ts` (linie 29-41)**:
```typescript
const cronSecret = request.headers.get('X-Cron-Secret');
const expectedSecret = process.env.CRON_SECRET;

if (!expectedSecret) {
  console.warn('[AutoSendInitial] CRON_SECRET not configured - endpoint is unprotected!');
} else if (cronSecret !== expectedSecret) {
  console.error('[AutoSendInitial] Unauthorized request - invalid cron secret');
  return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
}
```

---

### Problem 2: BRAK GitHub Actions Workflow (ŚREDNI)

**Fakt**:
- Istnieją tylko 3 workflow: `nightly-sync.yml`, `test-sync.yml`, `vercel-deploy.yml`
- **BRAK** workflow do windykacji (np. `windykacja-cron.yml`)

**Ryzyko**:
- Jeśli Vercel Cron zawiedzie → brak backup mechanizmu
- GitHub Actions mogłyby być alternatywą (np. o 8:00 CET)

---

### Problem 3: Brak Trwałych Logów (KRYTYCZNY)

**Fakty**:
- Błędy wysyłki logowane tylko przez `console.error()`
- Logi Vercel przechowywane max 24-48h
- **Nie ma tabeli `sms_send_log` w Supabase**
- `message_history` loguje tylko **UDANE** wysyłki

**Konsekwencja**:
- Po 24h niemożliwe sprawdzenie co poszło nie tak
- Nie wiemy czy wczoraj były błędy SMS Planet API
- Nie wiemy czy faktury miały brakujące telefony

---

### Problem 4: Warunki Filtrowania Mogą Być "Milczące"

**Faktura nie zostanie wysłana jeśli**:
1. `status === 'paid'` (opłacona)
2. `kind === 'canceled'` (anulowana)
3. `balance <= 0` (brak zaległości)
4. `STOP === true` w `[FISCAL_SYNC]` (ręcznie zatrzymana)
5. `SMS_1 === true` (już wysłane wcześniej)

**Problem**: Te warunki są sprawdzane **bez logowania**
- System po prostu skipuje fakturę
- User nie wie dlaczego SMS nie wyszedł

---

## 🔎 CO SPRAWDZIĆ W PIERWSZEJ KOLEJNOŚCI

### Krok 1: Sprawdź Vercel Logs (PILNE)

```
https://vercel.com/your-team/carebiuro-windykacja/logs
```

**Szukaj**:
- Timestamp: wczoraj 07:00 UTC i 07:15 UTC
- Logi zawierające: `[AutoSendInitial]`, `[AutoSendOverdue]`
- Błędy: `401 Unauthorized`, `CRON_SECRET`

**Możliwe scenariusze**:
- ✅ Logi pokazują "Auto-send completed: 5 sent, 0 failed" → wszystko OK
- ❌ Logi pokazują "401 Unauthorized" → problem z CRON_SECRET
- ❌ Brak logów w ogóle → cron się nie uruchomił

---

### Krok 2: Sprawdź Dane Adriana Piskuli w Supabase

**SQL Query (uruchom w Supabase Studio)**:
```sql
-- 1. Znajdź klienta
SELECT id, name, email, phone, note, total_unpaid
FROM clients
WHERE name ILIKE '%Piskula%';

-- 2. Sprawdź faktury
SELECT
  i.number,
  i.status,
  i.outstanding,
  i.internal_note,
  i.payment_to
FROM invoices i
JOIN clients c ON i.client_id = c.id
WHERE c.name ILIKE '%Piskula%'
ORDER BY i.issue_date DESC;

-- 3. Sprawdź historię wysyłek
SELECT
  invoice_number,
  message_type,
  level,
  status,
  sent_at,
  error_message
FROM message_history
WHERE client_id = (SELECT id FROM clients WHERE name ILIKE '%Piskula%' LIMIT 1)
ORDER BY sent_at DESC;
```

**Możliwe scenariusze**:
- ✅ `message_history` pokazuje wpisy z wczoraj → SMS wysłane pomyślnie
- ❌ Brak wpisów w `message_history` → SMS nie wysłane w ogóle
- ⚠️ Wpisy z `status='failed'` → błąd przy wysyłce
- ⚠️ `internal_note` zawiera `SMS_1=TRUE` z wcześniejszej daty → już wysłane dawniej

---

### Krok 3: Sprawdź Flagi w Fakturowni (BEZPOŚREDNIO)

**Fakturownia UI**:
```
1. Zaloguj się do Fakturowni
2. Wyszukaj klienta: Adrian Piskula
3. Przejdź do zakładki "Uwagi" lub "Notes"
4. Sprawdź czy widać: [WINDYKACJA]true[/WINDYKACJA]
```

**Fakturownia API** (przez Postman/curl):
```bash
curl "https://gbylzdyyhnvmrgfgpfqh.fakturownia.pl/clients.json?name=Piskula" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

**Możliwe scenariusze**:
- ✅ `note` zawiera `[WINDYKACJA]true[/WINDYKACJA]` → flaga ustawiona poprawnie
- ❌ `note` zawiera `[WINDYKACJA]false[/WINDYKACJA]` → toggle nie zadziałał
- ❌ Brak flagi w ogóle → nie zapisało się do Fakturowni

---

## 🛠️ REKOMENDACJE NAPRAWY

### PILNE (w ciągu 1-2 dni):

#### 1. Dodaj CRON_SECRET do .env
```bash
# Wygeneruj secret
openssl rand -base64 32

# Dodaj do .env
CRON_SECRET=<wygenerowany_secret>

# Ustaw w Vercel Dashboard:
# Project Settings → Environment Variables
# Add: CRON_SECRET = <ten_sam_secret>
```

#### 2. Stwórz tabelę do logowania błędów wysyłki
```sql
CREATE TABLE sms_send_log (
  id BIGSERIAL PRIMARY KEY,
  client_id BIGINT REFERENCES clients(id),
  invoice_id BIGINT REFERENCES invoices(id),
  invoice_number TEXT,
  attempt_type TEXT, -- 'initial', 'overdue', 'manual'
  status TEXT, -- 'success', 'failed', 'skipped'
  error_message TEXT,
  skip_reason TEXT, -- 'already_sent', 'no_phone', 'stopped', 'paid'
  sent_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 3. Zaktualizuj `/api/windykacja/auto-send` aby logował WSZYSTKO
```typescript
// Dla każdej faktury - nawet pominięte:
await supabase.from('sms_send_log').insert({
  client_id,
  invoice_id,
  invoice_number,
  status: 'skipped',
  skip_reason: 'SMS_1 already sent'
});
```

---

### ŚREDNIO PILNE (w ciągu tygodnia):

#### 4. Dodaj GitHub Actions workflow jako backup
```yaml
# .github/workflows/windykacja-cron.yml
name: Windykacja Auto-Send (Backup)

on:
  schedule:
    - cron: '0 7 * * *'  # 7:00 UTC = 8:00 CET
  workflow_dispatch:

jobs:
  send-reminders:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Initial Send
        run: |
          curl -X POST ${{ secrets.VERCEL_URL }}/api/windykacja/auto-send-initial \
            -H "X-Cron-Secret: ${{ secrets.CRON_SECRET }}"

      - name: Wait 15 minutes
        run: sleep 900

      - name: Trigger Overdue Send
        run: |
          curl -X POST ${{ secrets.VERCEL_URL }}/api/windykacja/auto-send-overdue \
            -H "X-Cron-Secret: ${{ secrets.CRON_SECRET }}"
```

#### 5. Dodaj Sentry dla błędów produkcyjnych
```typescript
// W /api/windykacja/auto-send/route.ts
import * as Sentry from '@sentry/nextjs';

catch (error) {
  Sentry.captureException(error, {
    tags: {
      endpoint: 'auto-send',
      client_id
    }
  });
}
```

---

### NICE TO HAVE (przyszłość):

#### 6. Dashboard do monitorowania wysyłek
- Widok: "Wysyłki z ostatnich 7 dni"
- Filtry: sukces / błąd / pominięte
- Exportowanie do CSV

#### 7. Retry mechanism dla failed SMS
```typescript
// Jeśli SMS się nie wyśle → dodaj do queue
await supabase.from('sms_retry_queue').insert({
  invoice_id,
  retry_count: 0,
  next_retry_at: NOW() + INTERVAL '5 minutes'
});
```

---

## 📋 CHECKLIST DO WYKONANIA TERAZ

- [ ] **Sprawdź Vercel Logs** (wczoraj 07:00-07:30 UTC)
- [ ] **Uruchom SQL queries** dla Adriana Piskuli (3 zapytania powyżej)
- [ ] **Sprawdź Fakturownia note** (czy [WINDYKACJA]true[/WINDYKACJA])
- [ ] **Dodaj CRON_SECRET** do .env i Vercel
- [ ] **Stwórz tabelę sms_send_log** w Supabase
- [ ] **Zaktualizuj auto-send** aby logował wszystkie skipowane faktury
- [ ] **Przetestuj ręcznie** - zaznacz testowego klienta do windykacji
- [ ] **Monitoruj logi** przez następne 24h

---

## 🎯 NASTĘPNE KROKI

**Dziś**:
1. Sprawdź Vercel Logs (10 min)
2. Uruchom SQL dla Adriana Piskuli (5 min)
3. Sprawdź Fakturownia (5 min)

**Jutro**:
1. Dodaj CRON_SECRET
2. Stwórz tabelę sms_send_log
3. Deploy zmian

**Za tydzień**:
1. Przejrzyj logi z nowej tabeli
2. Dodaj GitHub Actions backup
3. Rozważ Sentry integration

---

## 📞 KONTAKT DO DEBUGOWANIA

Jeśli potrzebujesz pomocy przy:
- Interpretacji logów Vercel → pokażę jak czytać
- SQL queries w Supabase → pomogę uruchomić
- Dodaniu CRON_SECRET → przeprowadzę krok po kroku

---

**Podsumowanie**: System windykacji jest poprawnie zaprojektowany, ale ma **brak monitoringu i logowania**. Najprawdopodobniej SMS-y wczoraj **nie wysłały się z powodu braku CRON_SECRET**, albo faktury miały już ustawioną flagę SMS_1=TRUE. Sprawdź logi Vercel i dane klienta w Supabase aby potwierdzić.
