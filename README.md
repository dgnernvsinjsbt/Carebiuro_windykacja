# 🚀 Fiscal Sync

System integracji między **Fakturownia**, **Supabase** i **n8n** do zarządzania przypomnieniami o nieopłaconych fakturach.

## 📋 Funkcje

- ✅ Synchronizacja faktur i klientów z Fakturowni do Supabase
- ✅ Wysyłka przypomnień (Email / SMS / WhatsApp) przez n8n
- ✅ Śledzenie wysłanych przypomnień przez komentarze `[FISCAL_SYNC]`
- ✅ Opcja STOP dla wyłączenia przypomnień dla konkretnych faktur
- ✅ Panel CRM z listą faktur i akcjami
- ✅ Rate limiting dla API Fakturowni (1000 req/h)

## 🛠️ Technologie

- **Next.js 14** - Framework React z Server Components
- **TypeScript** - Typy i bezpieczeństwo kodu
- **Supabase** - Baza danych PostgreSQL
- **Fakturownia API** - Pobieranie i aktualizacja faktur
- **n8n** - Automatyzacja wysyłki wiadomości
- **Tailwind CSS** - Styling
- **Zod** - Walidacja danych
- **React Hot Toast** - Notyfikacje

## 🚀 Instalacja

### 1. Klonowanie repozytorium

\`\`\`bash
git clone <repository-url>
cd Carebiuro_windykacja
\`\`\`

### 2. Instalacja dependencies

\`\`\`bash
npm install
\`\`\`

### 3. Konfiguracja Supabase

1. Utwórz nowy projekt w [Supabase](https://supabase.com)
2. **Uruchom migrację bazy danych**:
   - Otwórz SQL Editor w Supabase
   - Skopiuj i uruchom zawartość pliku **`QUICK_MIGRATION.sql`**
   - Sprawdź komunikaty - powinno być: ✓ OK
3. Skopiuj credentials:
   - Project URL
   - anon/public key
   - service_role key

**Uwaga**: Plik `QUICK_MIGRATION.sql` zawiera bezpieczną migrację, którą można uruchomić wielokrotnie.

### 4. Konfiguracja zmiennych środowiskowych

Skopiuj `.env.example` do `.env`:

\`\`\`bash
cp .env.example .env
\`\`\`

Wypełnij wszystkie wymagane wartości w `.env`:

\`\`\`env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Fakturownia
FAKTUROWNIA_API_TOKEN=your_token
FAKTUROWNIA_ACCOUNT=nazwa-konta  # np. "firma" dla firma.fakturownia.pl

# n8n (opcjonalne)
N8N_WEBHOOK_EMAIL=https://...
N8N_WEBHOOK_SMS=https://...
N8N_WEBHOOK_WHATSAPP=https://...
\`\`\`

### 5. Uruchomienie aplikacji

\`\`\`bash
npm run dev
\`\`\`

Aplikacja będzie dostępna pod [http://localhost:3000](http://localhost:3000)

## 📖 Użytkowanie

### Pierwsza synchronizacja

1. Otwórz aplikację w przeglądarce
2. Kliknij przycisk **"🔄 Synchronizuj dane"**
3. Poczekaj na pobranie wszystkich faktur i klientów z Fakturowni

### Wysyłanie przypomnień

1. Znajdź fakturę na liście
2. Kliknij przycisk przypomnienia:
   - **E1, E2, E3** - Email (poziom 1, 2, 3)
   - **S1, S2, S3** - SMS (poziom 1, 2, 3)
   - **W1, W2, W3** - WhatsApp (poziom 1, 2, 3)
3. System automatycznie:
   - Wyśle webhook do n8n (jeśli skonfigurowane)
   - Zaktualizuje komentarz `[FISCAL_SYNC]` w Fakturowni
   - Zapisze akcję w bazie Supabase

### Włączanie/wyłączanie STOP

- Kliknij przełącznik **STOP** przy fakturze
- Gdy STOP jest włączony (🟠), wszystkie przypomnienia są zablokowane

### Filtry

- **Wszystkie** - pokaż wszystkie faktury
- **Aktywne** - faktury bez flagi STOP
- **STOP** - faktury z włączonym STOP

## 🔄 Struktura komentarza [FISCAL_SYNC]

Każda faktura ma komentarz z sekcją:

\`\`\`
[FISCAL_SYNC]
EMAIL_1=FALSE
EMAIL_2=FALSE
EMAIL_3=FALSE
SMS_1=FALSE
SMS_2=FALSE
SMS_3=FALSE
WHATSAPP_1=FALSE
WHATSAPP_2=FALSE
WHATSAPP_3=FALSE
STOP=FALSE
UPDATED=2025-10-05T10:45:00Z
[/FISCAL_SYNC]
\`\`\`

- **TRUE** - akcja została wykonana
- **FALSE** - akcja nie była wykonana
- **STOP** - blokuje wysyłkę przypomnień
- **UPDATED** - timestamp ostatniej zmiany

## 🛠️ API Endpoints

### POST /api/sync
Pełna synchronizacja Fakturownia → Supabase (nocny cron)

\`\`\`bash
curl -X POST http://localhost:3000/api/sync
\`\`\`

### GET /api/sync?type=incremental
Częściowa synchronizacja (ostatnie 100 faktur)

\`\`\`bash
curl http://localhost:3000/api/sync?type=incremental
\`\`\`

### POST /api/reminder
Wysłanie przypomnienia

\`\`\`bash
curl -X POST http://localhost:3000/api/reminder \\
  -H "Content-Type: application/json" \\
  -d '{
    "invoice_id": 12345,
    "type": "email",
    "level": "1"
  }'
\`\`\`

### PATCH /api/invoice/[id]
Przełączenie flagi STOP

\`\`\`bash
curl -X PATCH http://localhost:3000/api/invoice/12345 \\
  -H "Content-Type: application/json" \\
  -d '{"stop": true}'
\`\`\`

## 📊 Baza danych (Supabase)

### Tabele

**clients**
- `id` - ID klienta z Fakturowni
- `name` - Nazwa klienta
- `email` - Email
- `phone` - Telefon
- `total_unpaid` - Łączna kwota nieopłaconych faktur
- `updated_at` - Ostatnia aktualizacja

**invoices**
- `id` - ID faktury z Fakturowni
- `client_id` - ID klienta (foreign key)
- `number` - Numer faktury
- `total` - Kwota brutto
- `status` - Status (issued, sent, paid, etc.)
- `comment` - Komentarz z sekcją [FISCAL_SYNC]
- `updated_at` - Ostatnia aktualizacja

**invoice_comments**
- `id` - Auto-increment ID
- `invoice_id` - ID faktury (foreign key)
- `body` - Treść komentarza / log akcji
- `created_at` - Data utworzenia
- `source` - Źródło: 'fakturownia' lub 'local'

## 🔐 Bezpieczeństwo

- ✅ Klucze API w `.env` (nie commitowane do repo)
- ✅ Service role key tylko na serwerze (Next.js API Routes)
- ✅ Walidacja danych przez Zod
- ✅ Rate limiting dla Fakturownia API
- ✅ Supabase RLS (Row Level Security) gotowe do konfiguracji

## 📝 Cron Setup (n8n)

Aby uruchomić automatyczną synchronizację co noc:

1. W n8n utwórz workflow z **Cron Trigger** (np. 3:00 AM)
2. Dodaj **HTTP Request** node:
   - Method: POST
   - URL: `https://your-app.com/api/sync`
3. Aktywuj workflow

## 🧪 Development

\`\`\`bash
# Development server
npm run dev

# Build production
npm run build

# Start production
npm start

# Type checking
npm run type-check
\`\`\`

## 📂 Struktura projektu

\`\`\`
Carebiuro_windykacja/
├── app/
│   ├── api/
│   │   ├── sync/route.ts          # Synchronizacja
│   │   ├── reminder/route.ts      # Wysyłka przypomnień
│   │   └── invoice/[id]/route.ts  # Operacje na fakturze
│   ├── globals.css                # Style globalne
│   ├── layout.tsx                 # Layout z Toaster
│   └── page.tsx                   # Dashboard (Server Component)
├── components/
│   ├── InvoiceTable.tsx           # Tabela faktur
│   ├── ReminderButtons.tsx        # Przyciski wysyłki
│   ├── StopToggle.tsx             # Przełącznik STOP
│   └── SyncButton.tsx             # Przycisk synchronizacji
├── lib/
│   ├── fiscal-sync-parser.ts      # Parser komentarzy [FISCAL_SYNC]
│   ├── fakturownia.ts             # Klient API Fakturowni
│   └── supabase.ts                # Klient Supabase + DB helpers
├── types/
│   └── index.ts                   # Typy TypeScript
├── .env                           # Zmienne środowiskowe (gitignored)
├── .env.example                   # Przykładowa konfiguracja
├── supabase-schema.sql            # Schemat bazy danych
└── README.md                      # Ten plik
\`\`\`

## 🐛 Troubleshooting

### Błąd: "Missing Supabase environment variables"
- Sprawdź czy plik `.env` istnieje i ma poprawne wartości
- Uruchom ponownie serwer dev (`npm run dev`)

### Błąd: "Fakturownia API error: 401"
- Sprawdź czy `FAKTUROWNIA_API_TOKEN` jest poprawny
- Sprawdź czy `FAKTUROWNIA_ACCOUNT` to nazwa konta (bez .fakturownia.pl)

### Synchronizacja trwa bardzo długo
- To normalne przy pierwszym uruchomieniu (pobiera wszystkie faktury)
- Rate limiting: 1200ms przerwy między requestami
- Dla 1000 faktur = ~20 minut

### Faktury nie pojawiają się w tabeli
1. Sprawdź czy synchronizacja się zakończyła (sprawdź konsole)
2. Sprawdź w Supabase Table Editor czy dane są w bazie
3. Odśwież stronę (F5)

## 📞 Support

W razie problemów:
1. Sprawdź konsole przeglądarki (F12)
2. Sprawdź logi serwera (terminal gdzie działa `npm run dev`)
3. Sprawdź logi w Supabase Dashboard

## 📄 License

Proprietary - Carebiuro Windykacja System

---

**Zbudowano z ❤️ dla biur rachunkowych**
