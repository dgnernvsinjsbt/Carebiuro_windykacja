# 🛡️ Sentry - Production Error Monitoring

## ✅ Status Instalacji MCP

```bash
claude mcp list
```

**Wynik:**
- ✅ Git MCP - Connected
- ⚠️ Sentry MCP - Needs configuration (wymaga konta Sentry)

---

## 🎯 Co to jest Sentry?

Sentry to **external service** (jak Fakturownia, n8n) do monitorowania błędów w czasie rzeczywistym.

### Jak działa:

```
Twoja Aplikacja (Next.js)
    ↓ wysyła błędy
Sentry Cloud (dashboard)
    ↓ analizuje przez
Sentry MCP
    ↓ Claude może debugować
```

---

## 🌍 Development vs Production

### 1. **Development (localhost:3000)**
- Sentry zbiera błędy z lokalnego dev
- Tagowane jako `environment: "development"`
- Przydatne do testowania czy Sentry działa
- ⚠️ To tylko błędy testowe

### 2. **Production (Vercel)**
- Sentry zbiera prawdziwe błędy od klientów
- Tagowane jako `environment: "production"`
- 🎯 **Tu jest największa wartość**
- Real-time monitoring prawdziwych problemów

---

## 📦 Instalacja (3 kroki)

### Krok 1: Załóż konto Sentry (DARMOWE)

1. Wejdź na https://sentry.io/signup/
2. Wybierz plan FREE (do 5000 events/miesiąc)
3. Utwórz nowy projekt → wybierz **Next.js**
4. Skopiuj **DSN** (wygląda jak: `https://abc123@o123.ingest.sentry.io/456`)

---

### Krok 2: Zainstaluj Sentry SDK w projekcie

```bash
cd /workspaces/Carebiuro_windykacja
npm install --save @sentry/nextjs
npx @sentry/wizard@latest -i nextjs
```

Wizard zapyta:
- DSN? → wklej swoje DSN
- Upload source maps? → **Yes** (dla lepszego debugowania)
- Performance monitoring? → **Yes**

---

### Krok 3: Dodaj DSN do .env

```bash
# .env.local (NIE commituj tego pliku!)
NEXT_PUBLIC_SENTRY_DSN=https://twoj-klucz@sentry.io/projekt-id
SENTRY_AUTH_TOKEN=twoj-auth-token-z-sentry
```

Dodaj do `.gitignore`:
```
.env.local
.sentryclirc
```

---

## 🔧 Konfiguracja Next.js

Wizard automatycznie utworzy:

### 1. `sentry.client.config.ts`
```typescript
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // Environment (auto-detect)
  environment: process.env.NODE_ENV,

  // Performance monitoring
  tracesSampleRate: 1.0,

  // Replay sessions (opcjonalnie)
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
});
```

### 2. `sentry.server.config.ts`
```typescript
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 1.0,
});
```

### 3. `sentry.edge.config.ts`
```typescript
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 1.0,
});
```

---

## 🎯 Jak używać Sentry w kodzie

### Automatyczne łapanie błędów:

Sentry automatycznie łapie:
- Nieobsłużone wyjątki
- Promise rejections
- Console errors
- React error boundaries

### Manualne wysyłanie błędów:

```typescript
import * as Sentry from "@sentry/nextjs";

// Prosty error
try {
  await fakturowniaAPI.getInvoice(123);
} catch (error) {
  Sentry.captureException(error);
  throw error;
}

// Error z kontekstem
try {
  await supabase.from('invoices').update({ paid: true });
} catch (error) {
  Sentry.captureException(error, {
    tags: {
      operation: 'invoice_update',
      client_id: clientId
    },
    extra: {
      invoice_id: invoiceId,
      old_status: oldStatus
    }
  });
}

// Custom message
Sentry.captureMessage('Fakturownia API limit reached', {
  level: 'warning',
  tags: { api: 'fakturownia' }
});
```

---

## 📊 Sentry Dashboard - Co zobaczysz

### 1. **Issues (Błędy)**
- Lista wszystkich błędów
- Ile razy wystąpił
- Ilu użytkowników dotknął
- Stack trace

### 2. **Performance**
- Wolne API calls
- Wolne DB queries
- Page load time

### 3. **Releases**
- Które wersje mają najwięcej błędów
- Regression detection

### 4. **Alerts**
- Email/Slack gdy nowy błąd
- Spike detection (nagły wzrost błędów)

---

## 🔍 Jak Claude używa Sentry MCP

### Konfiguracja Sentry MCP:

Po zainstalowaniu MCP, musisz podać token:

```bash
# Ustaw Sentry Auth Token
export SENTRY_AUTH_TOKEN="twoj-sentry-auth-token"
export SENTRY_ORG="twoja-organizacja"
export SENTRY_PROJECT="carebiuro-windykacja"
```

Lub dodaj do `~/.claude.json`:
```json
{
  "mcpServers": {
    "sentry": {
      "type": "stdio",
      "command": "npx",
      "args": ["@getsentry/sentry-mcp"],
      "env": {
        "SENTRY_AUTH_TOKEN": "twoj-token",
        "SENTRY_ORG": "twoja-org",
        "SENTRY_PROJECT": "carebiuro-windykacja"
      }
    }
  }
}
```

### Przykład użycia:

**Ty:**
> Claude, sprawdź ostatnie błędy w Sentry z production

**Claude (używa Sentry MCP):**
```
1. Pobieram issues z Sentry...
2. Filtruję environment: production
3. Analizuję top 5 błędów:

   Error #1: "Cannot read property 'total' of undefined"
   - Wystąpił: 42 razy (ostatnie 24h)
   - Dotknął: 12 użytkowników
   - Plik: app/api/sync/route.ts:156
   - Stack trace: [pokazuje dokładną linię]

4. Sugestia fixu: Dodaj null check przed invoice.total
```

---

## 🚀 Deploy na Vercel

### 1. Dodaj Sentry do Vercel Environment Variables:

W Vercel Dashboard → Settings → Environment Variables:

```
NEXT_PUBLIC_SENTRY_DSN=https://...
SENTRY_AUTH_TOKEN=...
SENTRY_ORG=twoja-org
SENTRY_PROJECT=carebiuro-windykacja
```

### 2. Deploy:

```bash
git add .
git commit -m "feat: Add Sentry error monitoring"
git push origin main
```

Vercel automatycznie:
- Zbuduje z Sentry
- Uploaduje source maps
- Połączy błędy z kodem

---

## 📈 Metryki które powinieneś śledzić

### Production:
1. **Error Rate** - ile błędów na 1000 requestów
2. **MTTR** (Mean Time To Resolution) - jak szybko naprawiasz
3. **Affected Users** - ilu użytkowników dotknął błąd
4. **API Response Time** - czy Fakturownia/Supabase wolno odpowiadają

### Development:
1. **Test Coverage** - które funkcje nie są testowane
2. **New Errors** - nowe błędy wprowadzone w branchu
3. **Performance Regression** - czy nowy kod spowolnił app

---

## ⚠️ Uwagi Bezpieczeństwa

### NIE wysyłaj do Sentry:
- ❌ Tokenów API (Fakturownia, Supabase)
- ❌ Haseł użytkowników
- ❌ Numerów kart kredytowych
- ❌ Danych osobowych (RODO)

### Filtruj wrażliwe dane:

```typescript
// sentry.client.config.ts
Sentry.init({
  beforeSend(event, hint) {
    // Usuń wrażliwe dane
    if (event.request?.headers) {
      delete event.request.headers['Authorization'];
      delete event.request.headers['Cookie'];
    }

    // Maskuj email w error messages
    if (event.message) {
      event.message = event.message.replace(
        /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g,
        '***@***'
      );
    }

    return event;
  }
});
```

---

## 🎯 Quick Start (TL;DR)

```bash
# 1. Załóż konto Sentry (darmowe)
https://sentry.io/signup/

# 2. Zainstaluj SDK
npm install --save @sentry/nextjs
npx @sentry/wizard@latest -i nextjs

# 3. Dodaj DSN do .env.local
NEXT_PUBLIC_SENTRY_DSN=https://...

# 4. Skonfiguruj Sentry MCP (opcjonalne)
export SENTRY_AUTH_TOKEN="..."
export SENTRY_ORG="..."
export SENTRY_PROJECT="carebiuro-windykacja"

# 5. Deploy na Vercel
git push origin main
```

---

## 🔗 Przydatne Linki

- Dashboard Sentry: https://sentry.io/organizations/[twoja-org]/
- Dokumentacja Next.js: https://docs.sentry.io/platforms/javascript/guides/nextjs/
- Sentry MCP GitHub: https://github.com/getsentry/sentry-mcp
- Blog Sentry MCP: https://blog.sentry.io/monitoring-mcp-server-sentry/

---

## ❓ FAQ

**Q: Czy Sentry MCP działa bez konta Sentry?**
A: NIE - musisz mieć konto i token autentykacji.

**Q: Czy Sentry MCP działa w development?**
A: TAK - ale będziesz widział tylko błędy testowe.

**Q: Ile kosztuje Sentry?**
A: Plan FREE: 5000 events/miesiąc (wystarczy na start).

**Q: Czy muszę deploy na Vercel żeby używać Sentry?**
A: NIE - Sentry działa też lokalnie (localhost:3000).

**Q: Jak Claude używa Sentry MCP?**
A: Gdy poprosisz "sprawdź błędy w Sentry", Claude:
   1. Połączy się z Sentry API (przez MCP)
   2. Pobierze listę issues
   3. Przeanalizuje stack traces
   4. Zasugeruje fixy

**Q: Czy muszę instalować Sentry SDK żeby używać Sentry MCP?**
A: TAK - Sentry MCP tylko czyta błędy, ale aplikacja musi je wysyłać (przez SDK).

---

*Ostatnia aktualizacja: 2025-10-08*
*Status: ⚠️ Wymaga konfiguracji konta Sentry*
