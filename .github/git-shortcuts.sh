#!/bin/bash
# Użycie: source .github/git-shortcuts.sh

# Szybki backup z opisem
backup() {
  if [ -z "$1" ]; then
    MSG="checkpoint: $(date '+%Y-%m-%d %H:%M')"
  else
    MSG="$1"
  fi

  echo "📦 Zapisuję: $MSG"
  git add .
  git commit -m "$MSG"
  git push origin main
  echo "✅ Gotowe!"
}

# Zapisz wszystko natychmiast (bez opisu)
save() {
  echo "💾 Szybki zapis..."
  git add .
  git commit -m "quick save: $(date '+%H:%M:%S')"
  git push origin main
  echo "✅ Zapisano!"
}

# Cofnij do ostatniego commita (UWAGA: kasuje niezapisane zmiany!)
undo() {
  echo "⚠️  Czy na pewno chcesz cofnąć wszystkie niezapisane zmiany? (tak/nie)"
  read answer
  if [ "$answer" = "tak" ]; then
    git reset --hard HEAD
    echo "↩️  Cofnięto do ostatniego commita"
  else
    echo "❌ Anulowano"
  fi
}

# Cofnij do konkretnego commita
rollback() {
  git log --oneline -10
  echo ""
  echo "Podaj hash commita (np. ccd54b0) lub zostaw puste aby anulować:"
  read commit_hash

  if [ -z "$commit_hash" ]; then
    echo "❌ Anulowano"
    return
  fi

  echo "⚠️  Cofniesz się do $commit_hash. Kontynuować? (tak/nie)"
  read answer
  if [ "$answer" = "tak" ]; then
    git reset --hard $commit_hash
    git push origin main --force
    echo "↩️  Cofnięto do $commit_hash"
  else
    echo "❌ Anulowano"
  fi
}

# Pokaż ostatnie zmiany
changes() {
  echo "📊 Ostatnie commity:"
  git log --oneline -10 --decorate --graph
  echo ""
  echo "📝 Niezapisane zmiany:"
  git status -s
}

echo "✅ Załadowano skróty Git:"
echo "  backup [opis]  - zapisz zmiany z opisem"
echo "  save           - szybki zapis bez opisu"
echo "  undo           - cofnij niezapisane zmiany"
echo "  rollback       - wróć do poprzedniej wersji"
echo "  changes        - pokaż co się zmieniło"
