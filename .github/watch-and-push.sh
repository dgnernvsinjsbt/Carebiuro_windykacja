#!/bin/bash
# Watch for changes and auto-push every 10 minutes

INTERVAL=${1:-600}  # Default: 10 minutes (600 seconds)

echo "👀 Watching for changes..."
echo "⏰ Auto-push interval: ${INTERVAL}s ($(($INTERVAL / 60)) minutes)"
echo "🛑 Press Ctrl+C to stop"
echo ""

while true; do
  # Sprawdź czy są zmiany
  if [[ -n $(git status -s) ]]; then
    echo "[$(date '+%H:%M:%S')] 📦 Zmiany wykryte - pushowanie..."

    git add .
    git commit -m "auto-save: $(date '+%Y-%m-%d %H:%M:%S')

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>" --no-verify

    git push origin main

    echo "✅ Zapisano!"
  else
    echo "[$(date '+%H:%M:%S')] ✓ Brak zmian"
  fi

  sleep $INTERVAL
done
