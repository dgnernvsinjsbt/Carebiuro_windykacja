-- ============================================================================
-- Migration: Unified Message Templates System
-- Description: Creates a unified template system for email, SMS, WhatsApp, and letters
-- Date: 2025-10-14
-- ============================================================================

-- ============================================================================
-- 1. CREATE NEW MESSAGE_TEMPLATES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS message_templates (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Template identification
  channel TEXT NOT NULL CHECK (channel IN ('email', 'sms', 'whatsapp', 'letter')),
  template_key TEXT NOT NULL, -- 'REMINDER_1', 'REMINDER_2', 'REMINDER_3', 'FORMAL_NOTICE'
  name TEXT NOT NULL,
  description TEXT,

  -- Status
  is_active BOOLEAN DEFAULT true,

  -- Email-specific fields
  subject TEXT,
  body_html TEXT,

  -- SMS/WhatsApp fields
  body_text TEXT,

  -- Letter-specific fields
  body_top TEXT,    -- Text above invoice table
  body_bottom TEXT, -- Text below invoice table

  -- Shared configuration
  placeholders JSONB DEFAULT '[]'::jsonb,

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  created_by TEXT,

  -- Ensure unique templates per channel
  UNIQUE(channel, template_key)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_message_templates_channel ON message_templates(channel);
CREATE INDEX IF NOT EXISTS idx_message_templates_active ON message_templates(channel, is_active);
CREATE INDEX IF NOT EXISTS idx_message_templates_lookup ON message_templates(channel, template_key, is_active);

-- Add comment
COMMENT ON TABLE message_templates IS 'Unified template storage for all message channels (email, SMS, WhatsApp, letters)';

-- ============================================================================
-- 2. CREATE MESSAGE_TEMPLATE_VERSIONS TABLE (for versioning)
-- ============================================================================

CREATE TABLE IF NOT EXISTS message_template_versions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  template_id UUID NOT NULL REFERENCES message_templates(id) ON DELETE CASCADE,
  version_number INTEGER NOT NULL,

  -- Snapshot of template content at this version
  subject TEXT,
  body_html TEXT,
  body_text TEXT,
  body_top TEXT,
  body_bottom TEXT,
  placeholders JSONB,

  -- Version metadata
  changed_by TEXT,
  changed_at TIMESTAMPTZ DEFAULT NOW(),
  change_note TEXT,

  UNIQUE(template_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_template_versions_template ON message_template_versions(template_id);
CREATE INDEX IF NOT EXISTS idx_template_versions_date ON message_template_versions(changed_at DESC);

COMMENT ON TABLE message_template_versions IS 'Version history for message templates';

-- ============================================================================
-- 3. MIGRATE EXISTING EMAIL TEMPLATES
-- ============================================================================

-- Insert email templates from old email_templates table
INSERT INTO message_templates (
  channel,
  template_key,
  name,
  subject,
  body_html,
  body_text,
  placeholders,
  created_at,
  updated_at,
  is_active
)
SELECT
  'email' as channel,
  id as template_key,
  name,
  subject,
  body_html,
  body_plain as body_text, -- Use body_plain as body_text
  placeholders,
  COALESCE(updated_at, NOW()) as created_at,
  COALESCE(updated_at, NOW()) as updated_at,
  true as is_active
FROM email_templates
ON CONFLICT (channel, template_key) DO NOTHING;

-- ============================================================================
-- 4. SEED DEFAULT SMS TEMPLATES
-- ============================================================================

INSERT INTO message_templates (channel, template_key, name, description, body_text, placeholders, is_active)
VALUES
  (
    'sms',
    'REMINDER_1',
    'Pierwsze przypomnienie SMS',
    'Uprzejme przypomnienie o zalegBej pBatno[ci',
    'Szanowni PaDstwo, uprzejmie przypominamy o nieopBaconej fakturze {{numer_faktury}} na kwot {{kwota}} {{waluta}} z terminem pBatno[ci {{termin}}. Prosimy o piln realizacj pBatno[ci. Carebiuro',
    '[
      {"key": "{{numer_faktury}}", "description": "Numer faktury"},
      {"key": "{{kwota}}", "description": "Kwota do zapBaty"},
      {"key": "{{waluta}}", "description": "Waluta (PLN, EUR, USD)"},
      {"key": "{{termin}}", "description": "Termin pBatno[ci"}
    ]'::jsonb,
    true
  ),
  (
    'sms',
    'REMINDER_2',
    'Drugie przypomnienie SMS',
    'Powt�rne przypomnienie z naciskiem na termin',
    'Drugie przypomnienie: faktura {{numer_faktury}} na {{kwota}} {{waluta}} pozostaje nieopBacona od {{termin}}. Prosimy o natychmiastow pBatno[, aby unikn dalszych krok�w windykacyjnych. Carebiuro',
    '[
      {"key": "{{numer_faktury}}", "description": "Numer faktury"},
      {"key": "{{kwota}}", "description": "Kwota do zapBaty"},
      {"key": "{{waluta}}", "description": "Waluta"},
      {"key": "{{termin}}", "description": "Termin pBatno[ci"}
    ]'::jsonb,
    true
  ),
  (
    'sms',
    'REMINDER_3',
    'Trzecie przypomnienie SMS - ostateczne',
    'Ostrze|enie przed przekazaniem sprawy do windykacji',
    'OSTATECZNE WEZWANIE: Faktura {{numer_faktury}} - {{kwota}} {{waluta}}. Brak pBatno[ci w cigu 3 dni spowoduje przekazanie sprawy do windykacji sdowej. Kontakt: biuro@carebiuro.pl',
    '[
      {"key": "{{numer_faktury}}", "description": "Numer faktury"},
      {"key": "{{kwota}}", "description": "Kwota do zapBaty"},
      {"key": "{{waluta}}", "description": "Waluta"}
    ]'::jsonb,
    true
  )
ON CONFLICT (channel, template_key) DO NOTHING;

-- ============================================================================
-- 5. SEED DEFAULT WHATSAPP TEMPLATES
-- ============================================================================

INSERT INTO message_templates (channel, template_key, name, description, body_text, placeholders, is_active)
VALUES
  (
    'whatsapp',
    'REMINDER_1',
    'Pierwsze przypomnienie WhatsApp',
    'Przyjazne przypomnienie przez WhatsApp',
    'DzieD dobry! =K

Uprzejmie przypominamy o nieopBaconej fakturze:

=� Numer: {{numer_faktury}}
=� Kwota: {{kwota}} {{waluta}}
=� Termin pBatno[ci: {{termin}}

Prosimy o piln realizacj pBatno[ci.

W razie pytaD, jeste[my do dyspozycji.

Pozdrawiamy,
Carebiuro',
    '[
      {"key": "{{numer_faktury}}", "description": "Numer faktury"},
      {"key": "{{kwota}}", "description": "Kwota do zapBaty"},
      {"key": "{{waluta}}", "description": "Waluta"},
      {"key": "{{termin}}", "description": "Termin pBatno[ci"}
    ]'::jsonb,
    true
  ),
  (
    'whatsapp',
    'REMINDER_2',
    'Drugie przypomnienie WhatsApp',
    'Powt�rne przypomnienie z pro[b o kontakt',
    'DzieD dobry,

Niestety nie otrzymali[my jeszcze pBatno[ci za faktur:

=� {{numer_faktury}}
=� {{kwota}} {{waluta}}
� Termin minB: {{termin}}

Prosimy o pilny kontakt lub realizacj pBatno[ci w cigu 3 dni.

Tel: +48 XXX XXX XXX
Email: biuro@carebiuro.pl

Pozdrawiamy,
Carebiuro',
    '[
      {"key": "{{numer_faktury}}", "description": "Numer faktury"},
      {"key": "{{kwota}}", "description": "Kwota do zapBaty"},
      {"key": "{{waluta}}", "description": "Waluta"},
      {"key": "{{termin}}", "description": "Termin pBatno[ci"}
    ]'::jsonb,
    true
  ),
  (
    'whatsapp',
    'REMINDER_3',
    'Trzecie przypomnienie WhatsApp - ostateczne',
    'Ostrze|enie przed windykacj',
    '� OSTATECZNE WEZWANIE �

Faktura: {{numer_faktury}}
Kwota: {{kwota}} {{waluta}}

Mimo wcze[niejszych wezwaD, pBatno[ nie zostaBa zrealizowana.

W przypadku braku pBatno[ci w cigu 3 dni roboczych, sprawa zostanie przekazana do windykacji sdowej, co wi|e si z dodatkowymi kosztami.

Pilny kontakt:
=� biuro@carebiuro.pl
=� +48 XXX XXX XXX

Carebiuro',
    '[
      {"key": "{{numer_faktury}}", "description": "Numer faktury"},
      {"key": "{{kwota}}", "description": "Kwota do zapBaty"},
      {"key": "{{waluta}}", "description": "Waluta"}
    ]'::jsonb,
    true
  )
ON CONFLICT (channel, template_key) DO NOTHING;

-- ============================================================================
-- 6. SEED DEFAULT LETTER TEMPLATES
-- ============================================================================

INSERT INTO message_templates (channel, template_key, name, description, body_top, body_bottom, placeholders, is_active)
VALUES
  (
    'letter',
    'FORMAL_NOTICE',
    'Wezwanie do zapBaty - list polecony',
    'Oficjalne wezwanie do zapBaty wysyBane listem poleconym',
    'Szanowni PaDstwo,

DziaBajc w imieniu naszego Klienta, wzywamy do niezwBocznej zapBaty nastpujcych zalegBych nale|no[ci:',
    'Termin zapBaty: 7 dni od otrzymania niniejszego wezwania.

W przypadku nieuregulowania nale|no[ci w wyznaczonym terminie, sprawa zostanie skierowana na drog postpowania sdowego bez dodatkowego uprzedzenia. Wi|e si to z dodatkowymi kosztami sdowymi, opBatami egzekucyjnymi oraz odsetkami ustawowymi za op�znienie.

Apelujemy o pilne uregulowanie zadBu|enia i uniknicie dalszych konsekwencji prawnych.

Dane do przelewu:
Numer konta: [DANE KONTA]
TytuB przelewu: ZadBu|enie - {{nazwa_klienta}}

W razie pytaD lub chci ustalenia planu spBat, prosimy o pilny kontakt.

Z powa|aniem,
Carebiuro Sp. z o.o.
Biuro Windykacyjne',
    '[
      {"key": "{{nazwa_klienta}}", "description": "Nazwa firmy klienta"},
      {"key": "{{suma_zadluzenia}}", "description": "Suma wszystkich zalegBo[ci"},
      {"key": "{{waluta}}", "description": "Waluta"}
    ]'::jsonb,
    true
  )
ON CONFLICT (channel, template_key) DO NOTHING;

-- ============================================================================
-- 7. CREATE TRIGGER FOR UPDATED_AT
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_message_templates_updated_at
  BEFORE UPDATE ON message_templates
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 8. CREATE TRIGGER FOR AUTO-VERSIONING
-- ============================================================================

CREATE OR REPLACE FUNCTION create_template_version()
RETURNS TRIGGER AS $$
DECLARE
  next_version INTEGER;
BEGIN
  -- Get next version number
  SELECT COALESCE(MAX(version_number), 0) + 1
  INTO next_version
  FROM message_template_versions
  WHERE template_id = NEW.id;

  -- Insert version record
  INSERT INTO message_template_versions (
    template_id,
    version_number,
    subject,
    body_html,
    body_text,
    body_top,
    body_bottom,
    placeholders,
    changed_by,
    changed_at
  ) VALUES (
    NEW.id,
    next_version,
    NEW.subject,
    NEW.body_html,
    NEW.body_text,
    NEW.body_top,
    NEW.body_bottom,
    NEW.placeholders,
    NEW.created_by,
    NOW()
  );

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auto_version_template
  AFTER UPDATE ON message_templates
  FOR EACH ROW
  WHEN (
    OLD.subject IS DISTINCT FROM NEW.subject OR
    OLD.body_html IS DISTINCT FROM NEW.body_html OR
    OLD.body_text IS DISTINCT FROM NEW.body_text OR
    OLD.body_top IS DISTINCT FROM NEW.body_top OR
    OLD.body_bottom IS DISTINCT FROM NEW.body_bottom
  )
  EXECUTE FUNCTION create_template_version();

-- ============================================================================
-- 9. GRANT PERMISSIONS (if using RLS)
-- ============================================================================

-- Enable RLS if needed
-- ALTER TABLE message_templates ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE message_template_versions ENABLE ROW LEVEL SECURITY;

-- Example policy (adjust based on your auth setup)
-- CREATE POLICY "Allow authenticated users to read templates"
--   ON message_templates FOR SELECT
--   TO authenticated
--   USING (true);

-- CREATE POLICY "Allow authenticated users to update templates"
--   ON message_templates FOR UPDATE
--   TO authenticated
--   USING (true);

-- ============================================================================
-- 10. VERIFICATION QUERIES (for testing)
-- ============================================================================

-- Uncomment to verify after migration:
-- SELECT channel, template_key, name FROM message_templates ORDER BY channel, template_key;
-- SELECT COUNT(*) as total_templates, channel FROM message_templates GROUP BY channel;
