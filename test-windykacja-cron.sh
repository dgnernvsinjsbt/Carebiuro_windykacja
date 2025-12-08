#!/bin/bash
# Test script for windykacja cron endpoints

CRON_SECRET="hcJjp0xd01HPm13M9unMl/BDo/gprjNNUDEz4M/1JTM="
BASE_URL="https://carebiuro-windykacja.vercel.app"

echo "========================================"
echo "Testing Windykacja Cron Endpoints"
echo "========================================"
echo ""

# Test auto-send-initial
echo "1. Testing auto-send-initial..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/windykacja/auto-send-initial" \
  -H "Content-Type: application/json" \
  -H "X-Cron-Secret: $CRON_SECRET" \
  --max-time 30)

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "Status: $HTTP_CODE"
echo "Response: $BODY"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ auto-send-initial: SUCCESS"
else
  echo "❌ auto-send-initial: FAILED (HTTP $HTTP_CODE)"
fi

echo ""
echo "========================================"
echo "Summary:"
echo "========================================"

if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ All tests passed! GitHub Action should work."
else
  echo "❌ Tests failed. Check:"
  echo "   1. Vercel deployment is complete"
  echo "   2. CRON_SECRET in Vercel matches GitHub secret"
  echo "   3. Middleware changes are deployed"
fi
