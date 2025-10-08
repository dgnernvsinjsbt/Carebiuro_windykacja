-- Migration: Add list_polecony column to clients table
-- Date: 2025-10-07

-- Add list_polecony column if it doesn't exist
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'clients'
    AND column_name = 'list_polecony'
  ) THEN
    ALTER TABLE clients ADD COLUMN list_polecony BOOLEAN DEFAULT false;
  END IF;
END $$;

-- Create index for list_polecony
CREATE INDEX IF NOT EXISTS idx_clients_list_polecony
ON clients(list_polecony)
WHERE list_polecony = true;
