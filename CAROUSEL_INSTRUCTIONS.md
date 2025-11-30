# Google Reviews Carousel - Instrukcja Obsługi

## 📋 Spis treści
1. [Jak wdrożyć w Go High Level](#jak-wdrożyć-w-go-high-level)
2. [Jak pobrać prawdziwe reviews z Google](#jak-pobrać-prawdziwe-reviews-z-google)
3. [Jak edytować reviews w kodzie](#jak-edytować-reviews-w-kodzie)
4. [Jak dostosować ustawienia karuzeli](#jak-dostosować-ustawienia-karuzeli)
5. [Troubleshooting](#troubleshooting)

---

## 🚀 Jak wdrożyć w Go High Level

### Krok 1: Otwórz plik HTML
1. Otwórz plik `google-reviews-carousel.html`
2. Zaznacz **cały kod** (Ctrl+A / Cmd+A)
3. Skopiuj (Ctrl+C / Cmd+C)

### Krok 2: Dodaj do Go High Level
1. Zaloguj się do Go High Level
2. Otwórz Page Builder / Funnel Builder
3. Przeciągnij element **"Custom Code"** na stronę
4. Kliknij na element, aby otworzyć edytor
5. **Wklej cały skopiowany kod** (Ctrl+V / Cmd+V)
6. Kliknij **"Save"**

### Krok 3: Podgląd i publikacja
1. Kliknij **"Preview"** aby zobaczyć karuzelę w akcji
2. Sprawdź czy karuzela przewija się automatycznie
3. Najedź myszką - powinna się zatrzymać (pause on hover)
4. Jeśli wszystko działa → **"Publish"**

✅ **Gotowe!** Karuzela powinna działać na Twojej stronie.

---

## 📥 Jak pobrać prawdziwe reviews z Google

### Metoda 1: Bezpośredni link (NAJŁATWIEJSZA)
1. Otwórz ten link w przeglądarce:
   ```
   https://www.google.com/maps/place/?q=place_id:ChIJr1j6aRVeyKERtMJqTpRkvQc
   ```

2. Kliknij na zakładkę **"Reviews"** (Recenzje)

3. Przewiń w dół i znajdź najlepsze 5-gwiazdkowe recenzje

4. Dla każdej recenzji skopiuj:
   - **Imię autora** (np. "John Smith")
   - **Tekst recenzji** (cały komentarz)
   - **Data** (np. "2 months ago")
   - **Inicjały** (np. "JS" - pierwsza litera imienia + nazwiska)

5. Zapisz je w notatniku lub przejdź do sekcji [Jak edytować reviews](#jak-edytować-reviews-w-kodzie)

### Metoda 2: Google My Business Dashboard
1. Zaloguj się do Google My Business
2. Wybierz swoją firmę
3. Przejdź do sekcji **"Reviews"**
4. Skopiuj wybrane recenzje

---

## ✏️ Jak edytować reviews w kodzie

### Lokalizacja w kodzie
W pliku `google-reviews-carousel.html` znajdź sekcję:

```javascript
// ============================================
// REVIEWS DATA - EDIT THIS SECTION
// ============================================
const reviews = [
  {
    author: "Michael Caito",
    initials: "MC",
    rating: 5,
    text: "Beautiful over look with all...",
    date: "4 year ago"
  },
  // ... więcej recenzji
];
```

### Format pojedynczej recenzji:
```javascript
{
  author: "Imię Nazwisko",        // WYMAGANE: Pełne imię autora
  initials: "IN",                 // OPCJONALNE: Inicjały (auto-generowane jeśli brak)
  rating: 5,                      // WYMAGANE: Ocena 1-5 (zwykle 5)
  text: "Treść recenzji...",      // WYMAGANE: Pełny tekst komentarza
  date: "3 months ago"            // WYMAGANE: Względna data (np. "2 weeks ago")
}
```

### Przykład dodania nowej recenzji:

**PRZED:**
```javascript
const reviews = [
  {
    author: "Michael Caito",
    initials: "MC",
    rating: 5,
    text: "Beautiful over look...",
    date: "4 year ago"
  }
];
```

**PO (dodanie nowej recenzji):**
```javascript
const reviews = [
  {
    author: "Michael Caito",
    initials: "MC",
    rating: 5,
    text: "Beautiful over look...",
    date: "4 year ago"
  },
  {
    author: "Anna Kowalska",
    initials: "AK",
    rating: 5,
    text: "Świetna obsługa i profesjonalizm!",
    date: "1 month ago"
  }
];
```

### ⚠️ WAŻNE:
- **Zawsze** pozostaw przecinek po każdej recenzji (oprócz ostatniej!)
- **Użyj cudzysłowów** wokół tekstu: `"tak"` nie `'tak'`
- **Rating** to liczba bez cudzysłowów: `5` nie `"5"`
- Jeśli tekst zawiera cudzysłów, użyj `\"`: `"He said \"wow\"!"`

---

## ⚙️ Jak dostosować ustawienia karuzeli

### Lokalizacja w kodzie
Znajdź sekcję:

```javascript
// ============================================
// CONFIGURATION - EASY TO EDIT
// ============================================
const CONFIG = {
  autoScrollInterval: 6000,  // 6 seconds between slides
  transitionSpeed: 1000,     // 1 second transition animation
  pauseOnHover: true         // Pause carousel on hover
};
```

### Dostępne opcje:

#### 1. **autoScrollInterval** (czas między slajdami)
- **Domyślnie:** `6000` (6 sekund)
- **Szybciej:** `4000` (4 sekundy)
- **Wolniej:** `8000` (8 sekund)

```javascript
autoScrollInterval: 5000,  // 5 sekund
```

#### 2. **transitionSpeed** (prędkość animacji)
- **Domyślnie:** `1000` (1 sekunda)
- **Szybciej:** `600` (0.6 sekundy)
- **Wolniej:** `1500` (1.5 sekundy)

```javascript
transitionSpeed: 800,  // Szybsza animacja
```

#### 3. **pauseOnHover** (zatrzymanie przy najechaniu)
- **Domyślnie:** `true` (zatrzymuje się)
- **Wyłącz:** `false` (nie zatrzymuje się)

```javascript
pauseOnHover: false,  // Karuzela nie zatrzyma się przy hover
```

---

## 🎨 Jak zmienić kolory i style

### Zmiana koloru tła sekcji:
Znajdź:
```css
.reviews-carousel-container {
  background-color: #f9f9f9;  /* ← ZMIEŃ TEN KOLOR */
}
```

### Zmiana koloru avatarów:
Znajdź:
```css
.review-avatar {
  background: #00A676;  /* ← ZMIEŃ TEN KOLOR (zielony) */
  color: white;         /* ← ZMIEŃ KOLOR LITER */
}
```

### Zmiana koloru gwiazdek:
Znajdź:
```css
.stars {
  color: #FFC107;  /* ← ZMIEŃ TEN KOLOR (żółty Google) */
}
```

---

## 🔧 Troubleshooting

### Problem: Karuzela nie przewija się automatycznie
**Rozwiązanie:**
1. Sprawdź czy w kodzie jest `autoScrollInterval` większe niż 0
2. Otwórz Console w przeglądarce (F12) i sprawdź błędy JavaScript
3. Upewnij się że cały kod został skopiowany (od `<style>` do `</script>`)

### Problem: Recenzje nie są widoczne
**Rozwiązanie:**
1. Sprawdź czy w `const reviews = [...]` są jakiekolwiek recenzje
2. Upewnij się że każda recenzja ma poprawny format (patrz sekcja "Jak edytować")
3. Sprawdź czy nie brakuje przecinków między recenzjami

### Problem: Karuzela "skacze" zamiast płynnie przewijać
**Rozwiązanie:**
1. Zwiększ `transitionSpeed` do `1200` lub więcej
2. Sprawdź czy przypadkiem nie usunąłeś sekcji CSS `transition: transform 1s ease-in-out;`

### Problem: Na mobile pokazuje się tylko 1 karta zamiast 4
**Rozwiązanie:**
To jest **normalne zachowanie** - responsywny design:
- **Desktop (>1024px):** 4 karty
- **Tablet (768-1024px):** 3 karty
- **Mobile (<768px):** 1 karta

Jeśli chcesz zawsze pokazywać 4 karty, usuń całą sekcję `@media` z CSS (niezalecane).

### Problem: W Go High Level kod nie działa
**Rozwiązanie:**
1. Sprawdź czy użyłeś elementu **"Custom Code"** (nie "HTML")
2. Upewnij się że wkleiłeś **CAŁY** kod (od pierwszej linii do ostatniej)
3. Sprawdź czy Go High Level nie blokuje JavaScript (niektóre plany mają ograniczenia)
4. Spróbuj opublikować stronę i sprawdzić na live URL (nie tylko preview)

---

## 📞 Potrzebujesz pomocy?

Jeśli masz problemy:
1. Sprawdź najpierw sekcję [Troubleshooting](#troubleshooting)
2. Otwórz Console w przeglądarce (F12) i poszukaj błędów
3. Upewnij się że używasz najnowszej wersji kodu

---

## 📝 Checklist wdrożenia

- [ ] Skopiowałem cały kod z `google-reviews-carousel.html`
- [ ] Wkleiłem kod do Go High Level Custom Code element
- [ ] Sprawdziłem preview - karuzela przewija się automatycznie
- [ ] Sprawdziłem pause on hover - działa
- [ ] (Opcjonalnie) Zastąpiłem przykładowe reviews prawdziwymi z Google
- [ ] (Opcjonalnie) Dostosowałem timing/kolory do moich preferencji
- [ ] Opublikowałem stronę i sprawdziłem na live URL

---

**Powodzenia! 🚀**
