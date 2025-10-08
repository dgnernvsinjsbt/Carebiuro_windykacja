-- Fix duplicate invoices and ensure ID is unique
-- Step 1: Find and remove duplicates (keep only the most recent)
DELETE FROM invoices a
USING invoices b
WHERE a.id = b.id
  AND a.updated_at < b.updated_at;

-- Step 2: Check if there are still any duplicates
-- (This query should return 0 rows after Step 1)
SELECT id, COUNT(*) as count
FROM invoices
GROUP BY id
HAVING COUNT(*) > 1;

-- Step 3: Ensure id column is PRIMARY KEY (should already be, but let's make sure)
-- Note: PostgreSQL doesn't allow altering existing PRIMARY KEY easily
-- If id is already PRIMARY KEY, this will fail but that's OK
-- ALTER TABLE invoices ADD PRIMARY KEY (id);

-- Note: Run this in Supabase SQL Editor and check results
