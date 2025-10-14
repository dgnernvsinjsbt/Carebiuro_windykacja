-- Migration: Add windykacja_enabled to clients table
-- Date: 2025-10-05
-- Description: Dodaje pole windykacja_enabled do tabeli clients (domyślnie false)
-- Ten toggle kontroluje czy automatyczne przypomnienia (SMS, Email, WhatsApp) są aktywne dla wszystkich faktur klienta

-- Dodaj kolumnę windykacja_enabled (domyślnie false)
ALTER TABLE clients
ADD COLUMN IF NOT EXISTS windykacja_enabled BOOLEAN DEFAULT FALSE;

-- Dodaj komentarz do kolumny
COMMENT ON COLUMN clients.windykacja_enabled IS 'Czy automatyczne przypomnienia (SMS/Email/WhatsApp) są włączone dla tego klienta. Domyślnie: false (wyłączone dla bezpieczeństwa).';

-- Aktualizuj indeksy (opcjonalnie - dla szybszych zapytań cron)
CREATE INDEX IF NOT EXISTS idx_clients_windykacja_enabled ON clients(windykacja_enabled) WHERE windykacja_enabled = TRUE;
