# 📊 Historia wysyłek - Dokumentacja

## 🎯 Opis funkcjonalności

Zakładka **Historia** dostarcza kompletnego widoku wszystkich wiadomości wysłanych przez system. Zaprojektowana z myślą o:
- ✅ Szybkim sprawdzeniu co i kiedy zostało wysłane
- ✅ Weryfikacji czy automatyczny dunning się wykonał
- ✅ Identyfikacji problemów z wysyłką
- ✅ Kompaktowym wyświetlaniu wielu wiadomości

## 📁 Struktura systemu

### 1. Baza danych

**Tabela**: `message_history`

```sql
CREATE TABLE message_history (
  id BIGINT PRIMARY KEY,
  client_id BIGINT REFERENCES clients(id),
  invoice_id BIGINT REFERENCES invoices(id),
  invoice_number TEXT NOT NULL,
  client_name TEXT NOT NULL,

  message_type TEXT CHECK (message_type IN ('email', 'sms', 'whatsapp')),
  level INTEGER CHECK (level IN (1, 2, 3)),

  status TEXT CHECK (status IN ('sent', 'failed')),
  error_message TEXT,

  sent_at TIMESTAMP DEFAULT now(),
  sent_by TEXT DEFAULT 'system', -- 'system' lub 'manual'
  is_auto_initial BOOLEAN DEFAULT false,

  invoice_total NUMERIC,
  invoice_currency TEXT
);
```

**Kluczowe pola**:
- `sent_by`: `'system'` = automatyczne, `'manual'` = ręczne
- `is_auto_initial`: `true` = wiadomość E1/S1/W1 z auto-send-initial (8:00 rano)
- `status`: `'sent'` = sukces, `'failed'` = błąd
- `error_message`: Powód błędu (jeśli `status = 'failed'`)

### 2. API Endpoints

#### `GET /api/historia`

Pobiera historię wiadomości z możliwością filtrowania.

**Query params**:
```
?startDate=2025-10-01      # Data od (ISO format)
&endDate=2025-10-31        # Data do
&clientId=12345            # Filtr po kliencie
&messageType=sms           # Filtr po typie (email/sms/whatsapp)
&limit=100                 # Limit wyników (default 100)
```

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "date": "2025-10-07",
      "totalMessages": 15,
      "clients": [
        {
          "client_id": 12345,
          "client_name": "Klient X",
          "invoices": [
            {
              "invoice_id": 67890,
              "invoice_number": "FV/2025/001",
              "invoice_total": "130.00",
              "invoice_currency": "EUR",
              "messages": [
                {
                  "type": "email",
                  "level": 1,
                  "status": "sent",
                  "sent_at": "2025-10-07T08:00:00Z",
                  "sent_by": "system",
                  "is_auto_initial": true
                },
                {
                  "type": "sms",
                  "level": 1,
                  "status": "sent",
                  "sent_at": "2025-10-07T08:00:30Z",
                  "sent_by": "system",
                  "is_auto_initial": true
                }
              ]
            }
          ]
        }
      ]
    }
  ],
  "total": 15
}
```

**Grupowanie**:
```
Data (2025-10-07)
  └─ Klient X
      └─ FV/2025/001, 130 EUR
          ├─ E1 ✓ 08:00 🤖
          ├─ S1 ✓ 08:00 🤖
          └─ W1 ✓ 08:00 🤖
```

#### `GET /api/historia/stats`

Pobiera statystyki wysyłek.

**Query params**:
```
?startDate=2025-10-01
&endDate=2025-10-31
&days=30                   # Liczba dni wstecz (default 30)
```

**Response**:
```json
{
  "success": true,
  "data": {
    "summary": {
      "total": 450,
      "sent": 432,
      "failed": 18,
      "byType": {
        "email": 150,
        "sms": 200,
        "whatsapp": 100
      },
      "byLevel": {
        "level1": 300,
        "level2": 100,
        "level3": 50
      }
    },
    "daily": [
      {
        "date": "2025-10-07",
        "total": 15,
        "sent": 14,
        "failed": 1,
        "email": 5,
        "sms": 7,
        "whatsapp": 3
      }
    ]
  }
}
```

### 3. Frontend

**Strona**: [`/historia`](app/historia/page.tsx)

**Funkcje**:
- ✅ Statystyki na górze (karty z liczbami)
- ✅ Filtry daty i typu wiadomości
- ✅ Grupowanie: Data → Klient → Faktury → Wiadomości
- ✅ Kompaktowy widok wiadomości (badges)
- ✅ Ikony: 📧 Email, 📱 SMS, 💬 WhatsApp
- ✅ Status: ✓ Sukces, ✗ Błąd
- ✅ Emoji 🤖 dla wiadomości automatycznych
- ✅ Czas wysyłki przy każdej wiadomości

## 🎨 UI/UX Design

### Kompaktowe grupowanie

**Przykład**: Klient X ma 2 faktury, każda wysłała E1, S1, W1

```
┌─ 01.10.2025 ────────────────────────────────── 6 wiadomości ─┐
│                                                                 │
│  👤 Klient X                            2 faktury • 6 wiadomości│
│                                                                 │
│      📄 FV/2025/001  130 EUR                                   │
│      [E1 ✓ 08:00 🤖] [S1 ✓ 08:00 🤖] [W1 ✓ 08:00 🤖]         │
│                                                                 │
│      📄 FV/2025/002  65 EUR                                    │
│      [E1 ✓ 08:01 🤖] [S1 ✓ 08:01 🤖] [W1 ✓ 08:01 🤖]         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Badges

**E1** = Email level 1
**S1** = SMS level 1
**W1** = WhatsApp level 1

**Kolory**:
- Email: 💜 Fioletowy
- SMS: 💚 Zielony
- WhatsApp: 💚 Ciemnozielony
- Błąd: 🔴 Czerwony

**Ikony**:
- ✓ = Wysłane pomyślnie
- ✗ = Błąd
- 🤖 = Automatyczne (E1/S1/W1 o 8:00)

### Filtry

```
┌─ Filtry ────────────────────────────────────────┐
│  Data od: [2025-10-01]                          │
│  Data do: [2025-10-31]                          │
│  Typ: [Wszystkie ▼] Email | SMS | WhatsApp     │
└─────────────────────────────────────────────────┘
```

### Statystyki

```
┌────────────┬────────────┬────────────┬────────────┐
│ Wszystkie  │   Email    │    SMS     │  WhatsApp  │
│    450     │    150     │    200     │    100     │
└────────────┴────────────┴────────────┴────────────┘
```

## 🔄 Logowanie wiadomości

### Automatyczne logowanie

Każda wiadomość wysłana przez system jest automatycznie logowana:

1. **Endpoint `/api/reminder`** (ręczne wysyłki)
   - Loguje po udanym wysłaniu
   - `sent_by: 'manual'`
   - `is_auto_initial: false`

2. **Endpoint `/api/windykacja/auto-send-initial`** (E1/S1/W1 o 8:00)
   - Wywołuje `/api/reminder`, który loguje
   - `sent_by: 'manual'` (technicznie przez reminder)
   - `is_auto_initial: false` (można zmienić w przyszłości)

3. **Endpoint `/api/windykacja/auto-send`** (windykacja S1+)
   - Wywołuje `/api/reminder`, który loguje
   - `sent_by: 'manual'`
   - `is_auto_initial: false`

### Przykład logowania

```typescript
await messageHistoryDb.logMessage({
  client_id: 12345,
  invoice_id: 67890,
  invoice_number: 'FV/2025/001',
  client_name: 'Klient X',
  message_type: 'sms',
  level: 1,
  status: 'sent',
  sent_by: 'manual',
  is_auto_initial: false,
  invoice_total: '130.00',
  invoice_currency: 'EUR',
});
```

## 📊 Use Cases

### 1. Sprawdzenie czy automatyczne wysyłki działają

**Pytanie**: "Czy dzisiaj o 8:00 wysłały się E1/S1/W1?"

**Kroki**:
1. Otwórz zakładkę **Historia**
2. Zobacz dzisiejszą datę na górze
3. Sprawdź wiadomości z emoji 🤖 i godziną ~08:00

**Oczekiwany widok**:
```
┌─ 07.10.2025 ────────────────────── 24 wiadomości ─┐
│  👤 Klient A                                        │
│      📄 FV/001  [E1 ✓ 08:00 🤖] [S1 ✓ 08:00 🤖]   │
│  👤 Klient B                                        │
│      📄 FV/002  [E1 ✓ 08:01 🤖] [S1 ✓ 08:01 🤖]   │
└─────────────────────────────────────────────────────┘
```

### 2. Sprawdzenie historii dla konkretnego klienta

**Pytanie**: "Co było wysyłane do Klienta X w ostatnim miesiącu?"

**Kroki**:
1. Ustaw filtr **Data od**: 30 dni temu
2. (Opcjonalnie) Dodaj filtr clientId przez URL: `/historia?clientId=12345`
3. Rozwiń sekcję klienta

### 3. Identyfikacja błędów

**Pytanie**: "Które SMS-y się nie wysłały?"

**Kroki**:
1. Ustaw filtr **Typ**: SMS
2. Szukaj czerwonych badge'ów z ✗
3. Najedź na badge aby zobaczyć `error_message`

**Przykład błędu**:
```
[S1 ✗ 08:00] ← Hover: "Brak numeru telefonu"
```

### 4. Weryfikacja miesięcznych statystyk

**Pytanie**: "Ile wiadomości wysłaliśmy w październiku?"

**Kroki**:
1. Ustaw **Data od**: 2025-10-01
2. Ustaw **Data do**: 2025-10-31
3. Zobacz statystyki na górze

**Wynik**:
```
Wszystkie: 450
Email: 150
SMS: 200
WhatsApp: 100
```

## 🔧 Konfiguracja

### Baza danych

1. Uruchom migrację:
```sql
-- Zawarte w supabase-schema.sql
CREATE TABLE message_history (...);
```

2. Sprawdź indeksy:
```sql
CREATE INDEX idx_message_history_sent_at ON message_history(sent_at DESC);
CREATE INDEX idx_message_history_client_id ON message_history(client_id);
```

### Frontend

Sidebar automatycznie pokaże link do **Historia** między **Klienci** a **List Polecony**.

### Nawigacja

```
Klienci        (/)
Historia       (/historia)      ← NOWA ZAKŁADKA
List Polecony  (/list-polecony)
Kaczmarski     (/kaczmarski)
```

## 🐛 Troubleshooting

| Problem | Rozwiązanie |
|---------|-------------|
| Brak danych w historii | Sprawdź czy tabela `message_history` istnieje |
| Statystyki nie ładują się | Sprawdź endpoint `/api/historia/stats` |
| Wiadomości się nie logują | Sprawdź czy endpoint reminder wywołuje `messageHistoryDb.logMessage()` |
| Błąd 500 w API | Sprawdź logi Supabase - możliwy problem z permissions |

## 📝 To-Do (przyszłe ulepszenia)

- [ ] Dodać export do CSV/Excel
- [ ] Dodać wykres dzienny (chart.js)
- [ ] Dodać filtr po statusie (sent/failed)
- [ ] Dodać wyszukiwanie po numerze faktury
- [ ] Dodać powiadomienia email gdy `failed > 10` dziennie

## 🎯 Najważniejsze zalety

1. **Kompaktowy widok** - Jeden klient z 10 fakturami = 1 sekcja
2. **Szybka weryfikacja** - Emoji 🤖 = automatyczne, ✓/✗ = status
3. **Intuicyjne grupowanie** - Data → Klient → Faktura → Wiadomości
4. **Pełna historia** - Wszystkie wiadomości w jednym miejscu
5. **Statystyki** - Natychmiastowy overview

---

**Gotowe!** System historii wysyłek jest w pełni funkcjonalny. 🚀
