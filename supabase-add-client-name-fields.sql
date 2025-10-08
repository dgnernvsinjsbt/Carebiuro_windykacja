-- Migration: Add first_name and last_name columns to clients table to match Fakturownia structure

-- Add first_name column
ALTER TABLE clients
ADD COLUMN IF NOT EXISTS first_name TEXT;

-- Add last_name column
ALTER TABLE clients
ADD COLUMN IF NOT EXISTS last_name TEXT;

-- Verify columns were added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'clients'
AND column_name IN ('first_name', 'last_name')
ORDER BY column_name;
