-- Migration: Sync clients table structure 1:1 with Fakturownia Client fields
-- This ensures exact field mapping to avoid confusion and errors

-- Add all missing Fakturownia fields
ALTER TABLE clients ADD COLUMN IF NOT EXISTS first_name TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS last_name TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS tax_no TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS post_code TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS city TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS street TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS street_no TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS country TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS mobile_phone TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS www TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS fax TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS bank TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS bank_account TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS shortcut TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS kind TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS token TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS discount NUMERIC;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS payment_to_kind TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS category_id INTEGER;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS use_delivery_address BOOLEAN DEFAULT false;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS delivery_address TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS person TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS use_mass_payment BOOLEAN DEFAULT false;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS mass_payment_code TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS external_id TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS company BOOLEAN DEFAULT false;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS register_number TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS tax_no_check TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS disable_auto_reminders BOOLEAN DEFAULT false;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE;

-- Verify all columns exist
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'clients'
ORDER BY ordinal_position;
