-- Migration: Add list_polecony boolean column to invoices table
-- Date: 2025-10-07
-- Description: Dodanie boolean flagi list_polecony dla spójności z list_polecony_ignored

-- Add list_polecony column if it doesn't exist
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'invoices'
    AND column_name = 'list_polecony'
  ) THEN
    ALTER TABLE invoices ADD COLUMN list_polecony BOOLEAN DEFAULT false;
  END IF;
END $$;

-- Migrate existing data: jeśli faktura ma list_polecony_sent_date, ustaw flag na true
UPDATE invoices
SET list_polecony = true
WHERE list_polecony_sent_date IS NOT NULL;

-- Create index for list_polecony
CREATE INDEX IF NOT EXISTS idx_invoices_list_polecony
ON invoices(list_polecony)
WHERE list_polecony = true;

-- Możemy zachować kolumnę list_polecony_sent_date dla historii (data wysłania)
-- Ale logika będzie teraz oparta na boolean flag
