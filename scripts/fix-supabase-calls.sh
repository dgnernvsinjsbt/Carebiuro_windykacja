#!/bin/bash

# Script to fix all supabase/supabaseAdmin calls to use function invocation
# Changes: supabase.from() -> supabase().from()
# Changes: supabaseAdmin.from() -> supabaseAdmin().from()

echo "🔧 Fixing Supabase function calls..."

# Find all TypeScript and TSX files
files=$(find app lib -type f \( -name "*.ts" -o -name "*.tsx" \) ! -path "*/node_modules/*" ! -path "*/.next/*")

count=0

for file in $files; do
  # Check if file contains supabase usage (but not already fixed)
  if grep -q "supabase\\.from\|supabaseAdmin\\.from\|supabase\\.auth\|supabaseAdmin\\.auth\|supabase\\.storage\|supabaseAdmin\\.storage\|supabase\\.rpc\|supabaseAdmin\\.rpc" "$file" 2>/dev/null; then
    # Skip if already has () after supabase
    if ! grep -q "supabase()\\.from\|supabaseAdmin()\\.from" "$file" 2>/dev/null; then
      echo "  → Fixing $file"

      # Use perl for more reliable replacement
      # Replace: await supabase.from -> await supabase().from
      perl -pi -e 's/await supabase\./await supabase()./g' "$file"
      perl -pi -e 's/await supabaseAdmin\./await supabaseAdmin()./g' "$file"

      # Replace: const { ... } = supabase.from -> const { ... } = supabase().from
      perl -pi -e 's/= supabase\./= supabase()./g' "$file"
      perl -pi -e 's/= supabaseAdmin\./= supabaseAdmin()./g' "$file"

      # Replace: return supabase.from -> return supabase().from
      perl -pi -e 's/return supabase\./return supabase()./g' "$file"
      perl -pi -e 's/return supabaseAdmin\./return supabaseAdmin()./g' "$file"

      # Replace any remaining standalone: supabase.from/auth/storage/rpc
      perl -pi -e 's/([^(])supabase\.(from|auth|storage|rpc|functions)/$1supabase().$2/g' "$file"
      perl -pi -e 's/([^(])supabaseAdmin\.(from|auth|storage|rpc|functions)/$1supabaseAdmin().$2/g' "$file"

      count=$((count + 1))
    fi
  fi
done

echo ""
echo "✅ Fixed $count files"
echo ""
echo "Running build to verify..."
