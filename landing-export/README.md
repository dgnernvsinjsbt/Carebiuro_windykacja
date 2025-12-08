# Polish Caregivers Germany - Landing Page

Landing page z formularzem kontaktowym dla usług legalnego zatrudnienia polskich opiekunek w Niemczech.

## 🚀 Szybki start

### Wymagania
- Node.js 18+
- npm lub yarn

### Instalacja

```bash
# 1. Zainstaluj zależności
npm install

# 2. Skopiuj plik .env.example do .env.local
cp .env.example .env.local

# 3. Edytuj .env.local i uzupełnij URL webhooka Google Sheets
# Zastąp PLACEHOLDER_WEBHOOK_ID swoim rzeczywistym ID

# 4. Uruchom serwer deweloperski
npm run dev
```

Aplikacja będzie dostępna pod adresem: **http://localhost:3001**

## 📁 Struktura projektu

```
landing-chatbot/
├── app/
│   ├── api/
│   │   └── contact/
│   │       └── route.ts         # API endpoint formularza
│   ├── layout.tsx               # Root layout z Toaster
│   ├── page.tsx                 # Główna strona (Hero + Form + FAQ)
│   └── globals.css              # Style globalne
├── components/
│   ├── Hero.tsx                 # Sekcja hero z video placeholder
│   ├── ContactForm.tsx          # Formularz kontaktowy (client-side)
│   └── FAQ.tsx                  # FAQ accordion
├── lib/
│   ├── validation.ts            # Zod schema walidacji
│   └── utils.ts                 # Helper functions
├── .env.local                   # Zmienne środowiskowe (gitignored)
├── .env.example                 # Template env vars
└── README.md                    # Ta dokumentacja
```

## ⚙️ Konfiguracja

### 1. Google Sheets Webhook

Aby formularz działał, musisz utworzyć Google Apps Script webhook:

#### Krok po kroku:

1. **Utwórz nowy Google Sheet**
   - Otwórz https://sheets.google.com
   - Utwórz nowy arkusz
   - Nazwij kolumny: `Name`, `Email`, `Phone`, `Timestamp`

2. **Dodaj Google Apps Script**
   - W menu kliknij: `Extensions` → `Apps Script`
   - Usuń domyślny kod i wklej:

```javascript
function doPost(e) {
  try {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    const data = JSON.parse(e.postData.contents);

    sheet.appendRow([
      data.name,
      data.email,
      data.phone,
      data.timestamp
    ]);

    return ContentService
      .createTextOutput(JSON.stringify({ success: true }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    return ContentService
      .createTextOutput(JSON.stringify({ success: false, error: error.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
```

3. **Deploy jako Web App**
   - Kliknij `Deploy` → `New deployment`
   - Typ: `Web app`
   - Execute as: `Me`
   - Who has access: `Anyone`
   - Kliknij `Deploy`
   - Skopiuj **Web app URL** (będzie wyglądać jak: `https://script.google.com/macros/s/ABC123.../exec`)

4. **Zaktualizuj .env.local**
   ```bash
   GOOGLE_SHEETS_WEBHOOK_URL=https://script.google.com/macros/s/TU_WKLEJ_SWOJE_ID/exec
   ```

5. **Zrestartuj serwer dev**
   ```bash
   npm run dev
   ```

## 🎨 Personalizacja

### Zmiana kolorów

Edytuj `/app/globals.css` lub komponenty bezpośrednio:
- Primary (granatowy): `#1e3a8a`
- Secondary (złoty): `#ca8a04`

### Edycja FAQ

Otwórz `/components/FAQ.tsx` i edytuj tablicę `faqData`:

```typescript
const faqData: FAQItem[] = [
  {
    question: 'Twoje pytanie?',
    answer: 'Twoja odpowiedź...',
  },
  // Dodaj więcej pytań tutaj
];
```

### Zmiana treści Hero

Edytuj `/components/Hero.tsx`:
- Nagłówki
- Tekst przycisku CTA
- Link przycisku (domyślnie: `#contact`)

### Zmiana video placeholder

W pliku `/components/Hero.tsx` znajdź sekcję `{/* Video Placeholder */}` i:
- Zastąp `<div>` przez `<iframe>` lub `<video>`
- Lub dodaj link do YouTube/Vimeo

Przykład YouTube embed:
```tsx
<iframe
  className="w-full aspect-video rounded-lg"
  src="https://www.youtube.com/embed/TWOJE_VIDEO_ID"
  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
  allowFullScreen
></iframe>
```

## 🚀 Deployment na Vercel

### Krok po kroku:

1. **Push code do GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/TWOJE_KONTO/landing-page.git
   git push -u origin main
   ```

2. **Połącz z Vercel**
   - Zaloguj się na https://vercel.com
   - Kliknij `New Project`
   - Import z GitHub
   - Wybierz swoje repo

3. **Skonfiguruj Environment Variables**
   - W ustawieniach projektu w Vercel
   - Dodaj: `GOOGLE_SHEETS_WEBHOOK_URL`
   - Wklej swój webhook URL

4. **Deploy**
   - Vercel automatycznie zbuduje i wdroży aplikację
   - Każdy push do `main` uruchomi nowy deployment

### Custom Domain

W Vercel dashboard:
1. Settings → Domains
2. Dodaj swoją domenę
3. Skonfiguruj DNS records (Vercel poda instrukcje)

## 🧪 Testowanie

### Lokalne testy

1. Uruchom dev server: `npm run dev`
2. Otwórz: http://localhost:3001
3. Sprawdź:
   - ✅ Hero section renderuje się poprawnie
   - ✅ Formularz ma walidację (spróbuj wysłać puste pola)
   - ✅ FAQ accordion expand/collapse działa
   - ✅ Responsywność (mobile/desktop)

### Test formularza

1. Wypełnij formularz prawidłowymi danymi
2. Kliknij "Wyślij zapytanie"
3. Sprawdź:
   - Toast notification pojawia się
   - Dane trafiają do Google Sheets
   - Konsola nie pokazuje błędów

### Build test

```bash
npm run build
```

Jeśli build przechodzi bez błędów TypeScript → gotowe do deployment.

## 📝 Scripts

```bash
npm run dev      # Uruchom dev server (port 3001)
npm run build    # Build produkcyjny
npm run start    # Start produkcyjnego serwera
npm run lint     # Uruchom ESLint
```

## 🔧 Troubleshooting

### Formularz nie wysyła danych

**Problem**: Toast pokazuje błąd, dane nie trafiają do Sheets

**Rozwiązanie**:
1. Sprawdź `.env.local` - czy webhook URL jest poprawny?
2. Sprawdź Google Apps Script deployment:
   - Execute as: `Me`
   - Who has access: `Anyone`
3. Sprawdź konsolę przeglądarki i terminal (server logs)
4. Testuj webhook bezpośrednio:
   ```bash
   curl -X POST YOUR_WEBHOOK_URL \
     -H "Content-Type: application/json" \
     -d '{"name":"Test","email":"test@test.com","phone":"123456789","timestamp":"2025-01-01"}'
   ```

### Port 3001 jest zajęty

**Rozwiązanie**: Zmień port w `package.json`:
```json
"dev": "next dev -p 3002"
```

### Build errors

**Problem**: TypeScript errors podczas `npm run build`

**Rozwiązanie**:
1. Sprawdź wszystkie komponenty
2. Upewnij się, że wszystkie importy są poprawne
3. Sprawdź czy wszystkie `@/` aliasy działają

### Toast notifications nie działają

**Problem**: Brak powiadomień po submit formularza

**Rozwiązanie**:
1. Sprawdź czy `<Toaster />` jest w `app/layout.tsx`
2. Sprawdź czy `react-hot-toast` jest zainstalowany
3. Zrestartuj dev server

## 📦 Zależności

### Production
- `next`: ^16.0.7 - Framework React
- `react`: ^19.2.0 - React library
- `react-dom`: ^19.2.0 - React DOM
- `react-hot-toast`: ^2.6.0 - Toast notifications
- `zod`: ^4.1.13 - Walidacja schema

### Development
- `typescript`: ^5 - TypeScript
- `tailwindcss`: ^4 - Utility-first CSS
- `eslint`: ^9 - Linter

## 🤖 AI Chatbot System

### Architektura

```
┌─────────────────┐
│  Widget (JS)    │ ──┐
│  Floating UI    │   │
└─────────────────┘   │
                      ▼
┌─────────────────────────────────┐
│  API /api/chat (Next.js Edge)   │
│  1. Check FAQ matches            │
│  2. If no match → OpenAI         │
│  3. Stream response              │
└─────────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
┌──────────────────┐    ┌────────────────┐
│  FAQ Database    │    │  OpenAI API    │
│  (faq.json)      │    │  (gpt-4o)      │
└──────────────────┘    └────────────────┘
```

### Jak działa

1. **Użytkownik pisze wiadomość** → Widget wysyła do `/api/chat`
2. **FAQ Matcher** → Sprawdza dopasowanie słów kluczowych w `public/faq.json`
3. **Natychmiastowa odpowiedź** → Jeśli znaleziono FAQ, zwraca bez OpenAI
4. **AI Fallback** → Jeśli brak dopasowania, wywołuje OpenAI z kontekstem FAQ
5. **Streaming Response** → Wyświetla odpowiedź słowo po słowie

### Edycja bazy wiedzy FAQ

Edytuj `public/faq.json`:

```json
[
  {
    "id": 1,
    "question": "Twoje pytanie?",
    "answer": "Szczegółowa odpowiedź (2-4 zdania).",
    "keywords": ["słowo1", "słowo2", "synonim"]
  }
]
```

**Wskazówki**:
- Dodaj wiele słów kluczowych (synonimy, błędy)
- Odpowiedzi zwięzłe (2-4 zdania)
- Używaj języka polskiego
- Testuj wpisując podobne frazy

### Osadzanie widgetu na innych stronach

Dodaj ten tag `<script>` do dowolnej strony HTML:

```html
<script src="https://your-domain.vercel.app/api/widget.js"></script>
```

**Custom API URL** (opcjonalnie):

```html
<script>
  window.CHATBOT_API_URL = 'https://twoj-api.com/api/chat';
</script>
<script src="https://your-domain.vercel.app/api/widget.js"></script>
```

Widget pojawi się jako floating button w prawym dolnym rogu.

### Konfiguracja OpenAI

1. **Pobierz klucz API**:
   - Przejdź do https://platform.openai.com/api-keys
   - Utwórz nowy klucz API
   - Skopiuj klucz (zaczyna się od `sk-`)

2. **Dodaj do `.env.local`**:
   ```bash
   OPENAI_API_KEY=sk-your-api-key-here
   ```

3. **Zrestartuj serwer**:
   ```bash
   npm run dev
   ```

### Koszty OpenAI

- **Model**: GPT-4o
- **Koszt input**: ~$2.50 / 1M tokens
- **Koszt output**: ~$10 / 1M tokens
- **Typowa konwersacja**: ~500 tokens = $0.01

**FAQ znacząco redukuje koszty** - większość pytań obsługiwana bez OpenAI!

### Test widgetu

**Lokalnie**:
1. `npm run dev`
2. Otwórz http://localhost:3001
3. Kliknij floating button (💬)
4. Wyślij wiadomość: "Czy moja praca jest legalna?"

**Na innej stronie (test embed)**:

Stwórz `test.html`:
```html
<!DOCTYPE html>
<html>
<head>
  <title>Test Chatbot</title>
</head>
<body>
  <h1>Test Embed</h1>
  <script src="http://localhost:3001/api/widget.js"></script>
</body>
</html>
```

Otwórz plik w przeglądarce → widget powinien działać!

## 🎯 Features

✅ **Responsywny design** - Mobile-first, działa na wszystkich urządzeniach
✅ **Walidacja formularza** - Zod schema + real-time feedback
✅ **Toast notifications** - User feedback po każdej akcji
✅ **FAQ Accordion** - Smooth animations
✅ **Google Sheets integration** - Webhook zapisujący dane
✅ **AI Chatbot** - OpenAI + FAQ knowledge base
✅ **Embeddable Widget** - Cross-domain script tag
✅ **Streaming Responses** - Real-time AI answers
✅ **SEO friendly** - Meta tags + semantic HTML
✅ **TypeScript** - Type safety
✅ **Tailwind CSS** - Utility-first styling
✅ **Production ready** - Gotowe do deploy na Vercel

## 📄 Licencja

Kod jest własnością klienta. Full ownership - możesz robić z nim co chcesz.

## 🤝 Wsparcie

Jeśli masz pytania lub potrzebujesz pomocy:
1. Sprawdź sekcję Troubleshooting powyżej
2. Sprawdź dokumentację Next.js: https://nextjs.org/docs
3. Sprawdź dokumentację Vercel: https://vercel.com/docs

---

**Gotowe do startu!** 🚀
Pamiętaj: zastąp `PLACEHOLDER_WEBHOOK_ID` w `.env.local` swoim rzeczywistym webhook URL.
