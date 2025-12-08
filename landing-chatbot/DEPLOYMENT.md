# Deployment Guide

## Quick Summary

This landing page is ready to deploy! All files are in `/workspaces/Carebiuro_windykacja/landing-chatbot/`

## Pre-Deployment Checklist

- ✅ Build passes: `npm run build` successful
- ✅ TypeScript: No errors
- ✅ Dev server: Works on port 3001
- ✅ Environment variables: Template provided (.env.example)
- ✅ Documentation: README.md complete

## Deployment to Vercel (Recommended)

### Step 1: Prepare Repository

Since this is a subfolder in a monorepo, you have two options:

**Option A: Extract to separate repo (Recommended)**

```bash
# Copy folder to new location
cp -r /workspaces/Carebiuro_windykacja/landing-chatbot /path/to/new/location

# Initialize new git repo
cd /path/to/new/location
git init
git add .
git commit -m "Initial commit - Polish Caregivers landing page"

# Push to GitHub
git remote add origin https://github.com/YOUR_USERNAME/landing-page.git
git push -u origin main
```

**Option B: Deploy from subfolder**

Vercel supports monorepo deployments. Just set:
- Root Directory: `landing-chatbot`
- Build Command: `npm run build`
- Output Directory: `.next`

### Step 2: Deploy on Vercel

1. Go to https://vercel.com
2. Click "New Project"
3. Import your Git repository
4. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `landing-chatbot` (if using Option B)
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`
   - **Install Command**: `npm install`

5. Add Environment Variables:
   ```
   GOOGLE_SHEETS_WEBHOOK_URL=https://script.google.com/macros/s/YOUR_ID/exec
   OPENAI_API_KEY=sk-your-api-key (if using AI chatbot)
   ```

6. Click "Deploy"

### Step 3: Post-Deployment

1. **Test the deployed site**:
   - Visit your Vercel URL (e.g., `https://your-project.vercel.app`)
   - Test form submission
   - Check FAQ accordion
   - Test mobile responsiveness

2. **Configure Custom Domain** (Optional):
   - In Vercel dashboard: Settings → Domains
   - Add your domain
   - Update DNS records as instructed

3. **Update Google Sheets Webhook** (if needed):
   - Make sure webhook accepts requests from your Vercel domain
   - Test form submission end-to-end

## Alternative Deployment Options

### Deploy to Netlify

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Deploy
cd landing-chatbot
netlify deploy --prod
```

Configure in `netlify.toml`:
```toml
[build]
  command = "npm run build"
  publish = ".next"

[[plugins]]
  package = "@netlify/plugin-nextjs"
```

### Deploy to Railway

1. Install Railway CLI: `npm install -g @railway/cli`
2. Run: `railway login`
3. Run: `railway init`
4. Run: `railway up`
5. Add environment variables in Railway dashboard

### Self-Hosted (VPS)

```bash
# On your server
git clone your-repo
cd landing-chatbot
npm install
npm run build

# Run with PM2
npm install -g pm2
pm2 start npm --name "landing-page" -- start
pm2 save
```

## Important Notes

### Turbopack Configuration

This project includes `turbopack.root` configuration in `next.config.ts`:

```typescript
turbopack: {
  root: __dirname,
}
```

This was added because the project sits in a subfolder. If you move it to a standalone repo, you can remove this configuration.

### Environment Variables

**Required**:
- `GOOGLE_SHEETS_WEBHOOK_URL`: For form submissions

**Optional**:
- `OPENAI_API_KEY`: Only if using AI chatbot feature

### Port Configuration

Default dev port: **3001** (configured in package.json)

Change it by editing `package.json`:
```json
"dev": "next dev -p YOUR_PORT"
```

## Troubleshooting Deployment

### Build fails with "middleware not found"

This happens if deployed from subfolder without turbopack.root config.

**Solution**: Ensure `next.config.ts` has:
```typescript
turbopack: {
  root: __dirname,
}
```

### Form submissions fail

Check:
1. Environment variable `GOOGLE_SHEETS_WEBHOOK_URL` is set
2. Google Apps Script is deployed with "Anyone" access
3. Check browser console for CORS errors

### Vercel build timeout

If build takes too long:
1. Upgrade Vercel plan (free tier has 45s limit)
2. Or optimize build by removing unused dependencies

### Cannot access on custom domain

1. Check DNS propagation (use https://dnschecker.org)
2. Wait up to 48 hours for DNS changes
3. Verify SSL certificate is active in Vercel

## Monitoring

After deployment, monitor:

1. **Vercel Analytics**: Built-in, shows traffic
2. **Google Sheets**: Check if form submissions arrive
3. **Vercel Logs**: Check for runtime errors

## Updating After Deployment

### Vercel Auto-Deploy

If connected to GitHub:
- Push to main branch → Vercel auto-deploys
- Open PR → Vercel creates preview deployment

### Manual Deploy

```bash
# Via Vercel CLI
vercel --prod

# Or push to Git
git add .
git commit -m "Update content"
git push
```

## Cost Estimate

### Vercel (Recommended)

- **Free Tier**: Perfect for this project
- **Bandwidth**: 100GB/month
- **Build Time**: 6000 minutes/month
- **Functions**: 100GB-hours/month

### OpenAI (if using chatbot)

- FAQ answers: **$0** (no API call)
- AI fallback: ~$0.01 per conversation
- Estimated: **$5-20/month** for moderate traffic

---

**Need Help?** Check README.md for detailed documentation.
