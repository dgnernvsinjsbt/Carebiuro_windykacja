-- Add outstanding column to invoices table
-- outstanding = total - paid (amount remaining unpaid)

ALTER TABLE invoices
ADD COLUMN IF NOT EXISTS outstanding NUMERIC DEFAULT 0;

-- Create index for queries filtering by outstanding amount
CREATE INDEX IF NOT EXISTS idx_invoices_outstanding ON invoices(outstanding);

-- Update existing rows: outstanding = total - paid
UPDATE invoices
SET outstanding = COALESCE(total, 0) - COALESCE(paid, 0)
WHERE outstanding IS NULL OR outstanding = 0;

-- Comment explaining the field
COMMENT ON COLUMN invoices.outstanding IS 'Amount remaining unpaid (total - paid). Used for List Polecony debt calculation.';
