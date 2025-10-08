# 🔧 MCP Servers - Status i Konfiguracja

## 📊 Aktualny Status (2025-10-08)

```bash
claude mcp list
```

### ✅ Działające (4/7)

| Serwer | Status | Opis | Użycie |
|--------|--------|------|---------|
| **Context7** | ✅ Connected | Dokumentacja bibliotek | Aktywnie używany |
| **Git MCP** | ✅ Connected | Operacje Git | Gotowy do użycia |
| **Playwright** | ✅ Connected | Testy E2E | Zabezpieczony (tylko client 211779362) |
| **Filesystem** | ✅ Connected | Operacje na plikach | Aktywnie używany |

### ⚠️ Wymaga Autentykacji (2/7)

| Serwer | Status | Powód | Co zrobić |
|--------|--------|-------|-----------|
| **Supabase MCP** | ⚠️ Needs authentication | Wymaga OAuth login | Zautentykować gdy będzie potrzebne |
| **Jam** | ⚠️ Needs authentication | Wymaga konta Jam.dev | Zautentykować gdy będzie potrzebne |

### ❌ Nie Działa (1/7)

| Serwer | Status | Powód | Co zrobić |
|--------|--------|-------|-----------|
| **Sentry MCP** | ❌ Failed to connect | Wymaga konta Sentry + token | Skonfigurować gdy założysz konto |

---

## 🔍 Szczegóły Konfiguracji

### 1. ✅ Context7 (ACTIVE)
```json
{
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "@upstash/context7-mcp@latest"]
}
```
**Status:** Działa ✅
**Użycie:** Automatyczne - używam do sprawdzania dokumentacji (Next.js, React, Supabase)

---

### 2. ✅ Git MCP (ACTIVE)
```json
{
  "type": "stdio",
  "command": "npx",
  "args": ["@cyanheads/git-mcp-server"]
}
```
**Status:** Działa ✅
**Użycie:** Gotowy - mogę robić commity, push, branching przez MCP
**Dokumentacja:** Może zastąpić bash git commands

---

### 3. ✅ Playwright (ACTIVE + SECURED)
```json
{
  "type": "stdio",
  "command": "npx",
  "args": ["@executeautomation/playwright-mcp-server"]
}
```
**Status:** Działa ✅
**Zabezpieczenia:** ✅ Tylko client 211779362
**Użycie:** Testy E2E z safety guards
**Dokumentacja:** [.github/SAFETY_CONFIG.md](.github/SAFETY_CONFIG.md)

---

### 4. ✅ Filesystem (ACTIVE)
```json
{
  "type": "stdio",
  "command": "npx",
  "args": [
    "@modelcontextprotocol/server-filesystem",
    "/workspaces/Carebiuro_windykacja"
  ]
}
```
**Status:** Działa ✅
**Scope:** Tylko folder projektu
**Użycie:** Automatyczne - operacje na plikach

---

### 5. ⚠️ Supabase MCP (NEEDS AUTH)
```json
{
  "type": "http",
  "url": "https://mcp.supabase.com/mcp"
}
```
**Status:** Wymaga OAuth ⚠️
**Powód:** HTTP MCP server wymaga logowania przez przeglądarkę

**Jak aktywować:**
```bash
# Krok 1: Claude spróbuje użyć Supabase MCP
# Krok 2: Otworzy się przeglądarka
# Krok 3: Zalogujesz się do Supabase
# Krok 4: Wybierzesz projekt (gbylzdyyhnvmrgfgpfqh)
# Krok 5: MCP będzie działać
```

**⚠️ UWAGA BEZPIECZEŃSTWA:**
- Supabase MCP daje pełny dostęp do bazy (read + write)
- **Zalecam:** Używać tylko na development projects
- **Opcja:** Możemy skonfigurować read-only mode
- **Dokumentacja:** https://supabase.com/docs/guides/getting-started/mcp

**Kiedy używać:**
- Gdy potrzebujesz zaawansowanych queries bez pisania SQL
- Gdy chcesz zarządzać tabelami przez Claude
- **NIE** używać na production bez testów

---

### 6. ⚠️ Jam (NEEDS AUTH)
```json
{
  "type": "http",
  "url": "https://mcp.jam.dev/mcp"
}
```
**Status:** Wymaga autentykacji ⚠️
**Powód:** Wymaga konta Jam.dev

**Jak używać:**
1. **Ty** musisz nagrać Jam (rozszerzenie Chrome):
   - Wejdź na stronę z błędem
   - Kliknij rozszerzenie Jam
   - Nagraj problem (screen + console + network)
   - Dostaniesz link: `https://jam.dev/c/abc123...`

2. **Dasz mi link:**
   ```
   Ty: "Claude, przeanalizuj: https://jam.dev/c/abc123"
   Ja: [używam Jam MCP] "Analizuję błąd..."
   ```

**Dokumentacja:** Sekcja o Jam w [.github/MCP_SERVERS_REVIEW.md](.github/MCP_SERVERS_REVIEW.md)

---

### 7. ❌ Sentry MCP (NOT CONFIGURED)
```json
{
  "type": "stdio",
  "command": "npx",
  "args": ["@getsentry/sentry-mcp"]
}
```
**Status:** Nie działa ❌
**Powód:** Wymaga:
- Konta Sentry (https://sentry.io)
- Auth Token
- Org + Project name

**Jak skonfigurować:**
1. Załóż konto Sentry (darmowe)
2. Skopiuj Auth Token
3. Dodaj do konfiguracji:
```json
{
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
```

**Dokumentacja:** [.github/SENTRY_SETUP.md](.github/SENTRY_SETUP.md)

---

## 🎯 Co Działa vs Co Wymaga Akcji

### ✅ Gotowe do użycia (nie musisz nic robić)
1. Context7 - dokumentacja
2. Git MCP - git operations
3. Playwright - testy (z safeguards)
4. Filesystem - pliki projektu

### ⚠️ Działa, ale wymaga Twojej autentykacji (gdy będziesz chciał użyć)
5. Supabase MCP - zaloguj przez OAuth gdy będę potrzebował
6. Jam - nagraj Jam i daj mi link

### ❌ Nie działa (musisz skonfigurować jeśli chcesz)
7. Sentry MCP - załóż konto + dodaj token

---

## 🔧 Dlaczego Supabase MCP był nieaktywny?

### Problem:
Początkowo próbowałem zainstalować Supabase MCP jako **stdio** z pakietu `@supabase-community/supabase-mcp`, ale:

1. ❌ Pakiet nie istnieje w npm
2. ❌ Był błędny namespace

### Rozwiązanie:
Zmieniono na oficjalny serwer Supabase:

```bash
# ❌ PRZED (nie działało)
{
  "type": "stdio",
  "command": "npx",
  "args": ["@supabase-community/supabase-mcp"]
}

# ✅ PO (działa, wymaga OAuth)
{
  "type": "http",
  "url": "https://mcp.supabase.com/mcp"
}
```

### Różnica:
- **stdio MCP** = lokalny proces (npm package)
- **HTTP MCP** = remote service (wymaga OAuth)

Supabase używa HTTP MCP z OAuth, bo daje lepsze bezpieczeństwo (kontrola dostępu per projekt).

---

## 🚀 Quick Commands

### Sprawdź status wszystkich MCP:
```bash
claude mcp list
```

### Usuń MCP serwer:
```bash
claude mcp remove <nazwa>
```

### Dodaj MCP serwer:
```bash
# stdio (npm package)
claude mcp add <nazwa> npx <package> -t stdio -s user

# HTTP (remote service)
claude mcp add <nazwa> <url> -t http -s user
```

### Zobacz szczegóły konfiguracji:
```bash
cat ~/.claude.json | jq '.mcpServers'
```

---

## 📝 Następne Kroki

### Teraz (już działa):
1. ✅ Context7 - używam aktywnie
2. ✅ Git MCP - gotowy do użycia
3. ✅ Playwright - zabezpieczony, gotowy do testów
4. ✅ Filesystem - używam aktywnie

### Jak będziesz potrzebował:
5. ⚠️ Supabase MCP - zautentykuję Cię przez OAuth
6. ⚠️ Jam - nagrasz Jam i dasz link

### Opcjonalnie (jeśli chcesz):
7. ❌ Sentry MCP - załóż konto → dostaniesz production monitoring

---

## 🔒 Bezpieczeństwo MCP Serwerów

### Read-Only (bezpieczne):
- ✅ Context7 (tylko czyta dokumentację)
- ✅ Filesystem (tylko projekty które whitelistujesz)

### Read + Write (wymaga ostrożności):
- ⚠️ Git MCP (może robić commity/push)
- ⚠️ Playwright (może klikać w UI - zabezpieczony)
- ⚠️ Supabase MCP (może modyfikować bazę - używać ostrożnie)

### External Services (wymaga konta):
- ⚠️ Jam (wymaga konta, ale read-only)
- ⚠️ Sentry (wymaga konta i tokenu)

**Rekomendacja:**
- Używaj tylko zaufanych MCP serwerów
- Read-only gdzie się da
- Testuj na development przed production
- Whitelistuj co można (jak z Playwright)

---

*Ostatnia aktualizacja: 2025-10-08*
*Status: 4/7 aktywnych, 2/7 wymaga auth, 1/7 wymaga konfiguracji*
