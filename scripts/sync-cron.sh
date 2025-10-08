#!/bin/bash
#
# Nightly Sync Cron Job
# Runs full synchronization from Fakturownia to Supabase
# Respects rate limits: 1 request/second, max 1000 requests/hour
#
# Add to crontab:
# 0 0 * * * /workspaces/Carebiuro_windykacja/scripts/sync-cron.sh

# Load environment variables
if [ -f /workspaces/Carebiuro_windykacja/.env.local ]; then
  export $(cat /workspaces/Carebiuro_windykacja/.env.local | grep -v '^#' | xargs)
fi

# Define app URL (adjust for production)
APP_URL="${APP_URL:-http://localhost:3000}"

# Log file
LOG_FILE="/var/log/carebiuro-sync.log"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Log start
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting nightly sync..." >> "$LOG_FILE"

# Call the sync API endpoint
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$APP_URL/api/sync" \
  -H "Content-Type: application/json" \
  -H "X-Cron-Secret: ${CRON_SECRET:-}" \
  --max-time 7200)

# Extract HTTP status code (last line)
HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | head -n -1)

# Log result
if [ "$HTTP_CODE" = "200" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Sync completed successfully: $BODY" >> "$LOG_FILE"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Sync failed with HTTP $HTTP_CODE: $BODY" >> "$LOG_FILE"
fi

# Optional: Send notification on failure
if [ "$HTTP_CODE" != "200" ]; then
  # Add your notification logic here (e.g., email, Slack, etc.)
  :
fi
