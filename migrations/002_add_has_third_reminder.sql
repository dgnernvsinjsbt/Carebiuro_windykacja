-- Migration: Add has_third_reminder column to invoices table
-- Date: 2025-10-06
-- Purpose: Optimize list polecony queries by pre-computing third reminder status

-- Add column
ALTER TABLE invoices
ADD COLUMN IF NOT EXISTS has_third_reminder BOOLEAN DEFAULT false;

-- Add index for fast filtering
CREATE INDEX IF NOT EXISTS idx_invoices_has_third_reminder
ON invoices(has_third_reminder)
WHERE has_third_reminder = true;

-- Backfill existing data (optional - will be populated by next sync)
-- This can take a while for large datasets, so commented out
-- UPDATE invoices SET has_third_reminder = true
-- WHERE comment LIKE '%EMAIL_3]true%'
--    OR comment LIKE '%SMS_3]true%'
--    OR comment LIKE '%WHATSAPP_3]true%';
