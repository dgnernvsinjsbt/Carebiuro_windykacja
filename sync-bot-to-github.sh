#!/bin/bash

# Sync bingx-trading-bot folder to separate GitHub repo
# Usage: ./sync-bot-to-github.sh [commit-message]

set -e

COMMIT_MSG="${1:-Update bot from main repo}"
BOT_FOLDER="bingx-trading-bot"

echo "========================================="
echo "SYNCING BOT TO GITHUB REPO"
echo "========================================="
echo ""

# Check if we're in the right directory
if [ ! -d "$BOT_FOLDER" ]; then
    echo "❌ Error: $BOT_FOLDER folder not found!"
    exit 1
fi

# Check if bot-repo remote exists
if ! git remote | grep -q "bot-repo"; then
    echo "Adding bot-repo remote..."
    git remote add bot-repo https://github.com/dgnernvsinjsbt/bingx-trading-bot.git
fi

echo "📦 Creating subtree split of $BOT_FOLDER..."
SPLIT_BRANCH=$(git subtree split --prefix=$BOT_FOLDER main)

if [ -z "$SPLIT_BRANCH" ]; then
    echo "❌ Error: Failed to create subtree split"
    exit 1
fi

echo "✅ Split created: $SPLIT_BRANCH"
echo ""

echo "🚀 Pushing to bot-repo..."
git push bot-repo $SPLIT_BRANCH:main --force

echo ""
echo "========================================="
echo "✅ SYNC COMPLETE!"
echo "========================================="
echo ""
echo "The bot repo has been updated:"
echo "https://github.com/dgnernvsinjsbt/bingx-trading-bot"
echo ""
echo "You can now pull on Hostinger."
