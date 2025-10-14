-- UsuD duplikaty z message_templates
-- Zostawia tylko najnowszy szablon dla ka|dego (template_key, channel)

BEGIN;

-- 1. Znajdz ID najnowszych szablonów (zachowaj tylko te)
CREATE TEMP TABLE templates_to_keep AS
SELECT DISTINCT ON (template_key, channel) id
FROM message_templates
ORDER BY template_key, channel, created_at DESC NULLS LAST;

-- 2. UsuD wszystkie szablony POZA tymi z listy do zachowania
DELETE FROM message_templates
WHERE id NOT IN (SELECT id FROM templates_to_keep);

-- 3. Dodaj UNIQUE constraint |eby zapobiec przyszBym duplikatom
ALTER TABLE message_templates
ADD CONSTRAINT message_templates_template_key_channel_unique
UNIQUE (template_key, channel);

-- 4. Dodaj komentarz do constrainta
COMMENT ON CONSTRAINT message_templates_template_key_channel_unique ON message_templates
IS 'Zapewnia |e istnieje tylko jeden aktywny szablon dla ka|dego (template_key, channel)';

COMMIT;

-- Poka| statystyki po czyszczeniu
DO $$
DECLARE
  total_count INTEGER;
  duplicates_removed INTEGER;
BEGIN
  SELECT COUNT(*) INTO total_count FROM message_templates;

  RAISE NOTICE ' Migracja zakoDczona pomy[lnie';
  RAISE NOTICE '=Ê Liczba szablonów po czyszczeniu: %', total_count;
  RAISE NOTICE '= Dodano UNIQUE constraint na (template_key, channel)';
END $$;
