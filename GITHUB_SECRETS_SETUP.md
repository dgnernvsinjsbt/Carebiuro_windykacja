# 🔐 Supabase Edge Function Deployment Guide

## Step 1: Generate Supabase Access Token

To deploy Edge Functions, you need a Supabase Access Token:

1. Go to: https://supabase.com/dashboard/account/tokens
2. Click **"Generate new token"**
3. Name it: "CLI Deploy"
4. Copy the token (starts with `sbp_...`)
5. Save it somewhere safe - you'll only see it once!

---

## Step 2: Set Environment Variable Locally

In your terminal (Codespace or local machine):

```bash
export SUPABASE_ACCESS_TOKEN=sbp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Replace `sbp_xxx...` with your actual token.

---

## Step 3: Link Supabase Project

```bash
npx supabase link --project-ref gbylzdyyhnvmrgfgpfqh
```

**Project Details:**
- Project ID: `gbylzdyyhnvmrgfgpfqh`
- Project URL: https://gbylzdyyhnvmrgfgpfqh.supabase.co

---

## Step 4: Set Supabase Secrets (Edge Function Environment)

These environment variables will be available inside the Edge Function:

```bash
# Set all required environment variables
npx supabase secrets set FAKTUROWNIA_API_TOKEN="$FAKTUROWNIA_API_TOKEN"
npx supabase secrets set SMSPLANET_API_TOKEN="$SMSPLANET_API_TOKEN"
npx supabase secrets set SMSPLANET_FROM="Cbb-Office"
npx supabase secrets set SUPABASE_URL="https://gbylzdyyhnvmrgfgpfqh.supabase.co"
npx supabase secrets set SUPABASE_SERVICE_ROLE_KEY="$SUPABASE_SERVICE_ROLE_KEY"
```

**Verify secrets are set:**
```bash
npx supabase secrets list
```

---

## Step 5: Deploy the Edge Function

```bash
npx supabase functions deploy full-sync
```

**Expected output:**
```
Deploying function full-sync...
✓ Deployed function full-sync
Function URL: https://gbylzdyyhnvmrgfgpfqh.supabase.co/functions/v1/full-sync
```

---

## Step 6: Update GitHub Secrets

Now that the function is deployed, update GitHub Actions to use it.

Go to: https://github.com/YOUR_USERNAME/Carebiuro_windykacja/settings/secrets/actions

**Add these 2 new secrets:**

### Secret #1: SUPABASE_FUNCTION_URL
**Name**: `SUPABASE_FUNCTION_URL`

**Value**:
```
https://gbylzdyyhnvmrgfgpfqh.supabase.co/functions/v1
```

### Secret #2: SUPABASE_ANON_KEY
**Name**: `SUPABASE_ANON_KEY`

**Value**:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdieWx6ZHl5aG52bXJnZmdwZnFoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk1Nzc5OTksImV4cCI6MjA3NTE1Mzk5OX0.UX76Ip2vz7nwywqSy2IWZxpnMN3KMn0mxj4cIV4BGFs
```

**Keep existing secrets:**
- ✅ `SMSPLANET_API_TOKEN` (already exists)
- ⚠️ `VERCEL_URL` (not needed anymore but won't hurt to keep)

---

## Step 7: Test the Edge Function

### Test #1: Manual curl test

```bash
curl -X POST https://gbylzdyyhnvmrgfgpfqh.supabase.co/functions/v1/full-sync \
  -H "x-github-action: true" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdieWx6ZHl5aG52bXJnZmdwZnFoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk1Nzc5OTksImV4cCI6MjA3NTE1Mzk5OX0.UX76Ip2vz7nwywqSy2IWZxpnMN3KMn0mxj4cIV4BGFs"
```

**Expected response** (after ~10-15 minutes):
```json
{
  "success": true,
  "data": {
    "synced_clients": 123,
    "synced_invoices": 44000,
    "duration_seconds": 834.56
  }
}
```

**Expected SMS messages:**
1. "FULL SYNC STARTING..." (immediate)
2. "FULL SYNC COMPLETE! 44000 invoices, 123 clients in 834.56s" (after completion)

### Test #2: GitHub Actions manual trigger

```bash
gh workflow run nightly-sync.yml
```

Or via GitHub web UI:
1. Go to: Actions tab
2. Select "Nightly Full Sync (Production)"
3. Click "Run workflow" button
4. Watch the progress

---

## Step 8: Monitor Execution

### Supabase Logs
https://supabase.com/dashboard/project/gbylzdyyhnvmrgfgpfqh/functions/full-sync/logs

Watch for:
- ✅ Function invocation started
- ✅ STEP 1: Clearing data
- ✅ STEP 2: Streaming invoices (page by page)
- ✅ STEP 3: Fetching client notes
- ✅ STEP 4: Calculating totals
- ✅ Synchronization complete

### GitHub Actions Logs
https://github.com/YOUR_USERNAME/Carebiuro_windykacja/actions

Watch for:
- ✅ SMS sent (start)
- ✅ Trigger Full Sync step
- ✅ HTTP 200 response
- ✅ SMS sent (success)

---

## 🚨 Troubleshooting

### Error: "Access token not provided"
```bash
export SUPABASE_ACCESS_TOKEN=sbp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
npx supabase link --project-ref gbylzdyyhnvmrgfgpfqh
```

### Error: "Function not found"
```bash
# Verify deployment
npx supabase functions list

# Redeploy
npx supabase functions deploy full-sync
```

### Error: "Missing environment variable"
```bash
# List current secrets
npx supabase secrets list

# Set missing one
npx supabase secrets set VARIABLE_NAME="value"
```

### Error: HTTP 504 (timeout still happening)

If the Edge Function still times out after 15 minutes:
1. Check Supabase logs for the exact error
2. Verify Fakturownia API is responding
3. Consider reducing page size or adding retry logic

---

## 📋 Deployment Checklist

- [ ] Generate Supabase Access Token
- [ ] Set `SUPABASE_ACCESS_TOKEN` locally
- [ ] Link project: `npx supabase link --project-ref gbylzdyyhnvmrgfgpfqh`
- [ ] Set 5 Supabase secrets (FAKTUROWNIA_API_TOKEN, SMSPLANET_API_TOKEN, etc.)
- [ ] Deploy function: `npx supabase functions deploy full-sync`
- [ ] Add 2 GitHub secrets (SUPABASE_FUNCTION_URL, SUPABASE_ANON_KEY)
- [ ] Test with curl
- [ ] Test with GitHub Actions manual trigger
- [ ] Verify SMS notifications arrive
- [ ] Check Supabase database for synced data
- [ ] Monitor first automatic nightly run (00:00 CEST)

---

## 🎯 Success Criteria

✅ Edge Function deploys without errors
✅ Manual test completes in 10-15 minutes
✅ All 44k invoices synced to Supabase
✅ Corrective invoices (FK) excluded from totals
✅ SMS notifications received (start + success)
✅ No timeout errors
✅ GitHub Actions workflow succeeds
✅ Nightly cron runs at midnight (00:00 CEST)

---

**Created**: 2025-10-10
**Migration**: Vercel → Supabase Edge Functions
**Reason**: 60s Vercel timeout → 15min Supabase timeout
