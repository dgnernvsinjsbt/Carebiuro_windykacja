-- Invoice Hash Registry: Persistent storage for invoice hash verification
-- This table is NOT dropped during nightly sync - it persists to detect "Wystaw podobną" duplicates

CREATE TABLE IF NOT EXISTS invoice_hash_registry (
  invoice_id INTEGER PRIMARY KEY,
  expected_hash TEXT NOT NULL,
  first_action_date TIMESTAMP NOT NULL, -- When we first took action on this invoice
  last_verified_date TIMESTAMP, -- Last time we verified the hash during sync
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for looking up invoices by hash (to detect duplicates)
CREATE INDEX IF NOT EXISTS idx_hash_lookup ON invoice_hash_registry(expected_hash);

-- Index for cleanup queries (find old entries)
CREATE INDEX IF NOT EXISTS idx_first_action_date ON invoice_hash_registry(first_action_date);

-- Comment explaining the purpose
COMMENT ON TABLE invoice_hash_registry IS 'Persistent registry mapping invoice_id to expected hash. Used to detect "Wystaw podobną" duplicates where internal_note is copied. This table MUST NOT be dropped during nightly sync.';

COMMENT ON COLUMN invoice_hash_registry.invoice_id IS 'Fakturownia invoice ID (unique identifier)';
COMMENT ON COLUMN invoice_hash_registry.expected_hash IS 'MD5 hash of invoice immutable data (id|issue_date|client_id). First 8 chars.';
COMMENT ON COLUMN invoice_hash_registry.first_action_date IS 'Timestamp when we first sent a reminder or took action on this invoice';
COMMENT ON COLUMN invoice_hash_registry.last_verified_date IS 'Last time we verified this hash during sync (for monitoring staleness)';
