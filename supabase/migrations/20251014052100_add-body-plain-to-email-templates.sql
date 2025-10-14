-- Dodaj kolumnę body_plain dla treści plain text
ALTER TABLE email_templates ADD COLUMN IF NOT EXISTS body_plain TEXT;

-- Zaktualizuj istniejące rekordy - skopiuj body_text do body_plain
UPDATE email_templates SET body_plain = body_text WHERE body_plain IS NULL;

-- Ustaw body_plain jako NOT NULL po migracji danych
ALTER TABLE email_templates ALTER COLUMN body_plain SET NOT NULL;