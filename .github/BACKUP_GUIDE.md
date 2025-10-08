# 🛡️ Przewodnik: Jak nie stracić pracy

## 🚨 Problem
Pracujesz w Codespace kilka dni, wszystko działa... ale zmiany nie są w GitHubie!

---

## ✅ Rozwiązanie: 3 metody

### Metoda 1️⃣: AUTO-BACKUP (uruchom i zapomnij)

**Uruchom w nowym terminalu:**
```bash
./.github/auto-backup.sh
```

**Co robi?**
- Co 10 minut sprawdza czy są zmiany
- Jeśli są → automatycznie zapisuje na GitHub
- Działa w tle, nie przeszkadza w pracy

**Kiedy używać?**
- Zawsze gdy rozpoczynasz pracę
- Chcesz mieć "ubezpieczenie" na wypadek awarii

**Jak zatrzymać?**
- Naciśnij `Ctrl+C` w terminalu

---

### Metoda 2️⃣: RĘCZNE CHECKPOINTY (masz kontrolę)

**Załaduj skróty (raz na sesję):**
```bash
source .github/git-shortcuts.sh
```

**Dostępne komendy:**

```bash
# Zapisz z opisem
backup "dodałem wysyłkę SMS"

# Szybki zapis bez opisu
save

# Pokaż co się zmieniło
changes

# Cofnij niezapisane zmiany
undo

# Wróć do poprzedniej wersji
rollback
```

**Przykład użycia:**
```bash
# Zaczynasz dzień
source .github/git-shortcuts.sh

# Pracujesz... edytujesz pliki...

# Co 30-60 min zapisujesz checkpoint
backup "sync z Fakturownią działa"

# Jeszcze praca...

# Coś się zepsuło? Cofnij!
undo

# Albo wróć do wcześniejszej wersji
rollback
```

---

### Metoda 3️⃣: TRADYCYJNY GIT (najprostsza)

**Co 30-60 minut:**
```bash
git add .
git commit -m "checkpoint: opis co zrobiłeś"
git push origin main
```

**Szybszy wariant:**
```bash
git add . && git commit -m "save" && git push
```

---

## 🎯 ZALECANY WORKFLOW

### Na początek dnia:
```bash
# Terminal 1 - twoja normalna praca
cd /workspaces/Carebiuro_windykacja

# Terminal 2 - auto-backup w tle
./.github/auto-backup.sh
```

### Podczas pracy:
- Terminal 2 pracuje w tle → auto-zapisuje co 10 min
- Ty w Terminal 1 codujesz normalnie
- Dodatkowo co godzinę możesz ręcznie zrobić: `git add . && git commit -m "checkpoint" && git push`

### Koniec dnia:
- Naciśnij `Ctrl+C` w Terminal 2 (zatrzymuje auto-backup)
- Sprawdź: `git log --oneline -5` (ostatnie zapisy)
- Gotowe! Wszystko na GitHubie ✅

---

## 📋 Sprawdź czy zmiany są na GitHubie

**W terminalu:**
```bash
git log --oneline -5
```
Pokaze ostatnie commity.

**W przeglądarce:**
https://github.com/dgnernvsinjsbt/Carebiuro_windykacja/commits/main

Jeśli widzisz swoje commity → wszystko OK! ✅

---

## 🆘 Ratowanie sytuacji

### "Nie zapisałem zmian od 3 dni!"
```bash
git add .
git commit -m "emergency backup: $(date)"
git push origin main
```

### "Coś się zepsuło, chcę wrócić do wersji sprzed godziny"
```bash
git log --oneline -20          # znajdź hash commita
git reset --hard abc1234       # wróć do tego commita
git push origin main --force   # wypchnij na GitHub
```

### "Jak sprawdzić co zmieniłem?"
```bash
git status           # pokaże co NIE jest zapisane
git log --oneline    # pokaże zapisane commity
git diff             # pokaże dokładne zmiany w plikach
```

---

## 💡 Pro Tips

1. **Auto-backup zawsze włączony**
   - Dodaj do `~/.bashrc`: `cd /workspaces/Carebiuro_windykacja && ./.github/auto-backup.sh &`

2. **Alias w terminalu**
   ```bash
   echo 'alias save="git add . && git commit -m \"quick save\" && git push"' >> ~/.bashrc
   ```
   Potem wystarczy wpisać: `save`

3. **Sprawdzaj GitHub raz dziennie**
   - https://github.com/dgnernvsinjsbt/Carebiuro_windykacja
   - Czy są dzisiejsze commity? ✅

---

## ⚠️ Czego NIE robić

❌ Nie używaj `git reset --hard` jeśli nie wiesz co robisz
❌ Nie używaj `--force` bez backupu
❌ Nie commituj plików `.env` z hasłami
❌ Nie czekaj 7 dni z zapisem na GitHub

✅ Zapisuj często, śpij spokojnie

---

## 🎓 Najważniejsze

**Zasada 3-2-1:**
- **Co 30 min** → sprawdź `git status` (czy są zmiany)
- **Co 2 godziny** → zapisz checkpoint
- **Co 1 dzień** → sprawdź GitHub czy wszystko tam jest

**Złota zasada:**
> Jeśli praca zajęła Ci > 30 minut, powinna być na GitHubie!

---

Masz pytania? Wpisz:
- `changes` → co się zmieniło
- `save` → zapisz teraz
- `git log` → pokaż historię
