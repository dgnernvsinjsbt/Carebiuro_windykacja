# Automatyczne wysyłanie E1, S1, W1 o 8:00 rano

## Opis

System automatycznie wysyła wiadomości informacyjne o wystawieniu faktury:
- **E1** - e-mail informacyjny
- **S1** - SMS informacyjny
- **W1** - WhatsApp informacyjny

**Ważne**: To NIE są przypomnienia windykacyjne, tylko informacje o fakturze, więc:
- ✅ **Ignorują** flagę `STOP` (na poziomie faktury)
- ✅ **Ignorują** flagę `WINDYKACJA` (na poziomie klienta)
- ✅ Wysyłają się **automatycznie** bez interwencji użytkownika

## Warunki wysyłki

Wiadomość E1/S1/W1 zostanie wysłana automatycznie, jeśli:

1. ✅ Faktura została **wystawiona w ciągu ostatnich 3 dni**
2. ✅ Faktura **nie jest opłacona** (`status != 'paid'`)
3. ✅ Faktura **nie jest anulowana** (`kind != 'canceled'`)
4. ✅ Faktura ma **nieopłacone saldo** (`total - paid > 0`)
5. ✅ Dana wiadomość **jeszcze nie została wysłana** (E1/S1/W1 = false w `[FISCAL_SYNC]`)

## Konfiguracja crona

### Opcja 1: Vercel Cron Jobs (rekomendowane)

Dodaj do `vercel.json`:

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

### Opcja 2: GitHub Actions

Stwórz `.github/workflows/auto-send-initial.yml`:

```yaml
name: Auto-send E1/S1/W1

on:
  schedule:
    # Codziennie o 8:00 (UTC+1 = 7:00 UTC w zimie, 6:00 UTC w lecie)
    - cron: '0 7 * * *'
  workflow_dispatch: # Pozwala na ręczne uruchomienie

jobs:
  auto-send:
    runs-on: ubuntu-latest
    steps:
      - name: Call auto-send endpoint
        run: |
          curl -X POST https://twoja-domena.vercel.app/api/windykacja/auto-send-initial \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer ${{ secrets.CRON_SECRET }}"
```

### Opcja 3: n8n Workflow

Stwórz workflow w n8n:

1. **Trigger**: Schedule Trigger (Cron: `0 8 * * *`)
2. **HTTP Request Node**:
   - Method: POST
   - URL: `https://twoja-domena.vercel.app/api/windykacja/auto-send-initial`
   - Headers: `Content-Type: application/json`

## Bezpieczeństwo (opcjonalnie)

Jeśli chcesz zabezpieczyć endpoint przed nieautoryzowanym dostępem, dodaj do endpointu:

```typescript
// W pliku route.ts
const cronSecret = request.headers.get('authorization')?.replace('Bearer ', '');
if (cronSecret !== process.env.CRON_SECRET) {
  return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
}
```

I dodaj `CRON_SECRET` do `.env`:

```bash
CRON_SECRET=twoj-losowy-klucz-tajny
```

## Testowanie ręczne

### 1. Przez curl

```bash
curl -X POST http://localhost:3000/api/windykacja/auto-send-initial \
  -H "Content-Type: application/json"
```

### 2. Przez przeglądarkę (Postman/Thunder Client)

- Method: `POST`
- URL: `http://localhost:3000/api/windykacja/auto-send-initial`
- Headers: `Content-Type: application/json`

### 3. Przez kod testowy

```typescript
// scripts/test-auto-send.ts
const response = await fetch('http://localhost:3000/api/windykacja/auto-send-initial', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
});

const result = await response.json();
console.log(result);
```

## Monitoring

Endpoint zwraca szczegółowy raport:

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

## Logi

Wszystkie operacje są logowane w konsoli:

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

## Najlepsze praktyki

1. **Uruchamiaj o 8:00 rano** - najlepszy czas na informowanie klientów
2. **Monitoruj logi** - sprawdzaj, czy wszystkie wiadomości idą
3. **Testuj regularnie** - upewnij się, że API SMS/Email/WhatsApp działają
4. **Sprawdzaj limity API** - SMS Planet ma limit 1000 req/h

## Różnice vs windykacja S1

| Cecha | Auto-send S1 (informacyjny) | Windykacja S1 (przypomnienie) |
|-------|----------------------------|-------------------------------|
| **Warunek STOP** | ❌ Ignoruje | ✅ Respektuje |
| **Warunek WINDYKACJA** | ❌ Ignoruje | ✅ Respektuje |
| **Kiedy wysyła** | Automatycznie o 8:00 (ostatnie 3 dni) | Ręcznie lub przez auto-send windykacji |
| **Cel** | Informacja o wystawieniu | Przypomnienie o płatności |
| **Endpoint** | `/api/windykacja/auto-send-initial` | `/api/windykacja/auto-send` |

## FAQ

### Co jeśli faktura ma już E1 wysłany, ale nie ma S1?

System wyśle tylko S1 (pominie E1).

### Co jeśli faktura została wystawiona 2 dni temu, a dziś jest sobota?

System wyśle wiadomości (działa 7 dni w tygodniu).

### Co jeśli faktura została już opłacona?

System pominie tę fakturę (sprawdza `status != 'paid'`).

### Co jeśli klient nie ma numeru telefonu?

S1 zwróci błąd, ale E1 i W1 nadal pójdą (jeśli są adresy).

## Troubleshooting

| Problem | Rozwiązanie |
|---------|-------------|
| Wiadomości nie idą | Sprawdź logi, upewnij się że endpoint działa |
| Za dużo wiadomości | Zmniejsz okno z 3 dni na 1 dzień |
| Za mało wiadomości | Sprawdź filtry (może faktury są starsze niż 3 dni) |
| SMS nie idzie | Sprawdź `SMSPLANET_API_TOKEN` w `.env` |
| Email nie idzie | Sprawdź `N8N_WEBHOOK_EMAIL` w `.env` |

## Aktywacja

Po dodaniu crona w Vercel/GitHub/n8n, system będzie automatycznie wysyłał wiadomości codziennie o 8:00 rano.

**Gotowe!** 🚀
