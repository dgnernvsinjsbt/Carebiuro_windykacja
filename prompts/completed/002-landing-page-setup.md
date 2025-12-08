<objective>
Stwórz nowy projekt Next.js 14 z landing page i formularzem kontaktowym dla "Polish Caregivers - Germany".

Cel: MVP landing page z formularzem wysyłającym dane na webhook (Google Sheets). Kod przekazywalny klientowi (full ownership).
</objective>

<context>
Nowy standalone projekt (POZA tym repo Carebiuro_windykacja).

Tematyka: Usługi dla polskich opiekunek w Niemczech (Gewerbe, legalna praca, ubezpieczenia).

Tech stack:
- Next.js 14 (App Router)
- Tailwind CSS
- TypeScript
- Hosting: Vercel (free tier)

Referencja design: Landing page z hero section, formularz kontaktowy, FAQ accordion.
</context>

<requirements>
1. **Nowy projekt Next.js**
   - Utwórz w `./landing-chatbot/` (subfolder w obecnym repo)
   - `npx create-next-app@latest landing-chatbot`
   - TypeScript, Tailwind, App Router

2. **Dev Server Config**
   - Zmień port w package.json: `"dev": "next dev -p 3001"`
   - (Żeby nie kolidować z główną aplikacją na porcie 3000)

3. **Landing Page (`app/page.tsx`)**
   - Hero section:
     - Nagłówek: "TWOJE BEZPIECZEŃSTWO - Polish Caregivers Germany"
     - Podnagłówek: "Legalne i pewne zatrudnienie w Niemczech"
     - Placeholder dla video (może być prostokąt z tekstem "Video placeholder")
     - CTA button: "Sprawdź oferty pracy"

   - Formularz kontaktowy (sekcja poniżej hero):
     - Nagłówek: "Zapytaj o szczegóły"
     - Pola: imię i nazwisko, email, numer telefonu
     - Walidacja (Zod schema)
     - Przycisk "Wyślij zapytanie"
     - Toast notifications (react-hot-toast)

   - FAQ Section (accordion):
     - Nagłówek: "Najczęściej zadawane pytania"
     - 5-6 pytań o Gewerbe/pracę w DE (placeholder treść)
     - Accordion expand/collapse

4. **API Endpoint - Formularz (`app/api/contact/route.ts`)**
   - POST endpoint
   - Walidacja danych (Zod)
   - Wyślij na webhook Google Sheets:
     ```
     POST https://script.google.com/macros/s/PLACEHOLDER_WEBHOOK_ID/exec
     Body: { name, email, phone, timestamp }
     ```
   - Zwróć success/error

5. **Responsywność**
   - Mobile-first design
   - Breakpoints: sm, md, lg, xl
   - Formularz 1-kolumnowy mobile, 2-kolumnowy desktop

6. **Styling**
   - Paleta kolorów:
     - Primary: #1e3a8a (granatowy - jak na screenie)
     - Secondary: #ca8a04 (złoty - przyciski)
     - Background: white
   - Tailwind utilities
   - Shadows, rounded corners
   - Smooth transitions

7. **Environment Variables**
   - `.env.local`:
     ```
     GOOGLE_SHEETS_WEBHOOK_URL=https://script.google.com/macros/s/PLACEHOLDER/exec
     ```
   - `.env.example` - template dla klienta

8. **Dokumentacja**
   - `README.md`:
     - Setup instructions
     - Environment variables
     - Deployment (Vercel)
     - Jak edytować FAQ
     - Jak zmienić webhook URL
</requirements>

<implementation>
Struktura projektu:

```
landing-chatbot/
├── app/
│   ├── page.tsx              # Landing page
│   ├── layout.tsx            # Root layout
│   ├── globals.css           # Tailwind globals
│   └── api/
│       └── contact/
│           └── route.ts      # Contact form API
├── components/
│   ├── Hero.tsx              # Hero section
│   ├── ContactForm.tsx       # Formularz
│   └── FAQ.tsx               # FAQ accordion
├── lib/
│   ├── validation.ts         # Zod schemas
│   └── utils.ts              # Helper functions
├── .env.local                # Env vars (gitignored)
├── .env.example              # Template
├── README.md                 # Dokumentacja
├── tailwind.config.ts        # Tailwind config
└── package.json
```

FAQ placeholder content (przykładowe pytania):
1. "Czy moje zatrudnienie jest w pełni legalne?"
2. "Jakie ubezpieczenie jest zapewnione?"
3. "Co obejmuje wsparcie w ramach Gewerbe?"
4. "Czy mam zapewnioną opiekę medyczną w Niemczech?"
5. "Jak wygląda proces legalizacji pobytu i pracy?"

Dependencies do zainstalowania:
- `react-hot-toast` - notifications
- `zod` - validation
- `lucide-react` - icons (opcjonalnie)
</implementation>

<styling_reference>
Bazuj na pokazanym screenie:
- Granatowy gradient w hero (#1e3a8a → ciemniejszy)
- Złote akcenty na przyciskach (#ca8a04)
- Białe tło dla formularza i FAQ
- Card z shadow dla formularza
- Accordion z border i padding
</styling_reference>

<output>
Stwórz nowy projekt:
- Katalog: `./landing-chatbot/` (w obecnym repo jako subfolder)
- Wszystkie wymienione pliki
- README z pełną dokumentacją

NIE modyfikuj innych plików w repo (app/, components/, etc.) - tylko landing-chatbot/ folder!
</output>

<verification>
1. `cd landing-chatbot && npm run dev`
2. Otwórz http://localhost:3001 (port 3001 żeby nie kolidować z główną aplikacją)
3. Sprawdź:
   - Landing page renderuje się poprawnie
   - Formularz ma walidację
   - Submit formularza wywołuje API (nawet jeśli webhook fail - to OK, placeholder)
   - FAQ accordion działa (expand/collapse)
   - Responsywność mobile/desktop
4. `npm run build` - brak błędów TypeScript
</verification>

<success_criteria>
- Nowy projekt Next.js w `./landing-chatbot/`
- Landing page z hero, formularz, FAQ
- API endpoint `/api/contact` z walidacją
- Responsywny design (mobile-first)
- Toast notifications
- README z dokumentacją
- Build przechodzi bez błędów
- Gotowe do deploy na Vercel
</success_criteria>
