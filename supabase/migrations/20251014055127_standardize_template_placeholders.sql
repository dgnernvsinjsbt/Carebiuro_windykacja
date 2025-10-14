-- ============================================================================
-- Migration: Standardize Template Placeholders
-- Description: Unifies placeholders across all message templates (email, SMS, WhatsApp, letter)
-- Date: 2025-10-14
-- ============================================================================

-- Define universal placeholder set that works for ALL templates
-- These placeholders will be available in email, SMS, WhatsApp, and letter templates

UPDATE message_templates
SET placeholders = '[
  {"key": "{{nazwa_klienta}}", "description": "Nazwa firmy/osoba klienta"},
  {"key": "{{numer_faktury}}", "description": "Numer faktury"},
  {"key": "{{kwota}}", "description": "Kwota do zapłaty"},
  {"key": "{{waluta}}", "description": "Waluta (PLN, EUR, USD)"},
  {"key": "{{termin}}", "description": "Termin płatności"},
  {"key": "{{data_wystawienia}}", "description": "Data wystawienia faktury"},
  {"key": "{{suma_zadluzenia}}", "description": "Suma wszystkich zaległości"},
  {"key": "{{email}}", "description": "E-mail kontaktowy"},
  {"key": "{{telefon}}", "description": "Telefon kontaktowy"},
  {"key": "{{nip}}", "description": "NIP klienta"},
  {"key": "{{adres}}", "description": "Adres klienta"}
]'::jsonb
WHERE channel IN ('email', 'sms', 'whatsapp', 'letter');

-- ============================================================================
-- Verification
-- ============================================================================

-- Uncomment to verify:
-- SELECT channel, template_key, name, jsonb_array_length(placeholders) as placeholder_count
-- FROM message_templates
-- ORDER BY channel, template_key;
