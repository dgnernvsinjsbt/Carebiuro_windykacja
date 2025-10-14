# 🔐 Environment Variables Setup Guide

## 📋 Overview

This project uses environment variables for configuration. There are two files:

1. **`.env.example`** - Template with placeholder values (committed to git)
2. **`.env`** - Your actual secrets (ignored by git, never commit!)

---

## 🚀 Quick Start

### 1. Copy the template
```bash
cp .env.example .env
```

### 2. Fill in your actual values
Edit `.env` and replace placeholder values with real credentials.

---

## 🔑 Required Variables

### Supabase (Database)
Get from: https://supabase.com/dashboard → Your Project → Settings → API

```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**How to get keys:**
```bash
# Using Supabase CLI (if you have access token)
SUPABASE_ACCESS_TOKEN="your-token" npx supabase projects list
SUPABASE_ACCESS_TOKEN="your-token" npx supabase projects api-keys --project-ref your-ref
```

### Application URL
```bash
# Local development
APP_URL=http://localhost:3000

# GitHub Codespaces
APP_URL=https://your-codespace-name-3000.app.github.dev

# Production
APP_URL=https://yourdomain.com
```

### Cron Secret
Generate with:
```bash
openssl rand -base64 32
```

Then add to `.env`:
```bash
CRON_SECRET=Lli262dzW8NC96oPLS1XKjfRB5flGDJOHqg4gC9AexM=
```

---

## 📦 Optional Variables

### Fakturownia API
For invoice synchronization:
```bash
FAKTUROWNIA_API_TOKEN=your-api-token
FAKTUROWNIA_ACCOUNT=your-account-name
```

### SMS Planet
For SMS notifications:
```bash
SMSPLANET_API_TOKEN=Bearer your-token
SMSPLANET_FROM=YourCompany
```

### Mailgun
For email sending:
```bash
MAILGUN_API_KEY=your-key
MAILGUN_DOMAIN=mg.yourdomain.com
MAILGUN_FROM_EMAIL=noreply@yourdomain.com
MAILGUN_SANDBOX_MODE=false
```

### n8n Webhooks
For workflow automation:
```bash
N8N_WEBHOOK_EMAIL=https://your-n8n.com/webhook/email
N8N_WEBHOOK_SMS=https://your-n8n.com/webhook/sms
N8N_WEBHOOK_WHATSAPP=https://your-n8n.com/webhook/whatsapp
```

---

## 🔒 Security Best Practices

### ✅ DO:
- Keep `.env` file local (already in `.gitignore`)
- Use strong random secrets for `CRON_SECRET`
- Store production secrets in Vercel/hosting platform
- Rotate keys regularly
- Use different keys for dev/staging/production

### ❌ DON'T:
- Never commit `.env` to git
- Don't share keys in Slack/Discord/etc
- Don't hardcode secrets in code
- Don't use the same keys across environments
- Don't store secrets in `.env.example`

---

## 🌍 Environment-Specific Setup

### Local Development
```bash
cp .env.example .env
# Edit .env with your local/development credentials
npm run dev
```

### GitHub Codespaces
```bash
# .env is already configured for your codespace
# Just update the APP_URL if needed
APP_URL=https://$(echo $CODESPACE_NAME)-3000.app.github.dev
```

### Vercel Deployment
1. Go to: https://vercel.com/your-project/settings/environment-variables
2. Add all variables from `.env.example`
3. Use production values (not dev/test keys!)
4. Set scope: Production / Preview / Development

### Other Platforms
Consult your platform's documentation for setting environment variables:
- Netlify: Site settings → Environment variables
- Railway: Variables tab
- Heroku: Settings → Config Vars

---

## 🧪 Testing Configuration

### Check if variables are loaded
```bash
# Start dev server
npm run dev

# You should see: "- Environments: .env"
```

### Verify Supabase connection
```bash
# Generate types (tests database connection)
SUPABASE_ACCESS_TOKEN="your-token" npx supabase gen types typescript --linked
```

### Test cron endpoint
```bash
curl -H "Authorization: Bearer YOUR_CRON_SECRET" \
  https://your-domain.com/api/cron/sync
```

---

## 📝 Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | ✅ Yes | - | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ✅ Yes | - | Public anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ Yes | - | Secret service role key |
| `APP_URL` | ✅ Yes | `http://localhost:3000` | Application URL |
| `CRON_SECRET` | ✅ Production | - | Random secret for cron jobs |
| `FAKTUROWNIA_API_TOKEN` | ⚠️ Optional | - | Invoice API token |
| `FAKTUROWNIA_ACCOUNT` | ⚠️ Optional | - | Invoice account name |
| `SMSPLANET_API_TOKEN` | ⚠️ Optional | - | SMS API token |
| `SMSPLANET_FROM` | ⚠️ Optional | `YourCompany` | SMS sender name |
| `MAILGUN_API_KEY` | ⚠️ Optional | - | Email API key |
| `N8N_WEBHOOK_*` | ⚠️ Optional | - | Webhook URLs |

---

## 🆘 Troubleshooting

### Error: "Missing NEXT_PUBLIC_SUPABASE_URL environment variable"
**Solution**: Make sure `.env` file exists and contains the variable
```bash
# Check if .env exists
ls -la .env

# Verify it's loaded
npm run dev
# Look for: "- Environments: .env"
```

### Error: "Failed to connect to Supabase"
**Solutions**:
1. Check if URL is correct (should end with `.supabase.co`)
2. Verify anon key is valid (starts with `eyJh...`)
3. Test connection:
```bash
curl https://your-project.supabase.co/rest/v1/
```

### Changes not taking effect
**Solution**: Restart dev server
```bash
# Kill current server (Ctrl+C)
npm run dev
```

### Works locally but fails in production
**Solutions**:
1. Check environment variables are set on hosting platform
2. Verify production keys (not dev keys!)
3. Check `APP_URL` points to correct domain
4. Ensure `CRON_SECRET` matches what you're using

---

## 📚 Related Documentation

- [Supabase Environment Variables](https://supabase.com/docs/guides/getting-started/local-development#environment-variables)
- [Next.js Environment Variables](https://nextjs.org/docs/basic-features/environment-variables)
- [Vercel Environment Variables](https://vercel.com/docs/concepts/projects/environment-variables)

---

## 🔄 Migration from Old Setup

If you had credentials in `.env.example`:

1. **Backup** your current `.env.example`:
```bash
cp .env.example .env.example.backup
```

2. **Move secrets** to `.env`:
```bash
# Copy real values from .env.example.backup to .env
cp .env.example .env
# Edit .env with actual credentials
```

3. **Update** `.env.example` with placeholders:
```bash
# Already done! ✅
```

4. **Verify** `.env` is ignored:
```bash
git status
# .env should NOT appear in changes
```

---

**Last Updated**: 2025-10-14
**Maintained By**: Development Team
