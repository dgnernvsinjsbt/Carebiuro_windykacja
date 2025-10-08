# 🚀 Quick Start - Carebiuro Windykacja

## ✅ Status obecny

**Serwer działa**: ✅ http://localhost:3000

**Migracja bazy**: ✅ Zakończona pomyślnie
- `list_polecony` column: ✅
- `message_history` table: ✅

**Nowe funkcje dostępne**:
1. 📧 **Auto-send E1/S1/W1** - Automatyczne wysyłanie o 8:00 rano
2. 📊 **Historia wysyłek** - Zakładka z kompletną historią wiadomości

---

## 🎯 Co możesz teraz zrobić

### 1. Otwórz zakładkę Historia
```
http://localhost:3000/historia
```

**Co zobaczysz**:
- 📊 Karty statystyk (na początku 0/0/0)
- 🔍 Filtry daty i typu wiadomości
- 📅 Grupowanie: Data → Klient → Faktura → Wiadomości
- 🆘 Komunikat "Brak wiadomości w wybranym okresie" (bo jeszcze nic nie wysłano)

### 2. Wyślij testową wiadomość

**Krok 1**: Przejdź do strony głównej
```
http://localhost:3000/
```

**Krok 2**: Kliknij na dowolnego klienta

**Krok 3**: Znajdź fakturę i kliknij "Send Email" lub "Send SMS"

**Krok 4**: Wróć do Historii
```
http://localhost:3000/historia
```

**Wynik**: Powinieneś zobaczyć wysłaną wiadomość!

### 3. Sprawdź automatyczne wysyłanie E1/S1/W1

**Funkcja**: Codziennie o 8:00 rano system automatycznie wysyła wiadomości informacyjne dla faktur wystawionych w ostatnich 3 dniach.

**Test manualny**:
```bash
curl -X POST http://localhost:3000/api/windykacja/auto-send-initial
```

**Test przez skrypt**:
```bash
npx ts-node scripts/test-auto-send-initial.ts
```

**Weryfikacja**:
- Zobacz logi w konsoli
- Sprawdź Historię (wiadomości z emoji 🤖)

---

## 📊 Przykład: Jak wygląda Historia

```
┌─ 07.10.2025 ────────────────────── 24 wiadomości ─┐
│                                                      │
│  👤 Klient X                  2 faktury • 6 wiadomości│
│      📄 FV/2025/001  130 EUR                        │
│      [E1 ✓ 08:00 🤖] [S1 ✓ 08:00 🤖] [W1 ✓ 08:00 🤖]│
│                                                      │
│      📄 FV/2025/002  65 EUR                         │
│      [E1 ✓ 08:01 🤖] [S1 ✓ 08:01 🤖] [W1 ✓ 08:01 🤖]│
│                                                      │
└──────────────────────────────────────────────────────┘
```

**Legenda**:
- **E1/S1/W1** = Email/SMS/WhatsApp poziom 1
- **✓** = Wysłane pomyślnie
- **✗** = Błąd
- **🤖** = Automatyczne (o 8:00)
- **08:00** = Czas wysyłki

---

## 🔧 Konfiguracja Vercel Cron (produkcja)

**Plik**: `vercel.json` (już utworzony)

```json
{
  "crons": [
    {
      "path": "/api/windykacja/auto-send-initial",
      "schedule": "0 8 * * *"
    }
  ]
}
```

**Po deploy na Vercel**:
- Cron automatycznie uruchomi się codziennie o 8:00
- Sprawdzisz logi w Vercel Dashboard → Cron Jobs

---

## 📚 Dokumentacja

| Plik | Opis |
|------|------|
| `CRON_AUTO_SEND.md` | Automatyczne wysyłanie E1/S1/W1 |
| `AUTO_SEND_SUMMARY.md` | Krótkie podsumowanie auto-send |
| `HISTORIA_WYSILEK.md` | Pełna dokumentacja Historii |
| `HISTORIA_SUMMARY.md` | Krótkie podsumowanie Historii |
| `QUICK_MIGRATION.sql` | Migracja bazy danych |
| `CHANGELOG.md` | Historia zmian (v1.2.0 + v1.3.0) |

---

## 🐛 Troubleshooting

### Historia nie ładuje się
**Rozwiązanie**: Sprawdź czy tabela `message_history` istnieje:
```sql
SELECT COUNT(*) FROM message_history;
```

### Brak danych w Historii
**Powód**: Jeszcze nic nie wysłano
**Rozwiązanie**: Wyślij testową wiadomość z panelu klienta

### API zwraca błąd
**Rozwiązanie**: Sprawdź logi serwera, upewnij się że migracja przeszła

---

## 🎉 Wszystko działa!

**Nowe zakładki w nawigacji**:
```
Klienci        (/)
Historia       (/historia)  ← NOWA!
List Polecony  (/list-polecony)
Kaczmarski     (/kaczmarski)
```

**API Endpoints**:
- `GET /api/historia` - Historia wiadomości
- `GET /api/historia/stats` - Statystyki
- `POST /api/windykacja/auto-send-initial` - Test auto-send

**Gratulacje! System jest w pełni funkcjonalny.** 🚀

---

## 📝 Następne kroki (opcjonalne)

1. ✅ Deploy na Vercel
2. ✅ Sprawdź pierwsze automatyczne wysyłki (jutro o 8:00)
3. ✅ Monitoruj Historię przez pierwsze 7 dni
4. ✅ Dodaj powiadomienia email przy błędach (przyszłość)

**Enjoy!** 🎊
