#!/bin/bash

# Sync bingx-trading-bot folder to separate GitHub repo
# Usage: ./sync-bot-to-github.sh [commit-message]

set -e

COMMIT_MSG="${1:-Update bot from main repo}"
BOT_FOLDER="bingx-trading-bot"
BOT_REPO="https://github.com/dgnernvsinjsbt/bingx-trading-bot.git"
TEMP_DIR="/tmp/bot-repo-sync-$$"

# Load token from .env file if exists
if [ -f ".env.bot-sync" ]; then
    source .env.bot-sync
fi

echo "========================================="
echo "SYNCING BOT TO GITHUB REPO"
echo "========================================="
echo ""

# Check if we're in the right directory
if [ ! -d "$BOT_FOLDER" ]; then
    echo "❌ Error: $BOT_FOLDER folder not found!"
    exit 1
fi

echo "📦 Creating temporary clone..."
# Use PAT for authentication
GITHUB_TOKEN="${GITHUB_BOT_TOKEN:-$GITHUB_TOKEN}"
git clone "https://${GITHUB_TOKEN}@github.com/dgnernvsinjsbt/bingx-trading-bot.git" "$TEMP_DIR"

echo "🔄 Copying files..."
rsync -av --delete \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='logs/' \
    "$BOT_FOLDER/" "$TEMP_DIR/"

cd "$TEMP_DIR"

# Check if there are changes
if git diff --quiet && git diff --cached --quiet; then
    echo ""
    echo "✅ No changes to sync - bot repo is already up to date!"
    cd - > /dev/null
    rm -rf "$TEMP_DIR"
    exit 0
fi

echo "📝 Committing changes..."
git add -A
git commit -m "$COMMIT_MSG"

echo "🚀 Pushing to GitHub..."
# Use PAT for push
git remote set-url origin "https://${GITHUB_TOKEN}@github.com/dgnernvsinjsbt/bingx-trading-bot.git"
git push origin main

cd - > /dev/null
rm -rf "$TEMP_DIR"

echo ""
echo "========================================="
echo "✅ SYNC COMPLETE!"
echo "========================================="
echo ""
echo "The bot repo has been updated:"
echo "https://github.com/dgnernvsinjsbt/bingx-trading-bot"
echo ""
echo "You can now pull on Hostinger:"
echo "  ssh hostinger"
echo "  cd bingx-trading-bot"
echo "  git pull"
echo "  # Restart bot if needed"
