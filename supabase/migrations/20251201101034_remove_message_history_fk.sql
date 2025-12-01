-- Migracja: Usunięcie FK z message_history
-- Problem: ON DELETE CASCADE powodowało usuwanie historii przy nocnym full-sync
-- Rozwiązanie: Historia jest niezależna od cache invoices/clients

-- Usuń FK do clients
ALTER TABLE message_history DROP CONSTRAINT IF EXISTS message_history_client_id_fkey;

-- Usuń FK do invoices
ALTER TABLE message_history DROP CONSTRAINT IF EXISTS message_history_invoice_id_fkey;

-- Kolumny client_id i invoice_id pozostają (bez FK) - przydatne do filtrowania
-- Dane denormalizowane (client_name, invoice_number, invoice_total) już istnieją

COMMENT ON TABLE message_history IS 'Historia wysyłek - niezależna od nocnego sync. Dane denormalizowane.';
