# 📨 List Polecony - Dokumentacja

## 🎯 Cel funkcjonalności

System automatycznie identyfikuje klientów wymagających eskalacji windykacji do etapu "List polecony" (Przedsądowe Wezwanie do Zapłaty) i umożliwia generowanie dokumentów PDF oraz Excel dla wybranych klientów.

---

## ⚖️ Warunki eskalacji

Klient kwalifikuje się do zakładki "List polecony", jeśli:

1. **Ma 3 lub więcej faktur** z wysłanym trzecim (finalnym) upomnieniem (`EMAIL_3`, `SMS_3` lub `WHATSAPP_3 = TRUE`)

   **LUB**

2. **Ma co najmniej jedną fakturę powyżej 190 EUR** z wysłanym trzecim upomnieniem

---

## 🔧 Architektura techniczna

### 1. **Struktura bazy danych**

#### Tabela `clients`
```sql
ALTER TABLE clients
  ADD COLUMN note TEXT,
  ADD COLUMN list_polecony BOOLEAN DEFAULT false;
```

- `note` - komentarz z Fakturowni (zawiera `[WINDYKACJA]` i `[LIST_POLECONY]`)
- `list_polecony` - flaga boolean oznaczająca klienta kwalifikującego się do listu poleconego

#### Tabela `invoices`
Rozszerzona o dodatkowe pola potrzebne do PDF/Excel:
- `issue_date`, `payment_to`, `paid_date`
- `buyer_name`, `buyer_email`, `buyer_street`, `buyer_city`, `buyer_post_code`, `buyer_country`
- `currency`, `price_net`, `price_tax`

---

### 2. **Parsery i helpery**

#### `lib/list-polecony-parser.ts`
Parser dla tagu `[LIST_POLECONY]true/false[/LIST_POLECONY]`:
- `parseListPolecony(note)` - odczytuje status
- `updateListPolecony(note, enabled)` - aktualizuje tag
- `removeListPolecony(note)` - usuwa tag

#### `lib/list-polecony-logic.ts`
Logika biznesowa:
- `qualifiesForListPolecony(client, invoices)` - sprawdza warunki eskalacji
- `hasThirdReminder(invoice)` - sprawdza czy faktura ma trzecie upomnienie
- `getInvoicesWithThirdReminder(invoices)` - filtruje faktury z trzecim upomnieniem
- `calculateTotalDebt(invoices)` - sumuje zadłużenie
- `calculateDelayDays(paymentDueDate)` - oblicza dni zwłoki
- `formatDate(dateString)` - formatuje daty do DD.MM.YYYY

#### `lib/pdf-generator.ts`
Generator HTML dla PDF-a:
- `generateListPoleconyHTML(data)` - tworzy HTML zgodny z szablonem "Przedsądowe Wezwanie do Zapłaty"

---

### 3. **API Endpoints**

#### `GET /api/list-polecony/clients`
Zwraca listę klientów kwalifikujących się do listu poleconego.

**Response:**
```json
{
  "success": true,
  "clients": [
    {
      "id": 123,
      "name": "Jan Kowalski",
      "email": "jan@example.com",
      "invoice_count": 5,
      "total_debt": 850.50,
      "qualifies_for_list_polecony": true
    }
  ],
  "count": 1
}
```

#### `POST /api/list-polecony/generate`
Generuje dokumenty (PDF + Excel + ZIP) dla wybranych klientów.

**Request:**
```json
{
  "clientIds": [123, 456, 789]
}
```

**Response:**
Plik ZIP do pobrania zawierający:
- `1.pdf`, `2.pdf`, `3.pdf` - PDF-y dla klientów (sortowane alfabetycznie)
- `lista_klientow.xlsx` - plik Excel z danymi klientów

---

### 4. **Frontend**

#### Strona `/list-polecony`
- Wyświetla tabelę klientów kwalifikujących się do listu poleconego
- Checkboxy do zaznaczania klientów
- Przycisk "Generuj dokumenty"
- Statystyki (liczba klientów, faktur, łączne zadłużenie)

#### Komponenty:
- `components/ListPoleconyTable.tsx` - tabela z checkboxami i akcjami
- `components/Sidebar.tsx` - zaktualizowany o link "List Polecony"

---

## 📄 Format dokumentów

### PDF - "Przedsądowe Wezwanie do Zapłaty"

Szablon zgodny z `1.pdf`:

**Nagłówek:**
```
CBB-OFFICE GmbH
Brunów 43, 59-140 Chocianów, Polska
NIP PL5020122714
poczta@cbb-office.pl
https://cbb-office.pl
Telefon: +48517765655
```

**Treść:**
- Dane odbiorcy (klient)
- Tytuł "PRZEDSĄDOWE WEZWANIE DO ZAPŁATY"
- Tabela faktur (numer, data wystawienia, termin płatności, kwota, dni zwłoki)
- Całkowita kwota zaległości
- Wezwanie do zapłaty w terminie 30 dni
- Dane do przelewu

**Nazewnictwo plików:**
- Klienci sortowani alfabetycznie według nazwy
- Pierwszy klient → `1.pdf`, drugi → `2.pdf`, itd.

---

### Excel - Lista klientów

Szablon zgodny z `szablon_neolist.xlsx`:

**Wiersz 1:** Nagłówek "Parametry druku" (scalony F1:AB1)

**Wiersz 2:** Nagłówki kolumn (A-AB)

**Wiersze 3+:** Dane klientów

#### Kolumny:
- **A-E:** Źródło paczek, Envelo ID, Imię, Nazwisko, Nazwa firmy
- **F-L:** Odbiorca, Ulica, Nr budynku, Nr lokalu, Kod pocztowy, Miasto, Kraj
- **M-Y:** Parametry druku (stałe wartości: Y, S, Test, Ins_A, Papier_X, itp.)
- **R:** `Wskazanie nazwy pliku PDF` → `1.pdf`, `2.pdf`, ...
- **Z-AB:** Dodatkowe dane (opcjonalne)

#### Stałe wartości (powtarzane dla każdego klienta):
- Kolumna M: `1` (Typ produktu)
- Kolumna N: `Y` (Ulica lub skrytka poczt.)
- Kolumna P: `Y` (ZPO)
- Kolumna S: `Y` (Kolor)
- Kolumna T: `S` (Duplex)
- Kolumna U: `Y` (Nadruk adresu)
- Kolumna V: `Y` (Generowanie skanów)
- Kolumna W: `Test` (Tekst ZPO)
- Kolumna X: `Ins_A` (Identyfikator interfejsu)
- Kolumna Y: `Papier_X` (Identyfikator paczki)

---

## 🚀 Workflow użytkowania

1. **Przejdź do zakładki "List Polecony"** (sidebar)
2. **Sprawdź listę klientów** kwalifikujących się do eskalacji
3. **Zaznacz klientów** za pomocą checkboxów (lub "Zaznacz wszystkie")
4. **Kliknij "Generuj dokumenty"**
5. **Pobierz archiwum ZIP** zawierające:
   - Osobne PDF-y dla każdego klienta (`1.pdf`, `2.pdf`, ...)
   - Plik Excel (`lista_klientow.xlsx`)
6. **Wyślij dokumenty** pocztą poleconą

---

## 🔄 Integracja z synchronizacją

### Automatyczna identyfikacja klientów

Podczas synchronizacji z Fakturownią:
1. System pobiera faktury i komentarze zawierające `[FISCAL_SYNC]`
2. Funkcja `qualifiesForListPolecony()` sprawdza warunki eskalacji
3. Jeśli klient kwalifikuje się:
   - Ustawia `list_polecony = true` w Supabase
   - Opcjonalnie aktualizuje tag `[LIST_POLECONY]true[/LIST_POLECONY]` w Fakturowni

### Manualna aktualizacja

Endpoint `GET /api/list-polecony/clients` automatycznie aktualizuje flagę `list_polecony` dla kwalifikujących się klientów.

---

## 🛠️ Konfiguracja i instalacja

### 1. Aktualizacja bazy danych

Uruchom w Supabase SQL Editor:
```sql
-- Zaktualizuj schemat (już w pliku supabase-schema.sql)
ALTER TABLE clients
  ADD COLUMN IF NOT EXISTS note TEXT,
  ADD COLUMN IF NOT EXISTS list_polecony BOOLEAN DEFAULT false;

-- Dodaj indeks
CREATE INDEX IF NOT EXISTS idx_clients_list_polecony
  ON clients(list_polecony)
  WHERE list_polecony = true;
```

### 2. Instalacja zależności

Zainstalowane automatycznie:
```bash
npm install puppeteer exceljs archiver
npm install --save-dev @types/archiver
```

### 3. Uruchomienie

```bash
npm run dev
```

Dostęp do zakładki: [http://localhost:3000/list-polecony](http://localhost:3000/list-polecony)

---

## 📊 Statystyki i monitoring

Strona `/list-polecony` wyświetla:
- **Łączna liczba klientów** kwalifikujących się
- **Łączna liczba faktur** z trzecim upomnieniem
- **Łączne zadłużenie** wszystkich klientów

---

## 🐛 Debugging i troubleshooting

### Problem: Klient nie pojawia się w zakładce

**Sprawdź:**
1. Czy faktury klienta mają prawidłową strukturę `[FISCAL_SYNC]` w `comment`
2. Czy `EMAIL_3`, `SMS_3` lub `WHATSAPP_3` są ustawione na `TRUE`
3. Czy suma zadłużenia (dla faktur >= 190 EUR) jest poprawna

**Logi:**
```typescript
console.log('Klient kwalifikuje się:', qualifiesForListPolecony(client, invoices));
```

### Problem: PDF nie generuje się

**Sprawdź:**
1. Czy Puppeteer jest zainstalowany poprawnie
2. Czy środowisko ma dostęp do Chrome/Chromium
3. Logi w `/api/list-polecony/generate`

**Fix dla środowisk bez GUI:**
```typescript
const browser = await puppeteer.launch({
  headless: true,
  args: ['--no-sandbox', '--disable-setuid-sandbox'],
});
```

### Problem: Excel ma nieprawidłowe dane

**Sprawdź:**
1. Czy dane klienta są poprawnie pobierane z Supabase
2. Czy faktury mają wypełnione pola `buyer_*`
3. Porównaj z szablonem `szablon_neolist.xlsx`

---

## 🔒 Bezpieczeństwo

- Endpoint `/api/list-polecony/generate` wymaga autoryzacji (dodaj middleware jeśli potrzebne)
- Pliki tymczasowe są automatycznie usuwane po wygenerowaniu ZIP
- Dane klientów są chronione przez Supabase RLS (jeśli włączone)

---

## 🎓 Przykładowy kod

### Sprawdzenie czy klient kwalifikuje się

```typescript
import { qualifiesForListPolecony } from '@/lib/list-polecony-logic';

const client = await supabase.from('clients').select('*').eq('id', 123).single();
const invoices = await supabase.from('invoices').select('*').eq('client_id', 123);

if (qualifiesForListPolecony(client.data, invoices.data)) {
  console.log('Klient kwalifikuje się do listu poleconego');
}
```

### Generowanie PDF-a programowo

```typescript
import { generateListPoleconyHTML } from '@/lib/pdf-generator';
import puppeteer from 'puppeteer';

const html = generateListPoleconyHTML({ client, invoices });
const browser = await puppeteer.launch({ headless: true });
const page = await browser.newPage();
await page.setContent(html);
const pdf = await page.pdf({ format: 'A4' });
await browser.close();
```

---

## ✅ Checklist wdrożenia

- [x] Zaktualizowano schemat bazy danych
- [x] Dodano parser `[LIST_POLECONY]`
- [x] Zaimplementowano logikę kwalifikacji
- [x] Stworzono generator HTML/PDF
- [x] Zaimplementowano endpoint `/api/list-polecony/generate`
- [x] Stworzono UI `/list-polecony`
- [x] Dodano link w Sidebar
- [x] Zainstalowano zależności (puppeteer, exceljs, archiver)
- [ ] Przetestowano na środowisku dev
- [ ] Uruchomiono w produkcji
- [ ] Przetestowano generowanie ZIP dla 10+ klientów

---

## 📝 Notatki rozwojowe

### Przyszłe usprawnienia

1. **Cache PDF-ów** - zamiast generować za każdym razem, cache dla tego samego zestawu faktur
2. **Background jobs** - generowanie w tle dla dużej liczby klientów (np. Bullmq + Redis)
3. **Preview PDF** - podgląd przed pobraniem
4. **Customizacja szablonu** - edytor treści listu poleconego
5. **Śledzenie wysyłek** - integr acja z API Poczty Polskiej
6. **Automatyczne wysyłanie** - integracja z serwisem mailingowym

### Optymalizacje

- Używaj `Promise.all()` dla równoległego generowania PDF-ów (obecnie sekwencyjnie przez Puppeteer)
- Rozważ użycie `pdfkit` zamiast Puppeteer dla lepszej wydajności
- Dodaj rate limiting dla endpointu generowania

---

## 🎬 Sukces

Po wdrożeniu:
- Klienci automatycznie trafiają do zakładki "List polecony"
- Możliwość wygenerowania paczki dokumentów jednym kliknięciem
- Dokumenty zgodne z szablonem CBB-OFFICE
- Eksport do Excel dla masowej wysyłki

**Make it work → Make it right → Make it fast.** ✅
