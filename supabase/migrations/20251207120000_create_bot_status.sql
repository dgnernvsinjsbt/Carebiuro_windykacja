-- Bot status table for remote monitoring
CREATE TABLE IF NOT EXISTS bot_status (
    bot_id TEXT PRIMARY KEY,
    status JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Allow public read/write for anon key
ALTER TABLE bot_status ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all access to bot_status" ON bot_status
    FOR ALL USING (true) WITH CHECK (true);

-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_bot_status_updated ON bot_status(updated_at DESC);
