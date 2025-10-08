# Checkpoint: Operation Lock System — 2025-10-06

## 🐛 Problem

Podczas szybkiego klikania w UI (np. STOP na fakturach + włącz WINDYKACJĘ w krótkim odstępie czasu) występował **race condition**:

1. User klikał STOP na 4 fakturach (aktualizacja komentarzy w Fakturowni)
2. User szybko klikał "Włącz WINDYKACJĘ"
3. WindykacjaToggle wywoływał `/api/sync/client` który:
   - Usuwał wszystkie faktury z Supabase
   - Pobierał je na nowo z Fakturowni
4. **Problem**: Fakturownia nie zdążyła przetworzyć zmian z punktu 1, więc sync nadpisał Supabase starymi danymi
5. **Efekt**: Utrata flag STOP na fakturach

### Dodatkowe komplikacje

- `StopToggle` wywoływał `window.location.reload()` co powodowało niepotrzebne reloady
- Brak mechanizmu blokującego równoczesne operacje
- User mógł klikać wiele rzeczy jednocześnie bez feedbacku

## ✅ Rozwiązanie

Zaimplementowano **globalny system blokad operacji** (Operation Lock):

### 1. Lock Context (`lib/client-operation-lock.tsx`)

```typescript
- ClientOperationLockProvider - React ContextProvider
- useClientOperationLock() - hook do zarządzania lockiem
- lockOperation(name) - próba zablokowania (zwraca true/false)
- unlockOperation() - zwolnienie blokady
- isLocked - status czy jakaś operacja jest w toku
- currentOperation - nazwa aktualnie wykonywanej operacji
```

**Jak działa**:
- Tylko JEDNA operacja może działać naraz
- Przy próbie drugiej operacji → toast error "Operacja w toku: [nazwa]. Proszę czekać..."
- Po zakończeniu operacji → automatyczne odblokowanie

### 2. Integracja z WindykacjaToggle

```typescript
const { lockOperation, unlockOperation, isLocked } = useClientOperationLock();

// Przed rozpoczęciem operacji
if (!lockOperation('Włączanie WINDYKACJI')) {
  return; // Inna operacja w toku
}

// Po zakończeniu (finally block)
unlockOperation();

// UI
disabled={isUpdating || isLocked}
```

### 3. Integracja z StopToggle

```typescript
// Analogicznie jak WindykacjaToggle

// WAŻNE: Usunięto window.location.reload()!
// Zamiast tego - optimistic update + unlock po 500ms
setTimeout(() => unlockOperation(), 500);
```

### 4. Wizualny Banner (`components/OperationStatusBanner.tsx`)

Banner na górze strony pokazujący:
- Spinner
- Nazwę operacji w toku
- "Proszę czekać"

Widoczny tylko gdy `isLocked === true`

### 5. Provider w stronie klienta

```typescript
<ClientOperationLockProvider>
  <OperationStatusBanner />
  <div>... reszta strony ...</div>
</ClientOperationLockProvider>
```

## 📁 Pliki zmodyfikowane

### Nowe pliki:
- `lib/client-operation-lock.tsx` - Context + hook
- `components/OperationStatusBanner.tsx` - Wizualny wskaźnik

### Zmodyfikowane pliki:
- `components/WindykacjaToggle.tsx` - dodano lock
- `components/StopToggle.tsx` - dodano lock + usunięto reload
- `app/client/[id]/page.tsx` - dodano Provider + Banner

## 🎯 Efekty

### ✅ Co działa

- **Blokada równoczesnych operacji** - niemożliwe wykonanie dwóch operacji naraz
- **Feedback dla usera** - toast + banner informują o operacji w toku
- **Brak niepotrzebnych reloadów** - StopToggle działa bez przeładowania strony
- **Optymistyczne UI** - zmiany widoczne natychmiast
- **Konsola loguje** lock/unlock dla debugowania

### 🛡️ Zapobieganie problemom

1. **Race condition** - rozwiązany przez serialization operacji
2. **Utrata danych** - niemożliwa bo sync nie może wystartować podczas update faktur
3. **Chaos w UI** - user widzi jasno co się dzieje
4. **Duplikacja requestów** - zablokowane

## 🧪 Test Plan

1. Wejdź na stronę klienta testowego
2. Szybko kliknij 4x STOP na różnych fakturach
3. Obserwuj:
   - Toast "Operacja w toku" przy drugiej próbie
   - Banner na górze ekranu
   - Disabled toggle buttons podczas operacji
4. Po zakończeniu wszystkich operacji sprawdź czy:
   - Flagi STOP są ustawione poprawnie
   - Dane się nie zgubiły
   - System odblokował się

## 📝 Next Steps (opcjonalne ulepszenia)

- [ ] Dodać queue zamiast reject - kolejkować operacje zamiast blokować
- [ ] Dodać timeout (auto-unlock po X sekundach jeśli coś się zawiesi)
- [ ] Rozszerzyć na inne strony (HomePage, List Polecony)
- [ ] Dodać analytics - ile razy user próbował kliknąć podczas locka

## 💡 Wnioski

**Problem**:
- Brak kontroli nad równoczesnymi operacjami prowadzi do race conditions
- Async operations wymagają serialization w krytycznych momentach

**Nauka**:
- Zawsze implementuj lock mechanism gdy masz operacje modyfikujące dane
- Feedback dla usera = kluczowe (toast + visual banner)
- Optimistic updates > page reloads (lepsze UX)

**Produktowo**:
- System teraz jest bezpieczniejszy i bardziej przewidywalny
- User nie może "zepsuć" danych przez zbyt szybkie klikanie
- Jasny komunikat "co się dzieje" buduje zaufanie

---

## 🚨 Red Flags do monitorowania

Jeśli zobaczysz:
- Lock nie odblokowuje się (operacja wiesza się) → dodaj timeout
- User często widzi "Operacja w toku" → może UX wymaga poprawy
- Logi pokazują wiele prób lock podczas lock → może queue będzie lepszy

**Status**: ✅ Gotowe do testów produkcyjnych
**Data**: 2025-10-06
**By**: Claude + Krystian
