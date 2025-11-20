# 📧 Automatyczna windykacja - E1 + S1 dla przeterminowanych faktur

## ✅ Co zostało zaimplementowane

### 1. Endpoint API
**Plik**: [`app/api/windykacja/auto-send-overdue/route.ts`](app/api/windykacja/auto-send-overdue/route.ts)

**Funkcja**: Automatycznie wysyła **E1 + S1** dla wszystkich **przeterminowanych faktur** klientów z włączoną windykacją.

**Harmonogram**: Codziennie o **8:15 rano** (via Vercel cron)

---

## 🎯 Jak to działa

### Logika działania (codziennie o 8:15 AM):

```
1. Pobierz wszystkich klientów z Supabase
2. Filtruj klientów z [WINDYKACJA]true[/WINDYKACJA] w polu "note"
3. Dla każdego klienta z windykacją:
   a. Pobierz wszystkie faktury z Fakturowni
   b. Filtruj faktury spełniające warunki:
      ✅ Status ≠ 'paid'
      ✅ Kind ≠ 'canceled'
      ✅ Saldo > 0 (total - paid > 0)
      ✅ payment_to < dzisiaj (PRZETERMINOWANA!)
      ✅ STOP = false (poziom faktury)
      ✅ E1/S1 jeszcze nie wysłane
4. Dla każdej przeterminowanej faktury:
   - Wyślij E1 (email) jeśli EMAIL_1 = false
   - Wyślij S1 (SMS) jeśli SMS_1 = false
5. Zaktualizuj [FISCAL_SYNC] w Fakturowni
6. Zwróć raport
```

---

## 📊 Warunki wysyłki

| Warunek | Opis |
|---------|------|
| **Klient windykacja** | `[WINDYKACJA]true[/WINDYKACJA]` w `clients.note` |
| **Status faktury** | Nie opłacona (`status != 'paid'`) |
| **Rodzaj faktury** | Nie anulowana (`kind != 'canceled'`) |
| **Saldo** | Nieopłacone (`total - paid > 0`) |
| **Termin płatności** | **Przeterminowana** (`payment_to < dzisiaj`) |
| **Flaga STOP** | **Wyłączona** (`STOP = false` w `[FISCAL_SYNC]`) |
| **E1/S1 wysłane** | **Nie** (`EMAIL_1 = false`, `SMS_1 = false`) |

---

## 🔄 Konfiguracja Cron

**Plik**: [`vercel.json`](vercel.json)

```json
{
  "crons": [
    {
      "path": "/api/windykacja/auto-send-initial",
      "schedule": "0 8 * * *",
      "description": "Send E1/S1/W1 for newly issued invoices (last 3 days)"
    },
    {
      "path": "/api/windykacja/auto-send-overdue",
      "schedule": "15 8 * * *",
      "description": "Send E1/S1 for overdue invoices (clients with windykacja enabled)"
    },
    {
      "path": "/api/sync",
      "schedule": "0 0 * * *",
      "description": "Daily Fakturownia sync at midnight"
    }
  ]
}
```

**Harmonogram**:
- **8:00 AM** → Wiadomości informacyjne (E1/S1/W1) dla nowych faktur (ostatnie 3 dni)
- **8:15 AM** → **Windykacja** (E1/S1) dla przeterminowanych faktur
- **12:00 AM** → Synchronizacja z Fakturownią

---

## 🧪 Testowanie

### 1. Włącz windykację dla klienta testowego

```bash
node scripts/enable-windykacja-test-client.mjs
```

To ustawi `[WINDYKACJA]true[/WINDYKACJA]` w polu `note` klienta "test" w Fakturowni i Supabase.

### 2. Sprawdź uprawnienia faktury

```bash
node check-invoice.mjs
```

To pokaże czy faktura **FP2025/10/000851** jest uprawniona do wysyłki S1:

```
✅ ELIGIBLE for auto-send S1

🎯 Auto-send eligibility:
✓ Not paid: ✅ (issued)
✓ Has unpaid balance: ✅ (66 PLN)
✓ Overdue: ✅ (9 days)
✓ STOP disabled: ✅ (STOP=false)
✓ SMS_1 not sent: ✅ (SMS_1=false)
✓ Client windykacja: ✅
```

### 3. Testuj endpoint ręcznie

```bash
npx tsx scripts/test-auto-send-overdue.ts
```

Lub przez curl:

```bash
curl -X POST http://localhost:3000/api/windykacja/auto-send-overdue
```

### Spodziewany output:

```json
{
  "success": true,
  "message": "Daily windykacja completed: 24 messages sent, 0 failed",
  "sent": {
    "email": 12,
    "sms": 12,
    "total": 24
  },
  "failed": 0,
  "clients_processed": 3,
  "results": [
    {
      "client_id": 211779362,
      "client_name": "test",
      "invoice_id": 424634325,
      "invoice_number": "FP2025/10/000851",
      "email_sent": true,
      "sms_sent": true
    }
  ]
}
```

---

## 📝 Jak włączyć/wyłączyć windykację dla klienta

### Przez UI (aplikacja Next.js):

1. Otwórz listę klientów
2. Znajdź klienta
3. Kliknij **zielony przełącznik "Windykacja aktywna"**
4. System automatycznie:
   - Zaktualizuje `[WINDYKACJA]true/false[/WINDYKACJA]` w polu `note` w Fakturowni
   - Zsynchronizuje zmianę z Supabase
   - Wyśle S1 do wszystkich uprawnionych faktur (jeśli włączono windykację)

### Przez API:

```bash
curl -X PATCH http://localhost:3000/api/client/211779362/windykacja \
  -H "Content-Type: application/json" \
  -d '{"windykacja_enabled": true}'
```

### Ręcznie w Fakturowni:

1. Otwórz klienta w Fakturowni
2. Edytuj pole **"Komentarz"** (note)
3. Dodaj na początku: `[WINDYKACJA]true[/WINDYKACJA]`
4. Zapisz
5. Uruchom sync: `POST /api/sync/client` z `client_id`

---

## 🔧 Monitorowanie

### Logi w konsoli (Vercel):

```
[AutoSendOverdue] Starting daily windykacja run...
[AutoSendOverdue] Found 3 clients with windykacja enabled (out of 150 total)
[AutoSendOverdue] Processing client: test (ID: 211779362)
[AutoSendOverdue] Found 12 total invoices for client 211779362
[AutoSendOverdue] Found 4 overdue invoices for client 211779362
[AutoSendOverdue] Sending E1 for invoice 424634325 (FP2025/10/000851)
[AutoSendOverdue] ✓ E1 sent for invoice 424634325
[AutoSendOverdue] Sending S1 for invoice 424634325 (FP2025/10/000851)
[AutoSendOverdue] ✓ S1 sent for invoice 424634325
[AutoSendOverdue] Completed: 24 total sent (E1: 12, S1: 12), 0 failed
```

### Co sprawdzać:

1. **Pierwsze 7 dni**: Monitoruj logi codziennie w Vercel Dashboard → Cron Jobs
2. **Limity API**:
   - SMS Planet: 1000 req/h
   - Fakturownia: 1000 req/h
3. **Błędy**: Brak numerów telefonu, błędne adresy email

---

## ⚙️ Zmienne środowiskowe (.env)

```bash
# Fakturownia API
FAKTUROWNIA_API_TOKEN=<twoj-token>
FAKTUROWNIA_ACCOUNT=<twoje-konto>

# SMS Planet API (dla S1)
SMSPLANET_API_TOKEN=<twoj-token>
SMSPLANET_FROM=Cbb-Office

# n8n webhooks (dla E1)
N8N_WEBHOOK_EMAIL=https://n8n.twoja-domena.pl/webhook/email

# Supabase
NEXT_PUBLIC_SUPABASE_URL=<url>
NEXT_PUBLIC_SUPABASE_ANON_KEY=<key>
```

---

## ⚠️ Różnice: Windykacja vs Wiadomości informacyjne

| Cecha | Windykacja (E1/S1 overdue) | Wiadomości informacyjne (E1/S1/W1 initial) |
|-------|----------------------------|-------------------------------------------|
| **Endpoint** | `/api/windykacja/auto-send-overdue` | `/api/windykacja/auto-send-initial` |
| **Cel** | Przypomnienie o zaległej płatności | Informacja o wystawieniu faktury |
| **Harmonogram** | **8:15 AM** codziennie | **8:00 AM** codziennie |
| **Warunek klienta** | ✅ **Wymaga** `[WINDYKACJA]true` | ❌ Ignoruje windykację |
| **Warunek faktury (STOP)** | ✅ **Respektuje** STOP | ❌ Ignoruje STOP |
| **Filtry faktur** | **Przeterminowane** (payment_to < dzisiaj) | **Nowe** (issue_date w ostatnich 3 dniach) |
| **Cel biznesowy** | Aktywna windykacja (nagabywanie) | Uprzejme powiadomienie |

---

## 🚀 Deployment

### Vercel (rekomendowane):

1. Commit i push zmian:
   ```bash
   git add .
   git commit -m "feat: Add auto-send for overdue invoices"
   git push
   ```

2. Vercel automatycznie:
   - Wykryje `vercel.json`
   - Ustawi crony
   - Uruchomi pierwszy run następnego dnia o 8:15 AM

3. Sprawdź w Vercel Dashboard → **Cron Jobs**

### GitHub Actions (alternatywa):

```yaml
name: Auto-send windykacja

on:
  schedule:
    - cron: '15 7 * * *'  # 8:15 CET (7:15 UTC)
  workflow_dispatch:

jobs:
  auto-send:
    runs-on: ubuntu-latest
    steps:
      - name: Call auto-send endpoint
        run: |
          curl -X POST https://twoja-domena.vercel.app/api/windykacja/auto-send-overdue
```

---

## 🐛 Troubleshooting

| Problem | Rozwiązanie |
|---------|-------------|
| Wiadomości nie idą | Sprawdź logi w Vercel, upewnij się że endpoint działa |
| Za dużo wiadomości | Zmniejsz zakres dat lub dodaj dodatkowe filtry |
| Za mało wiadomości | Sprawdź czy klienci mają `[WINDYKACJA]true` w note |
| SMS nie idzie | Sprawdź `SMSPLANET_API_TOKEN` w `.env` |
| Email nie idzie | Sprawdź `N8N_WEBHOOK_EMAIL` w `.env` |
| Cron nie uruchamia się | Sprawdź konfigurację w Vercel Dashboard |
| Faktura nie kwalifikuje się | Użyj `node check-invoice.mjs` aby sprawdzić warunki |

---

## 📚 Pliki w projekcie

| Plik | Opis |
|------|------|
| `app/api/windykacja/auto-send-overdue/route.ts` | **Główny endpoint windykacji** |
| `vercel.json` | Konfiguracja cronów Vercel |
| `scripts/test-auto-send-overdue.ts` | Skrypt testowy |
| `scripts/enable-windykacja-test-client.mjs` | Włącza windykację dla klienta testowego |
| `check-invoice.mjs` | Sprawdza uprawnienia faktury |
| `lib/client-flags-v2.ts` | Parsowanie flag klienta (`[WINDYKACJA]`) |
| `components/WindykacjaToggle.tsx` | Przełącznik windykacji w UI |
| `WINDYKACJA_AUTO_SEND.md` | **Ten plik** - dokumentacja |

---

## 🎯 Następne kroki

1. ✅ Deploy na Vercel
2. ✅ Włącz windykację dla wybranych klientów (przez UI lub API)
3. ✅ Monitoruj pierwszy run o 8:15 AM następnego dnia
4. ✅ Sprawdź logi przez 7 dni
5. ✅ Upewnij się, że limity API nie są przekraczane
6. ✅ Sprawdź czy S1/E1 idą poprawnie do klientów

---

## 💡 Pro Tips

- **Włączaj windykację stopniowo**: Najpierw dla 5-10 klientów, obserwuj reakcje
- **Monitoruj opinie**: Klienci mogą źle reagować na auto-SMS
- **Używaj STOP**: Jeśli klient zgłasza uwagi, włącz STOP na konkretnych fakturach
- **S2/S3/E2/E3**: Można rozbudować system o kolejne poziomy przypomnień (po 7/14 dniach)

---

## 📞 Kontakt

W razie problemów:
1. Sprawdź logi w Vercel Dashboard
2. Przeczytaj [dokumentację](WINDYKACJA_AUTO_SEND.md)
3. Uruchom test: `npx tsx scripts/test-auto-send-overdue.ts`
4. Sprawdź fakturę: `node check-invoice.mjs`

---

**Gotowe!** System automatycznej windykacji jest w pełni zaimplementowany i gotowy do użycia. 🚀
