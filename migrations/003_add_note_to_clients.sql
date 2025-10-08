-- Migration: Add note column to clients table
-- Date: 2025-10-05
-- Description: Dodaje pole note do tabeli clients do przechowywania komentarzy z Fakturowni
-- Komentarz będzie zawierał [WINDYKACJA]true[/WINDYKACJA] lub [WINDYKACJA]false[/WINDYKACJA]
-- Brak tagu = windykacja wyłączona (dla bezpieczeństwa)

-- Dodaj kolumnę note (komentarz klienta z Fakturowni)
ALTER TABLE clients
ADD COLUMN IF NOT EXISTS note TEXT;

-- Dodaj komentarz do kolumny
COMMENT ON COLUMN clients.note IS 'Komentarz klienta synchronizowany z Fakturowni (pole "note"). Zawiera [WINDYKACJA]true/false[/WINDYKACJA] kontrolujący automatyczne przypomnienia.';
