#!/bin/bash

# Fix multiline Supabase calls
# Pattern: await supabaseAdmin
#          .from('table')
# Should be: await supabaseAdmin()
#            .from('table')

echo "🔧 Fixing multiline Supabase calls..."

# Find all files with multiline pattern
files=$(grep -rl "await supabaseAdmin$\|await supabase$\|= supabaseAdmin$\|= supabase$" app/ lib/ --include="*.ts" --include="*.tsx" 2>/dev/null || true)

count=0

for file in $files; do
  if [ -f "$file" ]; then
    echo "  → Fixing $file"

    # Use sed to fix multiline patterns
    # Replace: await supabaseAdmin followed by newline and whitespace and .from
    sed -i 's/await supabaseAdmin$/await supabaseAdmin()/g' "$file"
    sed -i 's/await supabase$/await supabase()/g' "$file"
    sed -i 's/= supabaseAdmin$/= supabaseAdmin()/g' "$file"
    sed -i 's/= supabase$/= supabase()/g' "$file"

    count=$((count + 1))
  fi
done

echo ""
echo "✅ Fixed $count files"
