-- Migration: Fix timezone handling for sent_at column
-- Problem: TIMESTAMP (without time zone) doesn't preserve timezone info
-- Solution: Convert to TIMESTAMPTZ (timestamp with time zone)

-- Convert sent_at to TIMESTAMPTZ
-- This assumes existing data is in UTC (which is correct since now() returns UTC)
ALTER TABLE message_history
  ALTER COLUMN sent_at TYPE TIMESTAMPTZ
  USING sent_at AT TIME ZONE 'UTC';

-- Update default to explicitly use UTC
ALTER TABLE message_history
  ALTER COLUMN sent_at SET DEFAULT now();

-- Verify the change
-- SELECT column_name, data_type, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'message_history' AND column_name = 'sent_at';
