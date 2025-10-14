-- Add email_status and sent_time fields to invoices table
ALTER TABLE invoices
ADD COLUMN IF NOT EXISTS email_status TEXT,
ADD COLUMN IF NOT EXISTS sent_time TIMESTAMP;

-- Add index for better performance
CREATE INDEX IF NOT EXISTS idx_invoices_email_status ON invoices(email_status);
