# Supabase Edge Function Deployment Guide

## Overview
This guide explains how to deploy the `full-sync` Supabase Edge Function to replace the Vercel-based sync that was timing out.

**Why Supabase Edge Functions?**
- ✅ Free tier with 15-minute timeout (vs Vercel Hobby 60s)
- ✅ Handles 44k invoice sync (~10-15 minutes)
- ✅ No cost increase
- ✅ Reliable execution via GitHub Actions cron

## Prerequisites

1. **Supabase CLI installed**
   ```bash
   npm install -g supabase
   ```

2. **Supabase project linked**
   ```bash
   supabase login
   supabase link --project-ref YOUR_PROJECT_REF
   ```

3. **Environment variables set in Supabase Dashboard**
   Go to: Settings → Edge Functions → Secrets

   Add these secrets:
   ```
   SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
   FAKTUROWNIA_API_TOKEN=your-fakturownia-api-token
   SMSPLANET_FROM=Cbb-Office
   SMSPLANET_API_TOKEN=your-smsplanet-api-token
   ```

## Deployment Steps

### 1. Deploy the Edge Function

```bash
# Deploy the full-sync function
supabase functions deploy full-sync

# Verify deployment
supabase functions list
```

### 2. Get the Function URL

After deployment, you'll get a URL like:
```
https://YOUR_PROJECT_REF.supabase.co/functions/v1/full-sync
```

### 3. Update GitHub Secrets

Go to: GitHub repo → Settings → Secrets and variables → Actions

Add these secrets:
- `SUPABASE_FUNCTION_URL`: `https://YOUR_PROJECT_REF.supabase.co/functions/v1`
- `SUPABASE_ANON_KEY`: Your Supabase anon key (from Supabase Dashboard → Settings → API)

### 4. Test the Function Manually

```bash
# Test with curl
curl -X POST https://YOUR_PROJECT_REF.supabase.co/functions/v1/full-sync \
  -H "x-github-action: true" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_SUPABASE_ANON_KEY"
```

Expected response:
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

### 5. Test GitHub Actions Workflow

```bash
# Trigger manual test
gh workflow run nightly-sync.yml
```

Or use the GitHub Actions UI:
1. Go to Actions tab
2. Select "Nightly Full Sync (Production)"
3. Click "Run workflow"

## Monitoring

### Check Logs in Supabase

1. Go to: Functions → full-sync → Logs
2. Watch real-time execution
3. Check for errors or timeouts

### Check SMS Notifications

You should receive 3 SMS messages:
1. **Start**: "FULL SYNC STARTING..."
2. **Success**: "FULL SYNC COMPLETE! 44000 invoices, 123 clients in 834.56s"
3. **Failure** (only if error): "FULL SYNC FAILED: [error message]"

## Troubleshooting

### Function timeout (still getting 504)

The Edge Function timeout is 15 minutes by default. If it still times out:

1. **Check pagination rate limit**
   - Currently: 1 req/sec (1000ms delay)
   - Try reducing to 500ms if Fakturownia allows

2. **Split into batches**
   - Process clients in chunks
   - Use multiple function calls

### Missing environment variables

```bash
# List all secrets
supabase secrets list

# Set missing secret
supabase secrets set FAKTUROWNIA_API_TOKEN=your-token
```

### SMS not sending

Check:
1. SMS sender name is "Cbb-Office" (registered)
2. SMSPLANET_API_TOKEN is correct
3. Phone number format: +48536214664

### Database connection issues

Verify:
1. SUPABASE_URL is correct
2. SUPABASE_SERVICE_ROLE_KEY has correct permissions
3. RLS policies allow service role access

## Rollback Plan

If Supabase Edge Function fails, you can rollback to Vercel:

1. **Upgrade to Vercel Pro** ($20/month) for 15-minute timeout
2. **Revert GitHub Actions workflow**:
   ```yaml
   - name: Trigger Full Sync
     run: |
       curl -X POST ${{ secrets.VERCEL_URL }}/api/sync \
         -H "x-github-action: true"
   ```

## Architecture Diagram

```
┌─────────────────────┐
│  GitHub Actions     │  Cron: 00:00 CEST daily
│  (Free)             │  Timeout: 30 minutes
└──────────┬──────────┘
           │ HTTP POST with x-github-action header
           ↓
┌─────────────────────┐
│ Supabase Edge Func  │  Runtime: Deno
│ full-sync           │  Timeout: 15 minutes
│ (Free)              │  Memory: 512MB
└──────────┬──────────┘
           │
           ├──→ Fakturownia API (fetch invoices + clients)
           ├──→ Supabase Database (save data)
           └──→ SMS Planet API (send notifications)
```

## Success Criteria

✅ Nightly sync runs at midnight (00:00 CEST)
✅ Completes in ~10-15 minutes without timeout
✅ SMS notifications arrive for start/success/fail
✅ All 44k invoices synced
✅ Corrective invoices (FK) excluded from totals
✅ No cost increase (still on free tier)

## Next Steps

After successful deployment:

1. ✅ Monitor first nightly run
2. ✅ Verify data integrity in Supabase
3. ✅ Confirm SMS notifications
4. ✅ Remove old Vercel cron job from `vercel.json`
5. ✅ Document any issues or improvements needed
