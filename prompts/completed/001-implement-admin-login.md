<objective>
Zaimplementuj prosty system logowania dla aplikacji Next.js z jednym kontem administratora.

Cel: Zabezpieczyć całą aplikację przed nieautoryzowanym dostępem. Tylko zalogowany admin może korzystać z systemu.
</objective>

<context>
Aplikacja Next.js 14 z App Router. Obecnie brak jakiegokolwiek systemu autoryzacji.

Dane logowania (hardcoded na start):
- Login: admin
- Hasło: web140569X$

Tech stack:
- Next.js 14 (App Router)
- Tailwind CSS
- Supabase (ale NIE używaj Supabase Auth - prostsze rozwiązanie)
</context>

<requirements>
1. Strona logowania `/login` z formularzem (email/login + hasło)
2. API endpoint `/api/auth/login` do weryfikacji credentials
3. API endpoint `/api/auth/logout` do wylogowania
4. Middleware Next.js chroniący WSZYSTKIE strony oprócz `/login`
5. Sesja oparta na HTTP-only cookie (bezpieczna)
6. Prosty JWT token w cookie (7 dni ważności)
7. Przekierowanie niezalogowanych na `/login`
8. Przekierowanie zalogowanych z `/login` na `/`
</requirements>

<implementation>
Struktura plików do stworzenia:

1. `app/login/page.tsx` - strona logowania
   - Formularz z polami: login, hasło
   - Obsługa błędów (nieprawidłowe dane)
   - Stylowanie Tailwind (proste, czytelne)

2. `app/api/auth/login/route.ts` - endpoint logowania
   - Weryfikacja credentials (admin / web140569X$)
   - Generowanie JWT z jose library
   - Ustawienie HTTP-only cookie
   - Zwrot success/error

3. `app/api/auth/logout/route.ts` - endpoint wylogowania
   - Usunięcie cookie sesji
   - Przekierowanie na /login

4. `middleware.ts` - ochrona tras
   - Sprawdzenie cookie z JWT
   - Weryfikacja tokenu
   - Przekierowanie na /login jeśli brak/nieważny token
   - Whitelist: /login, /api/auth/*

5. `lib/auth.ts` - helper functions
   - signToken(payload) - tworzenie JWT
   - verifyToken(token) - weryfikacja JWT
   - SECRET z process.env.JWT_SECRET lub fallback

Zależności do zainstalowania:
- jose (do JWT - działa w Edge Runtime)

Credentials przechowuj w kodzie jako stałe (na razie bez env vars dla prostoty).
</implementation>

<ui_design>
Strona logowania powinna być:
- Wycentrowana na stronie
- Prosty formularz w karcie z cieniem
- Logo/nazwa aplikacji na górze
- Przycisk "Zaloguj się"
- Komunikat o błędzie pod formularzem
- Spójny z resztą UI (Tailwind)
</ui_design>

<output>
Stwórz/zmodyfikuj następujące pliki:
- `./app/login/page.tsx`
- `./app/api/auth/login/route.ts`
- `./app/api/auth/logout/route.ts`
- `./middleware.ts`
- `./lib/auth.ts`

Zainstaluj wymagane zależności przez npm.
</output>

<verification>
Po implementacji:
1. Uruchom `npm run build` - sprawdź czy brak błędów
2. Przetestuj ręcznie:
   - Wejście na / bez logowania -> przekierowanie na /login
   - Logowanie z błędnym hasłem -> komunikat błędu
   - Logowanie z admin/web140569X$ -> przekierowanie na /
   - Dostęp do wszystkich stron po zalogowaniu
   - Wylogowanie -> przekierowanie na /login
</verification>

<success_criteria>
- Wszystkie strony chronione (oprócz /login)
- Logowanie działa z danymi admin/web140569X$
- Sesja utrzymuje się po odświeżeniu strony
- Cookie HTTP-only (bezpieczne)
- Build przechodzi bez błędów
</success_criteria>
