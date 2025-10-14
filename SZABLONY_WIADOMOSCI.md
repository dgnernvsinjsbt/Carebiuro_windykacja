# 📧 System Szablonów Wiadomości - Dokumentacja

## 🎯 Przegląd

System szablonów wiadomości umożliwia centralne zarządzanie treścią wszystkich komunikatów wysyłanych do klientów przez 4 kanały:
- **E-mail** - Profesjonalne wiadomości HTML
- **SMS** - Krótkie przypomnienia z walidacją znaków
- **WhatsApp** - Przyjazne wiadomości z emotikonami
- **List polecony** - Formalne wezwania do zapłaty

## 🗂️ Struktura Bazy Danych

### Tabela: `message_templates`

```sql
CREATE TABLE message_templates (
  id UUID PRIMARY KEY,
  channel TEXT ('email', 'sms', 'whatsapp', 'letter'),
  template_key TEXT ('REMINDER_1', 'REMINDER_2', 'REMINDER_3', 'FORMAL_NOTICE'),
  name TEXT,
  description TEXT,
  is_active BOOLEAN,

  -- Email
  subject TEXT,
  body_html TEXT (auto-generated),

  -- SMS/WhatsApp
  body_text TEXT,

  -- Letter
  body_top TEXT,
  body_bottom TEXT,

  -- Wspólne
  placeholders JSONB,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ,

  UNIQUE(channel, template_key)
);
```

### Tabela: `message_template_versions`

Automatyczne wersjonowanie przy każdej zmianie szablonu:
```sql
CREATE TABLE message_template_versions (
  id UUID PRIMARY KEY,
  template_id UUID REFERENCES message_templates(id),
  version_number INTEGER,
  subject TEXT,
  body_html TEXT,
  body_text TEXT,
  body_top TEXT,
  body_bottom TEXT,
  changed_by TEXT,
  changed_at TIMESTAMPTZ,
  change_note TEXT
);
```

## 📁 Struktura Plików

```
app/szablony/
├── layout.tsx                    # Główny layout z nawigacją
├── page.tsx                      # Przekierowanie do /email
├── email/
│   ├── page.tsx                 # Lista szablonów email
│   └── [id]/page.tsx            # Edytor szablonu email
├── sms/
│   ├── page.tsx                 # Lista szablonów SMS
│   └── [id]/page.tsx            # Edytor SMS z licznikiem
├── whatsapp/
│   ├── page.tsx                 # Lista szablonów WhatsApp
│   └── [id]/page.tsx            # Edytor WhatsApp
└── list-polecony/
    ├── page.tsx                 # Lista szablonów listów
    └── [id]/page.tsx            # Edytor listu (2 pola)

components/templates/
├── TemplateNav.tsx              # Nawigacja między kanałami
└── editors/
    ├── EmailEditor.tsx          # Edytor email
    ├── SMSEditor.tsx            # Edytor SMS z walidacją
    ├── WhatsAppEditor.tsx       # Edytor WhatsApp
    └── LetterEditor.tsx         # Edytor listu

lib/templates/
├── types.ts                     # TypeScript types
├── template-service.ts          # Centralna logika
├── formatters/
│   └── sms-formatter.ts         # Formatowanie SMS
└── validators/
    └── sms-validator.ts         # Walidacja SMS (GSM-7/UCS-2)
```

## 🚀 Użycie

### 1. Dostęp do szablonów

Nawigacja: **Sidebar → Szablony**

URL: `http://localhost:3000/szablony`

### 2. Edycja szablonów

#### E-mail
- **Pola**: Temat, Treść (plain text → auto HTML)
- **Funkcje**: Automatyczne formatowanie do HTML
- **Zmienne**: `{{nazwa_klienta}}`, `{{numer_faktury}}`, `{{kwota}}`, `{{termin}}`, `{{waluta}}`

#### SMS
- **Pole**: Treść wiadomości
- **Limit**: 160 znaków (GSM-7) lub 70 znaków (UCS-2 z polskimi znakami)
- **Walidacja**: Real-time licznik, segmenty, encoding
- **Ostrzeżenia**: Automatyczne informacje o przekroczeniach
- **Max**: 3 segmenty SMS

#### WhatsApp
- **Pole**: Treść wiadomości
- **Funkcje**: Wsparcie emotikon, brak limitu znaków
- **Podgląd**: Mobilny mockup z zielonym tłem WhatsApp

#### List polecony
- **Pola**:
  - `body_top` - Tekst NAD tabelą faktur
  - `body_bottom` - Tekst POD tabelą faktur
- **Stałe elementy**: Nagłówek, tabela faktur, stopka (generowane auto)

### 3. API - Aktualizacja szablonu

**Endpoint**: `POST /api/templates/update`

```typescript
// Email
{
  id: "uuid",
  channel: "email",
  subject: "Nowy temat",
  body_text: "Nowa treść"
}

// SMS / WhatsApp
{
  id: "uuid",
  channel: "sms",
  body_text: "Nowa treść SMS"
}

// Letter
{
  id: "uuid",
  channel: "letter",
  body_top: "Tekst nad tabelą",
  body_bottom: "Tekst pod tabelą"
}
```

**Response**:
```json
{
  "success": true
}
```

### 4. Template Service - Pobieranie szablonów

```typescript
import { TemplateService } from '@/lib/templates/template-service';

// Pobierz wszystkie szablony dla kanału
const templates = await TemplateService.getTemplatesByChannel('sms');

// Pobierz konkretny szablon
const template = await TemplateService.getTemplate('email', 'REMINDER_1');

// Formatuj szablon z danymi
const formatted = await TemplateService.formatTemplate(
  'sms',
  'REMINDER_1',
  {
    nazwa_klienta: 'Przykładowa Firma',
    numer_faktury: 'FV/2024/10/123',
    kwota: '2,500.00',
    termin: '15.10.2024',
    waluta: 'PLN'
  }
);
```

## 📊 SMS Validator - Szczegóły

### Encoding Types

**GSM-7** (160 chars):
- Znaki ASCII standardowe
- Niektóre europejskie znaki (£, ¥, €)
- Znaki rozszerzone (^, {, }, [, ], ~, |) liczą się jako 2

**UCS-2** (70 chars):
- Wszystkie znaki Unicode
- Polskie znaki: ą, ć, ę, ł, ń, ó, ś, ź, ż
- Automatycznie wykrywane

### Segmentacja

| Encoding | 1 segment | 2+ segments (per segment) |
|----------|-----------|---------------------------|
| GSM-7    | 160 chars | 153 chars                 |
| UCS-2    | 70 chars  | 67 chars                  |

**Max segmentów**: 3 (ograniczenie systemowe)

### Przykład użycia

```typescript
import { SMSValidator } from '@/lib/templates/validators/sms-validator';

const validator = new SMSValidator('Cześć! Masz fakturę do zapłaty.');
const validation = validator.validate();

console.log(validation);
// {
//   length: 32,
//   encoding: 'UCS-2',  // polskie znaki!
//   segments: 1,
//   maxLength: 70,
//   isValid: true,
//   warnings: [
//     'Wiadomość zawiera polskie znaki (ą, ę, ć, etc.) - limit 70 znaków na SMS'
//   ]
// }
```

## 🔄 Wersjonowanie

Każda zmiana szablonu automatycznie tworzy wersję:

```sql
SELECT * FROM message_template_versions
WHERE template_id = 'uuid'
ORDER BY version_number DESC;
```

Przywracanie wersji:
```typescript
const versions = await TemplateService.getTemplateVersions(templateId);
// Ręcznie skopiuj wartości z poprzedniej wersji
```

## 🎨 Placeholders (Zmienne)

### Email
- `{{nazwa_klienta}}` - Nazwa firmy klienta
- `{{numer_faktury}}` - Numer faktury
- `{{kwota}}` - Kwota do zapłaty
- `{{termin}}` - Termin płatności
- `{{waluta}}` - Waluta (PLN, EUR, USD)

### SMS
- `{{numer_faktury}}` - Numer faktury
- `{{kwota}}` - Kwota
- `{{waluta}}` - Waluta
- `{{termin}}` - Termin

### WhatsApp
- Wszystkie jak SMS
- Dodatkowo emotikony: 📄, 💰, 📅, ⏰, ⚠️

### Letter
- `{{nazwa_klienta}}` - Nazwa firmy
- `{{suma_zadluzenia}}` - Suma wszystkich zaległości
- `{{waluta}}` - Waluta

## 🔧 Migracja z Systemu Starego

### Krok 1: Uruchom migrację

```bash
# Już wykonane - tabela message_templates istnieje
SUPABASE_ACCESS_TOKEN="sbp_..." npx supabase db push
```

### Krok 2: Sprawdź dane

```sql
-- Powinno być 10 szablonów:
-- 3 email (EMAIL_1, EMAIL_2, EMAIL_3)
-- 3 SMS (REMINDER_1, 2, 3)
-- 3 WhatsApp (REMINDER_1, 2, 3)
-- 1 Letter (FORMAL_NOTICE)

SELECT channel, template_key, name
FROM message_templates
ORDER BY channel, template_key;
```

### Krok 3: Aktualizuj istniejący kod

**Stary kod** (hardcoded SMS):
```typescript
// app/api/reminder/route.ts
const message = `Drogi kliencie, w dniu ${issueDate}...`;
```

**Nowy kod** (template system):
```typescript
import { TemplateService } from '@/lib/templates/template-service';

const formatted = await TemplateService.formatTemplate(
  'sms',
  'REMINDER_1',
  {
    numer_faktury: invoice.number,
    kwota: invoice.total,
    waluta: invoice.currency,
    termin: invoice.payment_to
  }
);

// formatted.text - gotowa wiadomość
// formatted.isValid - czy nie przekracza limitów
```

## ⚡ Performance

- **RSC (React Server Components)** - Wszystkie listy i edytory
- **Lazy loading** - Supabase client inicjalizowany on-demand
- **Indexed queries** - Indeksy na (channel, template_key, is_active)
- **Edge-ready** - Działa na Vercel Edge Functions

## 🐛 Troubleshooting

### Problem: "Template not found"
**Rozwiązanie**: Sprawdź czy migracja została wykonana:
```sql
SELECT COUNT(*) FROM message_templates;
-- Powinno być 10
```

### Problem: SMS pokazuje więcej segmentów niż się spodziewasz
**Przyczyna**: Polskie znaki powodują UCS-2 encoding (70 chars limit)
**Rozwiązanie**: Usuń polskie znaki lub zaakceptuj wieloczęściowy SMS

### Problem: Email nie formatuje się poprawnie
**Przyczyna**: `body_html` generuje się automatycznie przez `plainTextToHtml()`
**Rozwiązanie**: Edytuj `body_text`, HTML wygeneruje się sam

## 📈 Przyszłe Usprawnienia

- [ ] Bulk update szablonów
- [ ] A/B testing szablonów
- [ ] Statystyki skuteczności (open rate, click rate)
- [ ] Preview przed zapisem z prawdziwymi danymi
- [ ] Eksport/import szablonów (JSON)
- [ ] Multi-language support
- [ ] Template variables preview w czasie rzeczywistym

## 🔐 Bezpieczeństwo

- **RLS disabled** - Szablony dostępne tylko przez admin client
- **Server-side only** - TemplateService działa tylko na serwerze
- **No user input** - Placeholders są predefiniowane, nie user-generated
- **Versioning** - Historia zmian z `changed_by` field

---

**Autorzy**: System zaprojektowany przez Claude (Anthropic)
**Data**: 2025-10-14
**Wersja**: 1.0.0
