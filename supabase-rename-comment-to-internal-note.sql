-- Rename comment column to internal_note in invoices table
-- This ensures 1:1 field mapping with Fakturownia API

ALTER TABLE invoices RENAME COLUMN comment TO internal_note;

-- Verify the change
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'invoices'
  AND column_name = 'internal_note';
