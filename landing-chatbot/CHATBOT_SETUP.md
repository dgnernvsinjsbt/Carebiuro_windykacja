# AI Chatbot System - Setup Guide

## Overview

Self-hosted AI chatbot with OpenAI integration, embeddable on any website via script tag.

**Key Features:**
- ✅ FAQ Knowledge Base (instant answers, no OpenAI cost)
- ✅ OpenAI GPT-4o fallback for complex questions
- ✅ Streaming responses (real-time word-by-word display)
- ✅ Embeddable widget (cross-domain support)
- ✅ Mobile + Desktop responsive
- ✅ Multi-language support (currently Polish)

## Files Created

```
landing-chatbot/
├── lib/
│   ├── faq-matcher.ts          # FAQ keyword matching + Levenshtein distance
│   └── openai.ts               # OpenAI client + streaming helpers
├── app/api/
│   ├── chat/
│   │   └── route.ts            # Main chat endpoint (FAQ + OpenAI)
│   └── widget.js/
│       └── route.ts            # Serve widget.js with CORS
├── public/
│   ├── faq.json                # Knowledge base (10 Q&A)
│   └── widget.js               # Standalone vanilla JS widget
├── test-embed.html             # Test page for widget embed
├── .env.example                # Updated with OPENAI_API_KEY
└── README.md                   # Updated with chatbot docs
```

## Quick Start

### 1. Install Dependencies

Already installed: `openai` package

### 2. Configure OpenAI API Key

```bash
# Edit .env.local
OPENAI_API_KEY=sk-your-actual-key-here
```

Get your key: https://platform.openai.com/api-keys

### 3. Start Dev Server

```bash
npm run dev
```

Server runs on: http://localhost:3001

### 4. Test the Widget

**Option A: On Landing Page**

Open http://localhost:3001 - widget should appear as floating button (💬)

**Option B: Standalone Test Page**

Open `test-embed.html` in browser directly - widget loads from localhost

## How It Works

### Architecture Flow

```
User Message
     ↓
Widget (public/widget.js)
     ↓
POST /api/chat
     ↓
┌─────────────────────┐
│ FAQ Matcher         │
│ (keyword search)    │
└─────────────────────┘
     ↓
 Match found?
     ↓
  ┌──NO──┐  YES
  ↓      ↓
OpenAI   FAQ Answer
  ↓      ↓
Stream Response
     ↓
Widget Display
```

### FAQ Matching

**File:** `lib/faq-matcher.ts`

**Logic:**
1. Normalize user message (lowercase, remove diacritics)
2. Extract keywords from message
3. Compare with FAQ keywords using:
   - Exact match (highest score)
   - Word-level match
   - Fuzzy match (Levenshtein distance > 0.8)
4. If score > 0.6 threshold → return FAQ answer
5. Else → call OpenAI

**Example:**

```typescript
User: "Czy moja praca jest legalna?"
Keywords: ["praca", "legalna"]
FAQ #1 keywords: ["legalne", "legalność", "prawnie", "gewerbe"]
Match score: 2.8 (above threshold)
Result: Instant FAQ answer (no OpenAI call)
```

### OpenAI Fallback

**File:** `lib/openai.ts`

When no FAQ match:
1. Prepare system prompt with ALL FAQ context
2. Call GPT-4o with streaming
3. Stream response word-by-word to widget

**Cost Optimization:**
- FAQ answers are FREE (no API call)
- Only complex/unknown questions use OpenAI
- Average cost: ~$0.01 per AI conversation

## Editing FAQ

**File:** `public/faq.json`

### Structure

```json
{
  "id": 1,
  "question": "Full question text",
  "answer": "Detailed answer (2-4 sentences)",
  "keywords": ["keyword1", "synonym", "typo", "variant"]
}
```

### Best Practices

1. **Add Many Keywords**
   - Include synonyms
   - Common typos
   - Variations (singular/plural)
   - Related terms

2. **Keep Answers Concise**
   - 2-4 sentences ideal
   - Avoid walls of text
   - End with action/next step

3. **Test Your Questions**
   - Type similar phrases in chat
   - Check if FAQ matches
   - Adjust keywords if needed

### Example FAQ Entry

```json
{
  "id": 11,
  "question": "Ile kosztuje rejestracja Gewerbe?",
  "answer": "Rejestracja Gewerbe kosztuje około 20-60 EUR opłaty urzędowej. My pokrywamy te koszty za Ciebie i pomagamy w całym procesie. Dodatkowo oferujemy wsparcie księgowe bez dodatkowych opłat.",
  "keywords": [
    "koszt",
    "koszty",
    "cena",
    "ile",
    "opłata",
    "płacić",
    "gewerbe rejestracja",
    "założenie",
    "ile kosztuje"
  ]
}
```

## Embedding Widget

### On Same Domain (Landing Page)

Already added in `app/layout.tsx`:

```html
<script src="/api/widget.js" async></script>
```

### On External Sites

Add to any HTML page:

```html
<script src="https://your-domain.vercel.app/api/widget.js"></script>
```

### Custom Configuration

```html
<script>
  // Optional: Override API URL
  window.CHATBOT_API_URL = 'https://custom-api.com/api/chat';
</script>
<script src="https://your-domain.vercel.app/api/widget.js"></script>
```

## Widget Behavior

### Desktop
- 400px × 600px window
- Bottom-right corner (20px margin)
- Slide-in animation
- Rounded corners + shadow

### Mobile
- Fullscreen overlay
- Input fixed at bottom
- Scrollable messages

### Interactions
1. **Floating Button**: Click to open chat
2. **Send Message**: Type + press Enter or click "Wyślij"
3. **Streaming**: AI response appears word-by-word
4. **Close**: Click × or click outside window

## API Endpoints

### POST /api/chat

**Request:**
```json
{
  "message": "User question here",
  "conversationHistory": [
    { "role": "user", "content": "Previous message" },
    { "role": "assistant", "content": "Previous response" }
  ]
}
```

**Response:**
```
Content-Type: text/plain; charset=utf-8
Streaming response (word by word)
```

**CORS:** Enabled (`Access-Control-Allow-Origin: *`)

### GET /api/widget.js

**Response:**
```javascript
Content-Type: application/javascript
// Full widget.js code
```

**CORS:** Enabled for cross-domain embedding

## Testing Checklist

### 1. FAQ Matching

Test these exact questions (should get instant answers):

- [x] "Czy moje zatrudnienie jest w pełni legalne?"
- [x] "Jakie ubezpieczenie jest zapewnione?"
- [x] "Co obejmuje wsparcie w ramach Gewerbe?"
- [x] "Jak długo trwa proces rejestracji Gewerbe?"

### 2. OpenAI Fallback

Test custom questions (should call OpenAI):

- [ ] "Jakie są różnice między Gewerbe a Minijob?"
- [ ] "Czy mogę pracować zdalnie z Polski?"

**Note:** Requires `OPENAI_API_KEY` in `.env.local`

### 3. Widget UI

- [x] Floating button visible
- [x] Click opens chat window
- [x] Smooth slide-in animation
- [x] Messages display with correct styling
- [x] Input field works
- [x] Send button functional
- [x] Close button works
- [x] Responsive on mobile (fullscreen)

### 4. Streaming

- [x] Responses appear word-by-word
- [x] Auto-scroll to bottom
- [x] Loading indicator (typing dots)
- [x] No lag/jank

### 5. Embed Test

Open `test-embed.html` in browser:

- [x] Widget loads from localhost
- [x] Works on external HTML file
- [x] CORS headers allow cross-domain

## Deployment (Vercel)

### 1. Push to GitHub

```bash
git add .
git commit -m "feat: Add AI chatbot widget with OpenAI integration"
git push
```

### 2. Deploy on Vercel

1. Go to https://vercel.com
2. Import GitHub repo
3. Add Environment Variable:
   ```
   OPENAI_API_KEY=sk-your-key-here
   ```
4. Deploy

### 3. Update Widget URLs

After deployment, update embed code with production URL:

```html
<script src="https://your-app.vercel.app/api/widget.js"></script>
```

## Cost Estimation

### OpenAI Pricing (GPT-4o)

- **Input**: $2.50 / 1M tokens
- **Output**: $10 / 1M tokens
- **Average conversation**: ~500 tokens = $0.01

### Monthly Estimate

**Scenario: 1000 users/month**

- 70% questions handled by FAQ = FREE
- 30% questions use OpenAI = 300 × $0.01 = $3

**Total:** ~$3-5/month for 1000 users

## Troubleshooting

### FAQ Not Matching

**Problem:** Question should match but doesn't

**Solution:**
1. Check keywords in `public/faq.json`
2. Add more variations
3. Lower threshold in `lib/faq-matcher.ts` (line 95):
   ```typescript
   export function findFAQMatch(
     userMessage: string,
     faqs: FAQ[],
     threshold: number = 0.6 // Try 0.5 for looser matching
   )
   ```

### OpenAI Error

**Problem:** "OpenAI API key not configured"

**Solution:**
1. Check `.env.local` has `OPENAI_API_KEY=sk-...`
2. Restart dev server: `npm run dev`
3. Verify key is valid at https://platform.openai.com/api-keys

### Widget Not Loading

**Problem:** Floating button doesn't appear

**Solution:**
1. Check console for errors
2. Verify script tag: `<script src="/api/widget.js"></script>`
3. Test endpoint: `curl http://localhost:3001/api/widget.js`
4. Check CORS headers in response

### Streaming Not Working

**Problem:** Response appears all at once, not word-by-word

**Solution:**
1. Check `createTextStream()` in `lib/openai.ts`
2. Verify `ReadableStream` is supported in browser
3. Test with FAQ question first (simpler streaming)

## Maintenance

### Adding New FAQ

1. Edit `public/faq.json`
2. Add new entry with incremented ID
3. Include 5-10 keywords
4. Test with similar phrases
5. No restart needed (hot reload)

### Updating OpenAI Model

Edit `lib/openai.ts`:

```typescript
const stream = await openai.chat.completions.create({
  model: 'gpt-4o', // Change to gpt-4-turbo, gpt-3.5-turbo, etc.
  // ...
});
```

### Customizing Widget Styles

Edit `public/widget.js` → `injectStyles()` function:

```javascript
const PRIMARY_COLOR = '#1e3a8a'; // Change colors here
const ACCENT_COLOR = '#ca8a04';
```

## Support

If issues persist:

1. Check server logs: `npm run dev` output
2. Check browser console: F12 → Console tab
3. Test API directly: `curl -X POST http://localhost:3001/api/chat ...`
4. Verify FAQ.json is valid JSON: `cat public/faq.json | jq`

## Next Steps

- [ ] Deploy to Vercel
- [ ] Add analytics (track FAQ hits vs OpenAI calls)
- [ ] Add user feedback buttons (👍/👎)
- [ ] Implement conversation history persistence
- [ ] Add admin panel for FAQ management
- [ ] Multi-language support (English/German)

---

**Documentation complete!** 🚀

Start with: `npm run dev` → Open http://localhost:3001 → Click 💬
