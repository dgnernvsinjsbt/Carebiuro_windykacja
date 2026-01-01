# 📧 Podsumowanie: Automatyczne wysyłanie E1/S1/W1

## ✅ Co zostało zaimplementowane

### 1. Endpoint API
**Plik**: [`app/api/windykacja/auto-send-initial/route.ts`](app/api/windykacja/auto-send-initial/route.ts)

**Funkcja**: Automatycznie wysyła wiadomości informacyjne (E1, S1, W1) dla faktur wystawionych w ostatnich 3 dniach.

**Kluczowe różnice** vs windykacja:
- ❌ **Ignoruje** flagę `STOP` (poziom faktury)
- ❌ **Ignoruje** flagę `WINDYKACJA` (poziom klienta)
- ✅ Tylko dla **nowo wystawionych faktur** (3 dni)
- ✅ Nie wysyła **ponownie** (sprawdza `E1/S1/W1` w `[FISCAL_SYNC]`)

### 2. Konfiguracja Cron
**Plik**: [`vercel.json`](vercel.json)

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

**Harmonogram**: Codziennie o **8:00 rano**

### 3. Dokumentacja
**Plik**: [`CRON_AUTO_SEND.md`](CRON_AUTO_SEND.md)

Zawiera:
- Szczegółowy opis działania
- Opcje konfiguracji crona (Vercel, GitHub Actions, n8n)
- Instrukcje testowania
- FAQ i troubleshooting

### 4. Skrypt testowy
**Plik**: [`scripts/test-auto-send-initial.ts`](scripts/test-auto-send-initial.ts)

**Użycie**:
```bash
npx ts-node scripts/test-auto-send-initial.ts
```

### 5. CHANGELOG
**Plik**: [`CHANGELOG.md`](CHANGELOG.md)

Dodano sekcję **[1.2.0] - 2025-10-07** z pełnym opisem nowej funkcjonalności.

---

## 🎯 Jak to działa

### Logika wysyłania

```
Codziennie o 8:00 rano:
1. Pobierz wszystkie faktury z Fakturowni
2. Filtruj faktury spełniające warunki:
   ✅ Wystawione w ostatnich 3 dniach
   ✅ Status != 'paid'
   ✅ Kind != 'canceled'
   ✅ Saldo > 0 (total - paid > 0)
   ✅ E1/S1/W1 jeszcze nie wysłane
3. Dla każdej faktury:
   - Wyślij E1 (jeśli nie wysłany)
   - Wyślij S1 (jeśli nie wysłany)
   - Wyślij W1 (jeśli nie wysłany)
4. Zaktualizuj [FISCAL_SYNC] w Fakturowni
5. Zwróć raport z wynikami
```

### Warunki wysyłki

| Warunek | Opis |
|---------|------|
| **Data wystawienia** | Ostatnie 3 dni |
| **Status faktury** | Nie opłacona (`status != 'paid'`) |
| **Rodzaj faktury** | Nie anulowana (`kind != 'canceled'`) |
| **Saldo** | Nieopłacone (`total - paid > 0`) |
| **Flaga E1/S1/W1** | Jeszcze nie wysłana (`false` w `[FISCAL_SYNC]`) |
| **Flaga STOP** | ❌ **Ignorowana** (to nie windykacja!) |
| **Flaga WINDYKACJA** | ❌ **Ignorowana** (to nie windykacja!) |

---

## 🚀 Aktywacja

### Opcja 1: Vercel (rekomendowane)

1. Deploy projektu na Vercel
2. Vercel automatycznie wykryje `vercel.json` i ustawi crona
3. Sprawdź logi w Vercel Dashboard → Cron Jobs

### Opcja 2: GitHub Actions

1. Stwórz plik `.github/workflows/auto-send-initial.yml`:
```yaml
name: Auto-send E1/S1/W1

on:
  schedule:
    - cron: '0 7 * * *'  # 8:00 CET
  workflow_dispatch:

jobs:
  auto-send:
    runs-on: ubuntu-latest
    steps:
      - name: Call auto-send endpoint
        run: |
          curl -X POST https://twoja-domena.vercel.app/api/windykacja/auto-send-initial
```

### Opcja 3: n8n Workflow

1. W n8n, dodaj **Schedule Trigger**
   - Cron: `0 8 * * *`
2. Dodaj **HTTP Request Node**
   - Method: POST
   - URL: `https://twoja-domena.vercel.app/api/windykacja/auto-send-initial`

---

## 🧪 Testowanie

### Ręcznie przez API

```bash
curl -X POST http://localhost:3000/api/windykacja/auto-send-initial \
  -H "Content-Type: application/json"
```

### Przez skrypt testowy

```bash
npx ts-node scripts/test-auto-send-initial.ts
```

### Spodziewany output

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

---

## 📊 Monitorowanie

### Logi w konsoli

```
[AutoSendInitial] Starting auto-send for E1/S1/W1...
[AutoSendInitial] Looking for invoices issued after 2025-10-04T00:00:00.000Z
[AutoSendInitial] Found 234 total invoices, filtering...
[AutoSendInitial] Found 12 eligible invoices out of 234
[AutoSendInitial] Sending E1 for invoice 12345 (FV/2025/001)
[AutoSendInitial] ✓ E1 sent for invoice 12345
[AutoSendInitial] Sending S1 for invoice 12345 (FV/2025/001)
[AutoSendInitial] ✓ S1 sent for invoice 12345
[AutoSendInitial] Completed: 24 total sent (E1: 8, S1: 10, W1: 6), 3 failed
```

### Co sprawdzać

1. **Pierwszych 7 dni**: Sprawdzaj logi codziennie
2. **Limity API**: SMS Planet (1000 req/h), Fakturownia (1000 req/h)
3. **Błędy**: Brak numerów telefonu, błędne adresy email

---

## ⚠️ Różnice: E1 vs S1 (windykacja)

| Cecha | E1/S1/W1 (informacyjne) | S1 (windykacja - stary endpoint) |
|-------|-------------------------|----------------------------------|
| **Endpoint** | `/api/windykacja/auto-send-initial` | `/api/windykacja/auto-send` |
| **Cel** | Informacja o wystawieniu | Przypomnienie o płatności |
| **STOP** | ❌ Ignoruje | ✅ Respektuje |
| **WINDYKACJA** | ❌ Ignoruje | ✅ Respektuje |
| **Kiedy** | Auto o 8:00 (ostatnie 3 dni) | Ręcznie/auto (windykacja) |
| **Filtry** | Tylko nowe faktury (3 dni) | Wszystkie nieopłacone |

---

## 🔧 Konfiguracja środowiska

### Wymagane zmienne (.env)

```bash
# Fakturownia API
FAKTUROWNIA_API_TOKEN=<twoj-token>
FAKTUROWNIA_ACCOUNT=<twoje-konto>

# SMS Planet API (dla S1)
SMSPLANET_API_TOKEN=<twoj-token>
SMSPLANET_FROM=Cbb-Office

# n8n webhooks (dla E1/W1)
N8N_WEBHOOK_EMAIL=https://n8n.twoja-domena.pl/webhook/email
N8N_WEBHOOK_WHATSAPP=https://n8n.twoja-domena.pl/webhook/whatsapp

# Supabase
NEXT_PUBLIC_SUPABASE_URL=<url>
NEXT_PUBLIC_SUPABASE_ANON_KEY=<key>
```

---

## 📚 Pliki w projekcie

| Plik | Opis |
|------|------|
| `app/api/windykacja/auto-send-initial/route.ts` | Główny endpoint |
| `vercel.json` | Konfiguracja crona Vercel |
| `CRON_AUTO_SEND.md` | Pełna dokumentacja |
| `scripts/test-auto-send-initial.ts` | Skrypt testowy |
| `CHANGELOG.md` | Historia zmian (sekcja 1.2.0) |
| `AUTO_SEND_SUMMARY.md` | **Ten plik** - krótkie podsumowanie |

---

## 🎯 Następne kroki

1. ✅ Deploy na Vercel
2. ✅ Sprawdź czy cron działa (pierwszy run o 8:00 następnego dnia)
3. ✅ Monitoruj logi przez 7 dni
4. ✅ Upewnij się, że wiadomości idą poprawnie
5. ✅ Sprawdź limity API (czy nie przekraczamy)

---

## 🐛 Troubleshooting

| Problem | Rozwiązanie |
|---------|-------------|
| Wiadomości nie idą | Sprawdź logi, upewnij się że endpoint działa |
| Za dużo wiadomości | Zmniejsz okno z 3 dni na 1 dzień (w kodzie) |
| Za mało wiadomości | Sprawdź filtry (może faktury są starsze) |
| SMS nie idzie | Sprawdź `SMSPLANET_API_TOKEN` w `.env` |
| Email nie idzie | Sprawdź `N8N_WEBHOOK_EMAIL` w `.env` |
| Cron nie uruchamia się | Sprawdź konfigurację w Vercel Dashboard |

---

## 📞 Kontakt

W razie problemów:
1. Sprawdź logi w Vercel Dashboard
2. Przeczytaj [`CRON_AUTO_SEND.md`](CRON_AUTO_SEND.md)
3. Uruchom test ręcznie: `npx ts-node scripts/test-auto-send-initial.ts`

---

**Gotowe!** System automatycznego wysyłania E1/S1/W1 jest w pełni zaimplementowany i gotowy do użycia. 🚀
