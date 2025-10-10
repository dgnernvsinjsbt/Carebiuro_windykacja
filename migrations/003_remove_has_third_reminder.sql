-- Migration: Remove has_third_reminder column from invoices table
-- Date: 2025-10-10
-- Purpose: Remove deprecated optimization column - use invoice.internal_note as single source of truth

-- Drop index first
DROP INDEX IF EXISTS idx_invoices_has_third_reminder;

-- Drop column
ALTER TABLE invoices
DROP COLUMN IF EXISTS has_third_reminder;

-- Drop deprecated List Polecony columns from invoices
ALTER TABLE invoices
DROP COLUMN IF EXISTS list_polecony;

ALTER TABLE invoices
DROP COLUMN IF EXISTS list_polecony_sent_date;

ALTER TABLE invoices
DROP COLUMN IF EXISTS list_polecony_ignored;

ALTER TABLE invoices
DROP COLUMN IF EXISTS list_polecony_ignored_date;

-- Note: ALL List Polecony flags are now stored in invoice.internal_note
-- Format: [LIST_POLECONY_STATUS]sent|ignore|false[/LIST_POLECONY_STATUS]
-- Format: [LIST_POLECONY_STATUS_DATE]YYYY-MM-DD[/LIST_POLECONY_STATUS_DATE]
