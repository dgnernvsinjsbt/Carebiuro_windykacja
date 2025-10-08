-- Migration: Rename column comment to internal_note in invoices table
-- This unifies the naming with Fakturownia API where it's called internal_note

-- Step 1: Rename the column
ALTER TABLE invoices RENAME COLUMN comment TO internal_note;

-- Step 2: Verify the change
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'invoices'
AND column_name = 'internal_note';
