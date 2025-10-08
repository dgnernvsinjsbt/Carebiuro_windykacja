# 🔧 MCP Servers - Przegląd dla Carebiuro Windykacja

## ✅ Już Zainstalowane (5/5)

### 1. **Context7** ✅
```bash
# Już zainstalowany
```
- **Co robi:** Dostęp do najnowszej dokumentacji bibliotek (Next.js, React, Supabase, itp.)
- **Przydatność:** ⭐⭐⭐⭐⭐ (ESSENTIAL)
- **Czy używać:** TAK - już aktywnie używamy

### 2. **Playwright** ✅
```bash
# Już zainstalowany + zabezpieczenia
```
- **Co robi:** Automatyzacja testów E2E, browser automation
- **Przydatność:** ⭐⭐⭐⭐⭐ (ESSENTIAL)
- **Czy używać:** TAK - z safeguardami (tylko client 211779362)
- **Status:** Zabezpieczony whitelist, gotowy do testów

### 3. **Supabase MCP** ✅
```bash
# Już zainstalowany
```
- **Co robi:** Operacje na bazie Supabase (read/write)
- **Przydatność:** ⭐⭐⭐⭐⭐ (ESSENTIAL)
- **Czy używać:** TAK - głównie read-only dla bezpieczeństwa
- **Uwaga:** Może nie działać (wymaga konfiguracji projektu)

### 4. **Filesystem** ✅
```bash
# Już zainstalowany
```
- **Co robi:** Operacje na plikach projektu
- **Przydatność:** ⭐⭐⭐⭐⭐ (ESSENTIAL)
- **Czy używać:** TAK - dostęp do struktury projektu

### 5. **Jam** ✅
```bash
# Już zainstalowany
```
- **Co robi:** Debugging przez analizę nagrań Jam (video + logs + network)
- **Przydatność:** ⭐⭐⭐⭐ (VERY USEFUL)
- **Czy używać:** TAK - gdy masz błędy frontend
- **Wymaga:** Ty musisz nagrać Jam → potem dajesz mi link → ja analizuję
- **Instalacja Chrome:** https://chrome.google.com/webstore/detail/jam

---

## 🎯 Bardzo Przydatne (Polecam zainstalować)

### 6. **PostgreSQL MCP Pro** 🔥 RECOMMENDED
```bash
claude mcp add postgres-pro https://github.com/crystaldba/postgres-mcp -t stdio -s user
```
- **Co robi:**
  - Analiza wydajności PostgreSQL/Supabase
  - Rekomendacje indeksów
  - Execution plans
  - Health checks (buffer cache, constraints, vacuum)
- **Przydatność:** ⭐⭐⭐⭐⭐ (CRITICAL dla optymalizacji DB)
- **Dlaczego:** Twoja baza rośnie → potrzebne optymalizacje queries
- **Bezpieczeństwo:** Może być read-only mode

### 7. **Git MCP Server** 🔥 RECOMMENDED
```bash
claude mcp add git https://github.com/cyanheads/git-mcp-server -t stdio -s user
```
- **Co robi:**
  - Pełna kontrola Git (commit, push, pull, branch, merge, rebase)
  - Analiza historii commitów
  - Zarządzanie tagami i worktree
- **Przydatność:** ⭐⭐⭐⭐⭐ (Zastąpi Twoje manualne commity)
- **Dlaczego:** Automatyzacja git operations bez bash
- **Bezpieczeństwo:** Bardziej kontrolowany niż bash git commands

### 8. **GitHub MCP Server (Official)** 🔥 RECOMMENDED
```bash
claude mcp add github https://api.github.com/mcp -t http -s user
```
- **Co robi:**
  - Zarządzanie Issues & PRs
  - Code review automation
  - Repository browsing
  - Workflow automation
- **Przydatność:** ⭐⭐⭐⭐⭐ (Dla PR i Issues)
- **Dlaczego:** Automatyczne tworzenie issues, PR z opisami
- **Uwaga:** Wymaga OAuth GitHub

### 9. **Sentry MCP** 🔥 RECOMMENDED
```bash
claude mcp add sentry https://github.com/getsentry/sentry-mcp -t stdio -s user
```
- **Co robi:**
  - Error tracking i monitoring
  - Analiza crashów
  - Performance monitoring
  - Trace-connected debugging
- **Przydatność:** ⭐⭐⭐⭐⭐ (PRODUCTION MUST-HAVE)
- **Dlaczego:** Real-time error monitoring dla prawdziwych klientów
- **Wymaga:** Konto Sentry (darmowe tier wystarczy)

---

## 🤔 Opcjonalne (Może się przydać)

### 10. **SQL Analyzer MCP**
```bash
claude mcp add sql-analyzer https://github.com/j4c0bs/mcp-server-sql-analyzer -t stdio -s user
```
- **Co robi:** SQL linting, analiza queries, dialect conversion
- **Przydatność:** ⭐⭐⭐ (Nice to have)
- **Dlaczego:** Validation SQL queries przed wykonaniem
- **Kiedy:** Gdy piszesz skomplikowane raw SQL

### 11. **OpenAPI MCP**
```bash
claude mcp add openapi https://github.com/ouvreboite/openapi-to-mcp -t stdio -s user
```
- **Co robi:** Dostęp do API przez OpenAPI specs
- **Przydatność:** ⭐⭐⭐ (Jeśli używasz external APIs)
- **Dlaczego:** Testowanie Fakturownia API, n8n webhooks
- **Kiedy:** Gdy potrzebujesz testować API calls

### 12. **Debugg.AI**
```bash
# Wymaga rejestracji na https://debugg.ai
```
- **Co robi:** Zero-config E2E testing z AI
- **Przydatność:** ⭐⭐⭐ (Konkurencja dla Playwright)
- **Dlaczego:** Może być prostszy niż Playwright
- **Uwaga:** Wymaga external service

---

## ❌ NIE Instaluj (Nie dla tego projektu)

### ❌ **Puppeteer MCP**
- **Powód:** Masz już Playwright (lepszy)

### ❌ **Rubber Duck MCP**
- **Powód:** To tylko chatbot do debugowania (zbędne)

### ❌ **Memory Bank MCP**
- **Powód:** Niepotrzebne - masz CLAUDE.md

---

## 🎯 Rekomendowany Setup dla Carebiuro

### Minimum (już masz):
1. ✅ Context7
2. ✅ Playwright (z safeguards)
3. ✅ Filesystem
4. ✅ Jam

### Polecam dodać (3 najważniejsze):
5. 🔥 **PostgreSQL MCP Pro** - optymalizacja bazy
6. 🔥 **Git MCP** - lepsza kontrola nad git
7. 🔥 **Sentry MCP** - production monitoring

### Opcjonalnie (jeśli potrzebujesz):
8. GitHub MCP - jeśli chcesz automatyzować PRs/Issues
9. SQL Analyzer - jeśli piszesz dużo raw SQL
10. OpenAPI MCP - jeśli testujesz external APIs

---

## 📊 Porównanie: Co daje każdy serwer

| Serwer | Problem który rozwiązuje | Obecnie robisz | Z MCP będzie |
|--------|--------------------------|----------------|--------------|
| **PostgreSQL MCP Pro** | Powolne queries | Ręcznie EXPLAIN queries | Auto-analiza + rekomendacje indeksów |
| **Git MCP** | Commity przez bash | `git add . && git commit` | Inteligentne commity z kontekstem |
| **Sentry MCP** | Błędy w production | Szukasz w console.logs | Real-time error tracking |
| **GitHub MCP** | Tworzenie PRs | Ręcznie przez UI | Auto-tworzenie z opisami |
| **Jam** | Debugging UI bugs | Kopiujesz logi ręcznie | 1 link = wszystkie dane |

---

## 🚀 Quick Install (Top 3)

Jeśli chcesz zainstalować TOP 3 najważniejsze:

```bash
# 1. PostgreSQL MCP Pro (optymalizacja bazy)
claude mcp add postgres-pro https://github.com/crystaldba/postgres-mcp -t stdio -s user

# 2. Git MCP (lepsza kontrola git)
claude mcp add git https://github.com/cyanheads/git-mcp-server -t stdio -s user

# 3. Sentry MCP (production monitoring) - wymaga konta Sentry
claude mcp add sentry https://github.com/getsentry/sentry-mcp -t stdio -s user
```

---

## ⚠️ Uwagi Bezpieczeństwa

### Przed instalacją każdego serwera MCP:

1. **Sprawdź uprawnienia:**
   - Read-only → BEZPIECZNE
   - Write access → WYMAGA safeguards

2. **Testuj na test client (211779362):**
   - Każdy nowy serwer najpierw testuj
   - Sprawdź czy respektuje whitelisty

3. **Production monitoring (Sentry):**
   - Użyj osobnego workspace dla dev/staging/prod
   - Nigdy nie mieszaj danych testowych z produkcyjnymi

4. **Git/GitHub MCP:**
   - Ustaw branch protection rules
   - Używaj tylko na feature branches (nie na main)

---

## 🤝 Moja Rekomendacja

**Zainstaluj teraz (3 serwery):**
1. PostgreSQL MCP Pro - dla optymalizacji (PRIORYTET #1)
2. Git MCP - dla lepszej kontroli commitów
3. Sentry MCP - dla production monitoring (jeśli masz konto)

**Poczekaj z instalacją:**
- GitHub MCP - tylko gdy będziesz chciał automatyzować PRs
- SQL Analyzer - tylko przy skomplikowanych queries
- Debugg.AI - tylko jeśli Playwright nie wystarcza

**Nie instaluj:**
- Puppeteer (masz Playwright)
- Rubber Duck (zbędne)
- Memory Bank (masz CLAUDE.md)

---

## 📝 Następne Kroki

1. **Przejrzyj ten dokument**
2. **Zdecyduj które serwery chcesz**
3. **Powiedz mi:** "Zainstaluj TOP 3" lub wybierz własne
4. **Przetestuję każdy** z safeguardami
5. **Zaktualizujemy dokumentację**

---

*Ostatnia aktualizacja: 2025-10-08*
*Autor: Claude Code + Krystian*
