-- Migration: Add all missing Fakturownia fields to invoices table
-- Date: 2025-10-05

-- Core invoice data
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS issue_date DATE;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS sell_date DATE;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS payment_to DATE;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS paid_date DATE;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS created_at TIMESTAMP;

-- Financial data
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS price_net NUMERIC;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS price_tax NUMERIC;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS paid NUMERIC;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS currency VARCHAR(10);
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS payment_type VARCHAR(50);

-- Buyer information
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS buyer_name TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS buyer_email TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS buyer_phone TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS buyer_tax_no TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS buyer_street TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS buyer_city TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS buyer_post_code TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS buyer_country TEXT;

-- Document metadata
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS kind VARCHAR(50);
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS place TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS view_url TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS payment_url TEXT;

-- Status fields
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS overdue BOOLEAN;

-- Create indexes for sorting and filtering
CREATE INDEX IF NOT EXISTS idx_invoices_issue_date ON invoices(issue_date DESC);
CREATE INDEX IF NOT EXISTS idx_invoices_sell_date ON invoices(sell_date DESC);
CREATE INDEX IF NOT EXISTS idx_invoices_payment_to ON invoices(payment_to DESC);
CREATE INDEX IF NOT EXISTS idx_invoices_created_at ON invoices(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_invoices_buyer_email ON invoices(buyer_email);
CREATE INDEX IF NOT EXISTS idx_invoices_currency ON invoices(currency);
