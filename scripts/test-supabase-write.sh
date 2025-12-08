#!/bin/bash

SUPABASE_URL=$(grep NEXT_PUBLIC_SUPABASE_URL .env | cut -d '=' -f2 | tr -d '"' | tr -d "'")
SERVICE_KEY=$(grep SUPABASE_SERVICE_ROLE_KEY .env | cut -d '=' -f2 | tr -d '"' | tr -d "'")

echo "Testing Supabase READ access..."
curl -s "${SUPABASE_URL}/rest/v1/clients?id=eq.113906677&select=id,note,name" \
  -H "apikey: ${SERVICE_KEY}" \
  -H "Authorization: Bearer ${SERVICE_KEY}"

echo ""
echo ""
echo "Testing Supabase WRITE access..."
curl -X PATCH "${SUPABASE_URL}/rest/v1/clients?id=eq.113906677" \
  -H "apikey: ${SERVICE_KEY}" \
  -H "Authorization: Bearer ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d '{"note": "[WINDYKACJA]true[/WINDYKACJA]"}'
