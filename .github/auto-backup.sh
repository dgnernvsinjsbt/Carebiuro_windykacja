#!/bin/bash
# Auto-backup script - zapisuje zmiany co 10 minut

while true; do
  # Sprawdź czy są zmiany
  if [[ -n $(git status -s) ]]; then
    echo "🔄 [$(date '+%Y-%m-%d %H:%M:%S')] Wykryto zmiany, zapisuję..."

    git add .
    git commit -m "auto-backup: $(date '+%Y-%m-%d %H:%M:%S')" --no-verify
    git push origin main

    echo "✅ Zapisano!"
  else
    echo "✓ [$(date '+%H:%M:%S')] Brak zmian"
  fi

  # Czekaj 10 minut
  sleep 600
done
