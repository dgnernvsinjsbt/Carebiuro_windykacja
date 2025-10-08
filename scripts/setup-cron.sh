#!/bin/bash
#
# Setup Cron Job for Nightly Sync
# Run this script once to install the cron job
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNC_SCRIPT="$SCRIPT_DIR/sync-cron.sh"

# Make sync script executable
chmod +x "$SYNC_SCRIPT"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$SYNC_SCRIPT"; then
  echo "✅ Cron job already exists"
  crontab -l | grep "$SYNC_SCRIPT"
else
  # Add cron job: Run every day at midnight (00:00)
  (crontab -l 2>/dev/null; echo "0 0 * * * $SYNC_SCRIPT") | crontab -
  echo "✅ Cron job installed: Daily at 00:00 (midnight)"
  echo "   Script: $SYNC_SCRIPT"
fi

# List all cron jobs
echo ""
echo "Current cron jobs:"
crontab -l
