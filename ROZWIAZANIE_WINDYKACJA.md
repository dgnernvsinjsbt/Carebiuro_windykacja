# ✅ ROZWIĄZANIE: Niewysłane maile/SMS windykacyjne
**Data**: 2025-11-30
**Status**: NAPRAWIONE

---

## 🎯 ZNALEZIONE PROBLEMY

### Problem 1: Vercel Cron wysyła GET zamiast POST ❌
**Lokalizacja**: Vercel Cron + endpointy windykacji
**Objaw**: Błąd 405 Bad Request w logach (08:00:22 i 08:15:31)
**Przyczyna**:
- Vercel Cron domyślnie wysyła **GET requests**
- Endpointy miały tylko `export async function POST`
- Brak `GET` handlera → 405 Method Not Allowed

**Rozwiązanie**: ✅ NAPRAWIONE
```typescript
// Dodano do obu endpointów:
export async function GET(request: NextRequest) {
  console.log('[AutoSend] GET request received, forwarding to POST handler');
  return POST(request);
}
```

---

### Problem 2: BRAK CRON_SECRET w .env ❌
**Lokalizacja**: `/workspaces/Carebiuro_windykacja/.env`
**Objaw**: Endpoint loguje WARNING
**Przyczyna**: Zmienna `CRON_SECRET` nie była ustawiona

**Rozwiązanie**: ✅ NAPRAWIONE
```env
CRON_SECRET=eByVvHXtemKSILLoaVnWQOLo5ythfBbTVnw1T7nyvdg=
```

**⚠️ MUSISZ JESZCZE**:
1. Dodać ten sam secret do Vercel Dashboard:
   ```
   Project Settings → Environment Variables
   Name: CRON_SECRET
   Value: eByVvHXtemKSILLoaVnWQOLo5ythfBbTVnw1T7nyvdg=
   ```

2. Redeploy aplikacji (push do GitHub lub manual deploy)

---

### Problem 3: Adrian Piskula - brak telefonu + STOP=TRUE ⚠️
**Klient**: Adrian Piskula (ID: 136422702)
**Email**: apiskula076@gmail.com
**Telefon**: `null` ❌

**Faktury**:
```
FP2024/08/001572 - 695 PLN outstanding - brak internal_note
FP2024/08/000870 - 65 PLN outstanding  - STOP=TRUE
FP2024/07/000885 - 65 PLN outstanding  - STOP=TRUE
FP2024/06/000893 - 65 PLN outstanding  - STOP=TRUE
FP2024/05/000998 - 65 PLN outstanding  - STOP=TRUE
```

**Dlaczego SMS nie wysłane**:
1. ❌ **Brak numeru telefonu** - system nie może wysłać SMS
2. 🛑 **4 z 5 faktur ma STOP=TRUE** - windykacja ręcznie wstrzymana
3. ✅ **System poprawnie pomija takie faktury**

**Co zrobić**:
- [ ] Dodaj telefon do klienta w Fakturowni
- [ ] Usuń STOP=TRUE z faktur (lub zostaw jeśli celowo zatrzymane)
- [ ] Po dodaniu telefonu: zaznacz windykację ponownie w UI

---

## 📊 CO ZOSTAŁO NAPRAWIONE

### 1. Dodano GET handler do endpointów windykacji
**Pliki zmienione**:
- `/app/api/windykacja/auto-send-initial/route.ts` (linie 260-264)
- `/app/api/windykacja/auto-send-overdue/route.ts` (linie 262-266)

**Efekt**:
- Vercel Cron teraz może wywołać endpointy przez GET
- Błąd 405 nie powinien się więcej pojawiać

---

### 2. Dodano CRON_SECRET do .env
**Plik zmieniony**:
- `/workspaces/Carebiuro_windykacja/.env`

**Efekt**:
- Endpointy będą weryfikować secret
- Ochrona przed nieautoryzowanymi wywołaniami

---

## 🚀 DEPLOYMENT

### Krok 1: Commit zmian
```bash
git add .
git commit -m "fix: Add GET handlers for Vercel Cron + CRON_SECRET"
git push origin main
```

### Krok 2: Dodaj CRON_SECRET w Vercel
1. Zaloguj się do https://vercel.com
2. Wybierz projekt: carebiuro-windykacja
3. Settings → Environment Variables
4. Add New:
   - **Name**: `CRON_SECRET`
   - **Value**: `eByVvHXtemKSILLoaVnWQOLo5ythfBbTVnw1T7nyvdg=`
   - **Environment**: Production, Preview, Development (zaznacz wszystkie)
5. Kliknij Save

### Krok 3: Redeploy
```bash
# Automatycznie po push do GitHub
# LUB ręcznie w Vercel Dashboard → Deployments → Redeploy
```

---

## ✅ WERYFIKACJA

Po deploy sprawdź:

### 1. Logi Vercel (jutro o 8:00 CET)
```
https://vercel.com/your-team/carebiuro-windykacja/logs

Szukaj:
✅ "[AutoSendInitial] GET request received"
✅ "[AutoSendInitial] Starting auto-send"
✅ "Auto-send completed: X sent, Y failed"

❌ Brak "405 Bad Request"
❌ Brak "401 Unauthorized"
```

### 2. Supabase - message_history
```sql
SELECT * FROM message_history
WHERE sent_at > NOW() - INTERVAL '2 hours'
ORDER BY sent_at DESC;
```

Powinny pojawić się wpisy z dzisiejszej wysyłki.

### 3. Test ręczny (opcjonalnie)
```bash
# Wywołaj endpoint ręcznie
curl -X GET "https://carebiuro-windykacja.vercel.app/api/windykacja/auto-send-initial" \
  -H "X-Cron-Secret: eByVvHXtemKSILLoaVnWQOLo5ythfBbTVnw1T7nyvdg="
```

---

## 📋 TODO DLA UŻYTKOWNIKA

- [ ] **PILNE**: Dodaj CRON_SECRET do Vercel Environment Variables
- [ ] **PILNE**: Commit i push zmian do GitHub
- [ ] Dodaj telefon do Adriana Piskuli w Fakturowni
- [ ] Sprawdź logi jutro o 8:15 CET (po uruchomieniu crona)
- [ ] Zweryfikuj message_history w Supabase
- [ ] Rozważ dodanie tabeli `sms_send_log` dla lepszego monitoringu

---

## 🔮 REKOMENDACJE NA PRZYSZŁOŚĆ

### 1. Stwórz tabelę do logowania pominięć
```sql
CREATE TABLE sms_skip_log (
  id BIGSERIAL PRIMARY KEY,
  client_id BIGINT REFERENCES clients(id),
  invoice_id BIGINT REFERENCES invoices(id),
  skip_reason TEXT, -- 'no_phone', 'stop_true', 'already_sent', 'no_balance'
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2. Dodaj GitHub Actions jako backup
```yaml
# .github/workflows/windykacja-cron.yml
name: Windykacja Backup Cron
on:
  schedule:
    - cron: '30 7 * * *'  # 7:30 UTC jako backup
```

### 3. Monitoring alerts (Sentry/Email)
- Alert jeśli > 50% SMS-ów failed
- Alert jeśli cron się nie uruchomił przez 2 dni

---

## ✨ PODSUMOWANIE

**Główny problem**: Vercel Cron wysyła GET, a endpointy akceptowały tylko POST
**Drugi problem**: Brak CRON_SECRET w konfiguracji
**Trzeci problem**: Konkretny klient (Adrian Piskula) nie miał telefonu + STOP=TRUE

**Status**:
- ✅ Kod naprawiony (GET handlers dodane)
- ✅ CRON_SECRET wygenerowany i dodany do .env
- ⏳ Wymaga deployment + konfiguracji Vercel
- ⏳ Wymaga dodania telefonu do klienta

**Następne uruchomienie crona**:
- Jutro 2025-12-01 o 08:00 CET (auto-send-initial)
- Jutro 2025-12-01 o 08:15 CET (auto-send-overdue)

---

**Data naprawy**: 2025-11-30
**Autor**: Claude Code
**Pliki zmienione**: 3 (2 endpointy + .env)
