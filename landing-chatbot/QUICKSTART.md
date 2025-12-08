# AI Chatbot - Quick Start Guide

## 🚀 Get Started in 3 Minutes

### Step 1: Install Dependencies (if not done)

```bash
npm install
```

### Step 2: Configure OpenAI API Key

```bash
# Copy .env.example to .env.local
cp .env.example .env.local

# Edit .env.local and add your OpenAI key
nano .env.local
```

Add this line:
```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

Get your key: https://platform.openai.com/api-keys

### Step 3: Start Dev Server

```bash
npm run dev
```

Server starts at: **http://localhost:3001**

### Step 4: Test the Chatbot

1. Open http://localhost:3001 in browser
2. Look for 💬 button in bottom-right corner
3. Click to open chat window
4. Try these questions:
   - "Czy moje zatrudnienie jest w pełni legalne?"
   - "Jakie ubezpieczenie jest zapewnione?"
   - "Jak długo trwa proces rejestracji?"

---

## 🧪 Quick Tests

### Test 1: Widget Loads
```bash
curl http://localhost:3001/api/widget.js | head -5
```
Should see JavaScript code starting with `(function () {`

### Test 2: FAQ Works
```bash
curl -X POST http://localhost:3001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Czy moje zatrudnienie jest w pełni legalne?"}'
```
Should stream back: "Tak, Twoje zatrudnienie jest w pełni legalne..."

### Test 3: Embed Works
Open `test-embed.html` in browser - widget should load!

---

## 📝 Edit FAQ

```bash
# Open FAQ file
nano public/faq.json

# Add new entry:
{
  "id": 11,
  "question": "Your new question?",
  "answer": "Your detailed answer here.",
  "keywords": ["keyword1", "keyword2", "variant"]
}

# Save and close - changes hot-reload automatically!
```

---

## 🌐 Embed on Other Sites

Add this to any HTML page:

```html
<script src="http://localhost:3001/api/widget.js"></script>
```

For production (after deploying to Vercel):
```html
<script src="https://your-domain.vercel.app/api/widget.js"></script>
```

---

## ✅ Verification

Run the automated check:

```bash
./verify-chatbot.sh
```

Should show all green checkmarks ✅

---

## 📚 Full Documentation

- **Setup Guide:** `CHATBOT_SETUP.md` (detailed instructions)
- **Implementation:** `IMPLEMENTATION_SUMMARY.md` (technical details)
- **General README:** `README.md` (project overview)

---

## 🆘 Troubleshooting

### Widget Not Showing?
1. Check browser console (F12)
2. Verify script tag: `<script src="/api/widget.js"></script>`
3. Restart dev server: `npm run dev`

### FAQ Not Matching?
1. Check keywords in `public/faq.json`
2. Add more variations/synonyms
3. Try exact FAQ question to verify it works

### OpenAI Error?
1. Verify `.env.local` has `OPENAI_API_KEY=sk-...`
2. Check key is valid at https://platform.openai.com
3. Restart server after adding key

---

## 🎯 Next Steps

1. ✅ Test locally (done above)
2. 📝 Edit FAQ with your own questions
3. 🎨 Customize widget colors (edit `public/widget.js`)
4. 🚀 Deploy to Vercel
5. 🌐 Embed on your website

---

**Need help?** See `CHATBOT_SETUP.md` for detailed docs!

**Ready to deploy?** See `DEPLOYMENT.md` for Vercel guide!
