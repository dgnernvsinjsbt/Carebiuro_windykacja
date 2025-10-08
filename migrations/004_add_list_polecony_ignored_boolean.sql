-- Migration: Add list_polecony_ignored boolean column to invoices table
-- Date: 2025-10-07
-- Description: Zmiana logiki z śledzenia po dacie na boolean flag (true/false)

-- Add list_polecony_ignored column if it doesn't exist
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'invoices'
    AND column_name = 'list_polecony_ignored'
  ) THEN
    ALTER TABLE invoices ADD COLUMN list_polecony_ignored BOOLEAN DEFAULT false;
  END IF;
END $$;

-- Migrate existing data: jeśli faktura ma list_polecony_ignored_date, ustaw flag na true
UPDATE invoices
SET list_polecony_ignored = true
WHERE list_polecony_ignored_date IS NOT NULL;

-- Create index for list_polecony_ignored
CREATE INDEX IF NOT EXISTS idx_invoices_list_polecony_ignored
ON invoices(list_polecony_ignored)
WHERE list_polecony_ignored = true;

-- Możemy zachować kolumnę list_polecony_ignored_date dla historii (opcjonalnie)
-- Ale logika będzie teraz oparta na boolean flag
