# Bot Sync Workflow

Automatically sync the `bingx-trading-bot` folder to the separate GitHub repo.

## Usage

From the root of this repo, simply run:

```bash
./sync-bot-to-github.sh
```

Or with a custom commit message:

```bash
./sync-bot-to-github.sh "Add new strategy"
```

## How It Works

1. **Clones** the bot repo to `/tmp`
2. **Copies** all files from `bingx-trading-bot/` folder
3. **Commits** changes with your message
4. **Pushes** to https://github.com/dgnernvsinjsbt/bingx-trading-bot

## After Syncing

Deploy to Hostinger:

```bash
ssh your-hostinger-server
cd bingx-trading-bot
git pull
# Restart the bot if needed
sudo systemctl restart trading-engine
```

## Token Security

- Your GitHub token is stored in `.env.bot-sync` (not tracked by git)
- The script automatically loads it when you run sync
- Never commit `.env.bot-sync` to the repository

## Workflow Summary

**Before:**
1. Edit bot code in `bingx-trading-bot/` folder
2. Commit to main repo
3. Manually copy files to bot repo
4. Commit and push to bot repo
5. SSH to Hostinger and pull

**Now:**
1. Edit bot code in `bingx-trading-bot/` folder
2. Run `./sync-bot-to-github.sh "Your message"`
3. SSH to Hostinger and pull

Saves ~5 minutes every deployment! 🚀
