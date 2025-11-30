# Jak pobrać PRAWDZIWE reviews z Google Maps

## ✅ Metoda 1: Bezpośrednio z Google Maps (NAJŁATWIEJSZA)

### Krok 1: Otwórz Google Maps
Kliknij ten link (twój biznes):
```
https://www.google.com/maps/place/?q=place_id:ChIJr1j6aRVeyKERtMJqTpRkvQc
```

### Krok 2: Kliknij "Reviews"
1. Znajdź zakładkę **"Reviews"** (lub "Recenzje" jeśli w języku polskim)
2. Kliknij, aby zobaczyć wszystkie reviews
3. Przewiń w dół - zobaczysz wszystkie 10 recenzji

### Krok 3: Skopiuj każdą recenzję
Dla każdej z 10 recenzji zapisz:

**Format:**
```
Imię: [Pełne imię autora]
Inicjały: [Pierwsza litera imienia + nazwiska]
Rating: 5
Text: [Cały tekst komentarza]
Date: [Względna data np. "2 months ago"]
```

**Przykład:**
```
Imię: John Smith
Inicjały: JS
Rating: 5
Text: Great service! Very professional and reliable.
Date: 3 months ago
```

---

## ✅ Metoda 2: Przez Google My Business (jeśli masz dostęp)

### Krok 1: Zaloguj się
1. Przejdź do https://business.google.com
2. Zaloguj się kontem, które ma dostęp do Hunn's Landscaping

### Krok 2: Wybierz Reviews
1. Wybierz profil **Hunn's Landscaping**
2. Kliknij **"Reviews"** w menu bocznym
3. Zobaczysz listę wszystkich recenzji

### Krok 3: Eksportuj dane
1. Możesz skopiować każdą recenzję bezpośrednio
2. Lub zrobić screenshot dla łatwiejszego przepisywania

---

## 📝 Jak wkleić reviews do kodu

### Krok 1: Otwórz plik HTML
Otwórz `google-reviews-carousel.html`

### Krok 2: Znajdź sekcję REVIEWS DATA
Szukaj tego fragmentu (około linia 245):

```javascript
// ============================================
// REVIEWS DATA - EDIT THIS SECTION
// REPLACE WITH YOUR ACTUAL GOOGLE REVIEWS
// ============================================
const reviews = [
```

### Krok 3: Zastąp przykładowe dane
**PRZED (przykładowe dane):**
```javascript
const reviews = [
  {
    author: "John Smith",
    initials: "JS",
    rating: 5,
    text: "Hunn's Landscaping transformed our yard...",
    date: "2 months ago"
  },
  // ... więcej przykładowych reviews
];
```

**PO (prawdziwe dane z Google):**
```javascript
const reviews = [
  {
    author: "Real Name 1",        // PRAWDZIWE IMIĘ Z GOOGLE
    initials: "RN",               // INICJAŁY
    rating: 5,                    // OCENA (1-5)
    text: "Actual review text from Google Maps...",  // PRAWDZIWY TEKST
    date: "2 months ago"          // PRAWDZIWA DATA
  },
  {
    author: "Real Name 2",
    initials: "RN",
    rating: 5,
    text: "Another real review...",
    date: "1 month ago"
  }
  // ... pozostałe prawdziwe reviews (wszystkie 10)
];
```

### Krok 4: Zapisz i wklej do Go High Level
1. Zapisz plik
2. Skopiuj **CAŁY KOD**
3. Wklej do Go High Level Custom Code

---

## 🎯 Szablon do przepisywania reviews

Możesz użyć tego szablonu w Notatkach/Excelu:

| Imię | Inicjały | Rating | Text | Date |
|------|----------|--------|------|------|
| John Smith | JS | 5 | Great service! | 2 months ago |
| Sarah Johnson | SJ | 5 | Very professional | 1 month ago |

Potem przekonwertuj do formatu:

```javascript
{
  author: "John Smith",
  initials: "JS",
  rating: 5,
  text: "Great service!",
  date: "2 months ago"
},
```

---

## ⚠️ WAŻNE UWAGI

### 1. Rating i liczba reviews (linia ~216)
Jeśli zmienisz reviews, **MUSISZ** zaktualizować też header:

```html
<div class="reviews-rating-wrapper">
  <span class="rating-number">5.0</span>    <!-- ZMIEŃ NA ŚREDNIĄ -->
  <div class="stars">★★★★★</div>
  <span class="review-count">Based on 10 Reviews</span>  <!-- ZMIEŃ LICZBĘ -->
</div>
```

**Jak policzyć średnią:**
- Wszystkie 5-gwiazdkowe → `5.0`
- Dwie 4-gwiazdkowe + osiem 5-gwiazdkowych → `(4+4+5+5+5+5+5+5+5+5) / 10 = 4.8`

### 2. Format daty
Google używa **względnych dat**:
- ✅ "2 months ago"
- ✅ "1 year ago"
- ✅ "3 weeks ago"
- ❌ NIE: "January 2024"
- ❌ NIE: "2024-01-15"

### 3. Cudzysłowy w tekście
Jeśli review zawiera cudzysłów, użyj `\"`:

❌ **ŹLE:**
```javascript
text: "He said "great work"!"  // BŁĄD!
```

✅ **DOBRZE:**
```javascript
text: "He said \"great work\"!"  // OK
```

lub użyj apostrofu:

✅ **DOBRZE:**
```javascript
text: "He said 'great work'!"  // OK
```

### 4. Przecinki między recenzjami
**ZAWSZE** dodawaj przecinek po każdej recenzji **OPRÓCZ OSTATNIEJ**:

✅ **DOBRZE:**
```javascript
const reviews = [
  { author: "A", text: "..." },  // ← PRZECINEK
  { author: "B", text: "..." },  // ← PRZECINEK
  { author: "C", text: "..." }   // ← BRAK PRZECINKA (ostatnia)
];
```

❌ **ŹLE:**
```javascript
const reviews = [
  { author: "A", text: "..." }   // ← BRAKUJE PRZECINKA
  { author: "B", text: "..." },
];
```

---

## 🚀 Szybki sposób (ChatGPT/Claude)

Jeśli masz dostęp do AI, możesz:

1. **Skopiuj wszystkie 10 reviews z Google Maps**
2. **Wklej do ChatGPT/Claude z promptem:**

```
Przekonwertuj te Google reviews do formatu JavaScript:

[WKLEJ REVIEWS]

Format:
{
  author: "Imię Nazwisko",
  initials: "IN",
  rating: 5,
  text: "Treść recenzji",
  date: "względna data"
}
```

3. **AI wygeneruje gotowy kod** do wklejenia

---

## 📞 Problemy?

### "Nie widzę reviews na Google Maps"
- Upewnij się że link działa: https://www.google.com/maps/place/?q=place_id:ChIJr1j6aRVeyKERtMJqTpRkvQc
- Spróbuj zalogować się na konto Google
- Sprawdź czy reviews są publiczne (w Google My Business)

### "Mam więcej/mniej niż 10 reviews"
- Kod działa z **dowolną liczbą** reviews (minimum 4 dla 4-kolumnowego układu)
- Możesz dodać więcej lub usunąć niektóre

### "Jak zmienić liczbę widocznych kart (teraz 4)?"
Patrz: `CAROUSEL_INSTRUCTIONS.md` → sekcja "Troubleshooting"

---

**Powodzenia!** 🎉
