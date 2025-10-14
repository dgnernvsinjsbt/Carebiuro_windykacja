-- Tabela przechowująca edytowalne szablony e-maili dla przypominań o płatnościach
CREATE TABLE IF NOT EXISTS email_templates (
  id TEXT PRIMARY KEY,                    -- 'EMAIL_1', 'EMAIL_2', 'EMAIL_3'
  name TEXT NOT NULL,                     -- 'Email przypomnienie 1'
  subject TEXT NOT NULL,                  -- 'Przypomnienie: Faktura {{invoice_number}}'
  body_html TEXT NOT NULL,                -- HTML template
  body_text TEXT NOT NULL,                -- Plain text fallback
  placeholders JSONB DEFAULT '["{{client_name}}", "{{invoice_number}}", "{{amount}}", "{{due_date}}"]',
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed domyślne template'y
INSERT INTO email_templates (id, name, subject, body_html, body_text) VALUES
('EMAIL_1', 'Email przypomnienie 1', 'Przypomnienie o płatności faktury {{invoice_number}}',
  '<html><body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;"><p>Dzień dobry {{client_name}},</p><p>Uprzejmie przypominamy o płatności za fakturę <strong>{{invoice_number}}</strong> na kwotę <strong>{{amount}}</strong>.</p><p>Termin płatności: {{due_date}}</p><p>Prosimy o jak najszybszą regulację należności.</p><p>Pozdrawiamy,<br><strong>Carebiuro</strong></p></body></html>',
  'Dzień dobry {{client_name}},

Uprzejmie przypominamy o płatności za fakturę {{invoice_number}} na kwotę {{amount}}.

Termin płatności: {{due_date}}

Prosimy o jak najszybszą regulację należności.

Pozdrawiamy,
Carebiuro'),

('EMAIL_2', 'Email przypomnienie 2', 'Drugie przypomnienie: Faktura {{invoice_number}}',
  '<html><body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;"><p>Dzień dobry {{client_name}},</p><p>Ponownie przypominamy o zaległej płatności za fakturę <strong>{{invoice_number}}</strong> na kwotę <strong>{{amount}}</strong>.</p><p>Termin płatności: {{due_date}}</p><p>Prosimy o jak najszybszą regulację należności.</p><p>Pozdrawiamy,<br><strong>Carebiuro</strong></p></body></html>',
  'Dzień dobry {{client_name}},

Ponownie przypominamy o zaległej płatności za fakturę {{invoice_number}} na kwotę {{amount}}.

Termin płatności: {{due_date}}

Prosimy o jak najszybszą regulację należności.

Pozdrawiamy,
Carebiuro'),

('EMAIL_3', 'Email przypomnienie 3 (ostateczne)', 'OSTATECZNE przypomnienie: Faktura {{invoice_number}} przeterminowana',
  '<html><body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;"><p>Dzień dobry {{client_name}},</p><p><strong style="color: #d32f2f;">Ostateczne przypomnienie</strong> o przeterminowanej płatności za fakturę <strong>{{invoice_number}}</strong> na kwotę <strong>{{amount}}</strong>.</p><p>Termin płatności <strong>{{due_date}}</strong> już minął.</p><p>Prosimy o natychmiastową regulację należności.</p><p>Pozdrawiamy,<br><strong>Carebiuro</strong></p></body></html>',
  'Dzień dobry {{client_name}},

OSTATECZNE przypomnienie o przeterminowanej płatności za fakturę {{invoice_number}} na kwotę {{amount}}.

Termin płatności {{due_date}} już minął.

Prosimy o natychmiastową regulację należności.

Pozdrawiamy,
Carebiuro');
