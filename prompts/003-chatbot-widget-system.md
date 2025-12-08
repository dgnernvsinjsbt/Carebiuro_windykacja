<objective>
Stwórz self-hosted chatbot AI z OpenAI, embeddable widget i FAQ knowledge base.

Cel: Chatbot widget (floating button) który można osadzić na dowolnej stronie przez <script> tag. Streaming odpowiedzi z OpenAI + baza wiedzy FAQ.
</objective>

<context>
Dodaj do projektu `./landing-chatbot/` (z poprzedniego prompta).

Chatbot będzie używany na:
- Landing page projektu
- Inne strony klienta (multi-domain embed)

Tematyka: Polish Caregivers w Niemczech - odpowiedzi na pytania o Gewerbe, legalność pracy, ubezpieczenia.

Tech stack:
- Backend: Next.js API Route (streaming)
- OpenAI: gpt-4o (streaming)
- Widget: Vanilla JavaScript (no React - dla cross-domain embed)
- FAQ: JSON file (łatwo edytowalne)
</context>

<requirements>
1. **FAQ Knowledge Base (`public/faq.json`)**
   - JSON array z pytaniami i odpowiedziami
   - Struktura:
     ```json
     [
       {
         "id": 1,
         "question": "Czy moje zatrudnienie jest w pełni legalne?",
         "answer": "Tak, pełne ubezpieczenie zdrowotne i społeczne...",
         "keywords": ["legalne", "legalność", "prawnie", "gewerbe"]
       },
       ...
     ]
     ```
   - 8-10 pytań o: Gewerbe, ubezpieczenia, legalność, proces zatrudnienia
   - Dobrze napisane, pomocne odpowiedzi (2-4 zdania każda)

2. **Chat API Endpoint (`app/api/chat/route.ts`)**
   - POST endpoint
   - Request body: `{ message: string, conversationHistory?: Message[] }`
   - Logika:
     a) Szukaj exact match w FAQ (keyword search)
     b) Jeśli match: zwróć FAQ answer (instant)
     c) Jeśli brak: wywołaj OpenAI z FAQ context
   - OpenAI streaming (Server-Sent Events)
   - System prompt:
     ```
     Jesteś asystentem dla polskich opiekunek w Niemczech.
     Pomagasz z pytaniami o Gewerbe, legalną pracę, ubezpieczenia.
     Odpowiadaj po polsku, zwięźle, pomocnie.

     Baza wiedzy FAQ:
     {faq_json}
     ```
   - Response: streaming text (SSE format)

3. **Chat Widget - Frontend (`public/widget.js`)**
   - Standalone vanilla JavaScript (NO React/frameworks)
   - Floating button (bottom-right):
     - Icon: chat bubble
     - Badge z "Napisz do nas"
     - Kliknięcie: otwiera chat window

   - Chat Window (overlay):
     - Header: "Czat z konsultantem" + close button
     - Messages list (auto-scroll to bottom)
     - Input field + send button
     - Loading state (typing indicator)
     - Error handling

   - Styling:
     - Inline CSS (no external dependencies)
     - Z-index: 9999 (ponad wszystkim)
     - Responsywny (mobile: fullscreen, desktop: 400px x 600px)
     - Kolory: granatowy (#1e3a8a) + złoty (#ca8a04)

   - API Integration:
     - Fetch POST `/api/chat`
     - Stream parsing (ReadableStream)
     - Display messages w czasie rzeczywistym

4. **Widget Embed Script (`app/api/widget.js/route.ts`)**
   - GET endpoint zwracający `widget.js` content
   - Headers: `Content-Type: application/javascript`
   - CORS: `Access-Control-Allow-Origin: *`
   - Klient embeduje przez:
     ```html
     <script src="https://your-domain.vercel.app/api/widget.js"></script>
     ```

5. **OpenAI Integration (`lib/openai.ts`)**
   - OpenAI client setup
   - Function: `streamChatCompletion(messages, faqContext)`
   - Model: gpt-4o
   - Temperature: 0.7
   - Max tokens: 500
   - Stream: true

6. **FAQ Matcher (`lib/faq-matcher.ts`)**
   - Function: `findFAQMatch(userMessage: string, faq: FAQ[])`
   - Keyword matching (case-insensitive)
   - Fuzzy matching (opcjonalnie - Levenshtein distance)
   - Return: FAQ answer lub null

7. **Environment Variables**
   - `.env.local`:
     ```
     OPENAI_API_KEY=sk-...
     ```
   - `.env.example` - template

8. **Dokumentacja**
   - Dodaj do `README.md`:
     - Jak edytować FAQ (`public/faq.json`)
     - Jak embedować widget na innych stronach
     - OpenAI setup (API key)
     - Koszty (gpt-4o pricing)
</requirements>

<implementation>
Rozszerz projekt:

```
landing-chatbot/
├── app/
│   ├── api/
│   │   ├── chat/
│   │   │   └── route.ts        # Chat API (OpenAI streaming)
│   │   └── widget.js/
│   │       └── route.ts        # Serve widget script
├── lib/
│   ├── openai.ts               # OpenAI client
│   └── faq-matcher.ts          # FAQ search logic
├── public/
│   ├── faq.json                # Baza wiedzy (edytowalna)
│   └── widget.js               # Widget standalone bundle
├── scripts/
│   └── build-widget.sh         # Build widget (opcjonalnie)
```

Widget.js structure (vanilla JS):
```javascript
(function() {
  // Config
  const API_URL = 'https://your-domain.vercel.app/api/chat';

  // Create UI
  function createChatButton() { ... }
  function createChatWindow() { ... }

  // API
  async function sendMessage(message) {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });

    const reader = response.body.getReader();
    // Stream parsing...
  }

  // Init
  window.addEventListener('DOMContentLoaded', () => {
    document.body.appendChild(createChatButton());
  });
})();
```

Przykładowe FAQ (8 pytań):
1. Czy moje zatrudnienie jest w pełni legalne?
2. Jakie ubezpieczenie jest zapewnione?
3. Co obejmuje wsparcie w ramach Gewerbe?
4. Czy mam zapewnioną opiekę medyczną w Niemczech?
5. Jak wygląda proces legalizacji pobytu i pracy?
6. Gdzie mogę uzyskać pomoc w nagłych wypadkach?
7. Jakie są koszty ubezpieczenia?
8. Jak długo trwa proces rejestracji Gewerbe?

Dependencies:
- `openai` - OpenAI SDK
- `ai` - Vercel AI SDK (opcjonalnie, dla streaming helpers)
</implementation>

<widget_behavior>
Zachowanie widgetu:
1. Page load → floating button pojawia się (bottom-right, 20px margin)
2. Click button → chat window slide-in animation
3. User type message → disable input, show "typing..."
4. API response streaming → wyświetlaj słowo po słowie
5. Error → show "Przepraszamy, wystąpił błąd. Spróbuj ponownie."
6. Close button → slide-out animation, hide window

Mobile:
- Fullscreen overlay (100vw x 100vh)
- Input fixed na dole
- Messages scroll area w środku

Desktop:
- 400px x 600px window
- Position: fixed, bottom-right
- Shadow, rounded corners
</widget_behavior>

<output>
Rozszerz projekt `./landing-chatbot/`:
- Wszystkie wymienione pliki
- Zaktualizuj README.md (dodaj sekcję Chatbot)
- Test widgetu lokalnie
- Dodaj widget do landing page (app/page.tsx)

Commit z opisem: "feat: Add AI chatbot widget with OpenAI integration"
</output>

<verification>
1. Uruchom dev server
2. Sprawdź `/api/chat`:
   - POST z message → streaming response
   - FAQ match → instant answer
   - OpenAI fallback → stream z OpenAI
3. Sprawdź widget:
   - Floating button widoczny
   - Click → otwiera chat
   - Wysłanie wiadomości → streaming odpowiedź
   - Close button działa
   - Responsywność mobile/desktop
4. Test embed:
   - Utwórz test.html z `<script src="http://localhost:3000/api/widget.js"></script>`
   - Otwórz w przeglądarce → widget działa
5. Edytuj `public/faq.json` → odpowiedzi się zmieniają
</verification>

<success_criteria>
- Chat API z OpenAI streaming
- FAQ knowledge base (8-10 pytań)
- Widget vanilla JS (embeddable)
- Floating button + chat window
- Multi-domain support (CORS)
- Mobile + desktop responsive
- README dokumentacja (FAQ edit, embed)
- Test embed działa
- Build przechodzi bez błędów
</success_criteria>
