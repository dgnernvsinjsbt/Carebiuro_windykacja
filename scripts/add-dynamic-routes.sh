#!/bin/bash

# Script to add dynamic route configuration to all API routes
# This prevents Next.js from trying to statically evaluate routes at build time

find app/api -name "route.ts" -type f | while read -r file; do
  # Check if file already has "export const dynamic"
  if grep -q "export const dynamic" "$file"; then
    echo "✓ Skipping $file (already has dynamic export)"
  else
    echo "→ Processing $file"

    # Find the first line with "export async function" or "export function"
    line_number=$(grep -n "^export \(async \)\?function" "$file" | head -1 | cut -d: -f1)

    if [ -n "$line_number" ]; then
      # Insert before the function export
      sed -i "${line_number}i\\
// Force dynamic rendering - don't evaluate at build time\\
export const dynamic = 'force-dynamic';\\
export const runtime = 'nodejs';\\
" "$file"
      echo "  ✓ Added dynamic config"
    else
      echo "  ✗ Could not find export function"
    fi
  fi
done

echo ""
echo "✓ Done! All API routes now have dynamic configuration."
