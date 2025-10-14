-- Migration: Add issue_date column to invoices table
-- Date: 2025-10-05

ALTER TABLE invoices ADD COLUMN IF NOT EXISTS issue_date DATE;

-- Create index for sorting by issue date
CREATE INDEX IF NOT EXISTS idx_invoices_issue_date ON invoices(issue_date DESC);

-- Add comment
COMMENT ON COLUMN invoices.issue_date IS 'Data wystawienia faktury (z Fakturownia.created_at)';
