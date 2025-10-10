# 🚀 Vercel Production Environment Setup

## 📋 Overview

This guide shows how to switch email sending (E1/E2/E3 buttons) from **sandbox** to **production** Mailgun.

**Code already supports production mode** - no code changes needed! Just update environment variables.

---

## ✅ Step 1: Add Environment Variables to Vercel

### Option A: Via Vercel Dashboard (Recommended)

1. Go to: https://vercel.com/your-team/carebiuro-windykacja/settings/environment-variables

2. Add the following variables (click "Add" for each):

#### MAILGUN_API_KEY
```
20d3ec92a77dbe580b0e767333c8d4e4-556e0aa9-6c66fbc3
```
- Environment: **Production** ✓
- Environment: **Preview** ✓
- Environment: **Development** ✓

#### MAILGUN_DOMAIN
```
cbb-office.pl
```
- Environment: **Production** ✓
- Environment: **Preview** ✓
- Environment: **Development** ✓

#### MAILGUN_BASE_URL
```
https://api.eu.mailgun.net/v3
```
- Environment: **Production** ✓
- Environment: **Preview** ✓
- Environment: **Development** ✓

#### MAILGUN_FROM_EMAIL
```
Cbb-Office <noreply@cbb-office.pl>
```
- Environment: **Production** ✓
- Environment: **Preview** ✓
- Environment: **Development** ✓

#### EMAIL_MODE
```
production
```
- Environment: **Production** ✓
- Environment: **Preview** ✓
- Environment: **Development** ✓

#### EMAIL_SANDBOX_RECIPIENT
```
cbb.krd@gmail.com
```
- Environment: **Production** ✓
- Environment: **Preview** ✓
- Environment: **Development** ✓

---

### Option B: Via Vercel CLI

```bash
# Install Vercel CLI (if not already installed)
npm i -g vercel

# Login
vercel login

# Add environment variables
vercel env add MAILGUN_API_KEY production
# Paste: 20d3ec92a77dbe580b0e767333c8d4e4-556e0aa9-6c66fbc3

vercel env add MAILGUN_DOMAIN production
# Paste: cbb-office.pl

vercel env add MAILGUN_BASE_URL production
# Paste: https://api.eu.mailgun.net/v3

vercel env add MAILGUN_FROM_EMAIL production
# Paste: Cbb-Office <noreply@cbb-office.pl>

vercel env add EMAIL_MODE production
# Paste: production

vercel env add EMAIL_SANDBOX_RECIPIENT production
# Paste: cbb.krd@gmail.com
```

---

## ✅ Step 2: Redeploy Application

After adding environment variables, you need to redeploy:

### Option A: Via Dashboard
1. Go to: https://vercel.com/your-team/carebiuro-windykacja/deployments
2. Click on latest deployment
3. Click **"Redeploy"** button
4. Select **"Use existing Build Cache"** (faster)
5. Click **"Redeploy"**

### Option B: Via Git Push
```bash
git commit --allow-empty -m "chore: trigger redeploy for env vars"
git push
```

### Option C: Via CLI
```bash
vercel --prod
```

---

## ✅ Step 3: Verify Production Email

1. **Open Client Panel**: Go to production URL
2. **Find client** with email address
3. **Click E1 button** (first reminder email)
4. **Expected behavior**:
   - ✅ Email sent to **actual client email** (not cbb.krd@gmail.com)
   - ✅ From: `Cbb-Office <noreply@cbb-office.pl>`
   - ✅ Success toast: "E-mail wysłany"
   - ✅ Check Mailgun logs: https://app.mailgun.com/mg/sending/domains/cbb-office.pl/logs

---

## 🔍 How It Works

### Code Logic (lib/mailgun.ts:66-71)

```typescript
const isSandbox = process.env.EMAIL_MODE === 'sandbox';

// W sandbox mode, wszystkie emaile idą na EMAIL_SANDBOX_RECIPIENT
const actualRecipient = isSandbox
  ? process.env.EMAIL_SANDBOX_RECIPIENT!
  : recipientEmail;
```

### Sandbox Mode (EMAIL_MODE=sandbox)
- ❌ All emails redirect to: `cbb.krd@gmail.com`
- ❌ Uses sandbox domain: `sandboxde14172dbf8f4f76b1f5958087ceeae1.mailgun.org`
- ✅ Safe for testing

### Production Mode (EMAIL_MODE=production)
- ✅ Emails sent to actual client addresses
- ✅ Uses production domain: `cbb-office.pl`
- ✅ Ready for real use

---

## 📊 Expected Results

### Before (Sandbox):
```
To: cbb.krd@gmail.com
From: Carebiuro <postmaster@sandboxde14172dbf8f4f76b1f5958087ceeae1.mailgun.org>
Status: Delivered (sandbox only)
```

### After (Production):
```
To: actual-client@example.com
From: Cbb-Office <noreply@cbb-office.pl>
Status: Delivered (real email)
```

---

## 🧪 Test Checklist

After deployment:

- [ ] E1 button sends email to actual client address
- [ ] E2 button sends email to actual client address
- [ ] E3 button sends email to actual client address
- [ ] From address shows: `Cbb-Office <noreply@cbb-office.pl>`
- [ ] Success toast appears after send
- [ ] Mailgun dashboard shows delivery: https://app.mailgun.com/mg/sending/domains/cbb-office.pl/logs
- [ ] Email arrives in client inbox (check spam folder)

---

## ⚠️ Rollback Plan

If production emails fail, quickly rollback:

```bash
# Via CLI
vercel env add EMAIL_MODE production
# Type: sandbox

# Then redeploy
vercel --prod
```

Or via dashboard: Change `EMAIL_MODE` to `sandbox` and redeploy.

---

## 📝 Environment Variables Summary

| Variable | Production Value | Sandbox Value |
|----------|-----------------|---------------|
| `MAILGUN_API_KEY` | `20d3ec92a77dbe580b0e767333c8d4e4-556e0aa9-6c66fbc3` | `d0e88d4fce1cd0a1e31eedc863c93557-556e0aa9-107181aa` |
| `MAILGUN_DOMAIN` | `cbb-office.pl` | `sandboxde14172dbf8f4f76b1f5958087ceeae1.mailgun.org` |
| `MAILGUN_BASE_URL` | `https://api.eu.mailgun.net/v3` | `https://api.mailgun.net/v3` |
| `MAILGUN_FROM_EMAIL` | `Cbb-Office <noreply@cbb-office.pl>` | `Carebiuro <postmaster@sandbox...>` |
| `EMAIL_MODE` | `production` | `sandbox` |
| `EMAIL_SANDBOX_RECIPIENT` | `cbb.krd@gmail.com` | `cbb.krd@gmail.com` |

---

## 🎯 Next Steps

1. ✅ Add environment variables to Vercel
2. ✅ Redeploy application
3. ✅ Test E1/E2/E3 buttons
4. ✅ Monitor Mailgun delivery logs
5. ✅ Confirm client receives email

**Status**: Ready to deploy! 🚀
