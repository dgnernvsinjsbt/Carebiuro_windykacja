#!/bin/bash
# Auto-push using GitHub CLI

set -e  # Exit on error

# Kolory
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 GitHub Auto-Push${NC}"
echo ""

# 1. Sprawdź czy są zmiany
if [[ -z $(git status -s) ]]; then
  echo -e "${GREEN}✅ Brak zmian do zapisania${NC}"
  exit 0
fi

# 2. Pokaż zmiany
echo -e "${BLUE}📝 Znalezione zmiany:${NC}"
git status -s
echo ""

# 3. Pobierz opis od użytkownika (opcjonalnie)
if [ -z "$1" ]; then
  COMMIT_MSG="auto-save: $(date '+%Y-%m-%d %H:%M:%S')"
else
  COMMIT_MSG="$1"
fi

# 4. Commit
echo -e "${BLUE}💾 Commitowanie...${NC}"
git add .
git commit -m "$COMMIT_MSG

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 5. Push
echo -e "${BLUE}📤 Pushowanie do GitHub...${NC}"
git push origin main

# 6. Pokaż link do commita
COMMIT_HASH=$(git rev-parse --short HEAD)
REPO_URL=$(gh repo view --json url -q .url)
echo ""
echo -e "${GREEN}✅ Sukces!${NC}"
echo -e "${GREEN}🔗 Commit: ${REPO_URL}/commit/${COMMIT_HASH}${NC}"
echo ""
