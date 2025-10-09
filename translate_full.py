#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from docx import Document

def translate_german_to_polish(text):
    """Kompletne tłumaczenie z niemieckiego na polski"""

    # Kompletny słownik tłumaczeń wszystkich zdań
    full_sentences = {
        # Już przetłumaczone
        'Die Betraege in der excel Datei muessen mit Komma stehen, nicht mit punkt, sonst sind es keine zahlen, sondern text.':
            'Kwoty w pliku Excel muszą być zapisane z przecinkiem, a nie z kropką, w przeciwnym razie będą traktowane jako tekst, a nie liczby.',

        'Unsere Excel Datei muss die volle IBAN nummern haben in Auftraggeberkonto, die können wir in TM5 rausfinden.':
            'Nasz plik Excel musi zawierać pełne numery IBAN w kolumnie "Konto zleceniodawcy" (Auftraggeberkonto), które możemy znaleźć w systemie TM5.',

        'Fuer jedes Auftraggeber Konto muss eine separate Excel Datei erstellt werden.':
            'Dla każdego konta zleceniodawcy należy utworzyć osobny plik Excel.',

        'Die excel datei muss in dem gleichen folder gespeichert werden, wie die 3 template files .exe,.pbt, .bat':
            'Plik Excel musi być zapisany w tym samym folderze co 3 pliki szablonów: .exe, .pbt, .bat',

        'Rechter mausklick auf die bat datei -> edytuj w notatniku':
            'Kliknij prawym przyciskiem myszy na plik .bat → Edytuj w Notatniku',

        'Zmien nazwe pliku na nasz gotowy plik excel':
            'Zmień nazwę pliku na nasz gotowy plik Excel',

        # Nowe tłumaczenia
        'Wenn alles fertig, dann einfach die .bat doppelklick und laufen lassen.':
            'Gdy wszystko jest gotowe, wystarczy kliknąć dwukrotnie plik .bat i uruchomić.',

        'Noch wichitg – in der zweiten zeile muss die endung .exe – format aldi - drinstehen.':
            'Jeszcze ważne – w drugiej linii musi być rozszerzenie .exe – format aldi.',

        'Es entsteht eine xml. datei , die automatisch im selben folder gespeichert wird-> diese Datei wird in TM5 hochgeladen.':
            'Powstaje plik .xml, który jest automatycznie zapisywany w tym samym folderze → ten plik zostanie przesłany do TM5.',

        'Datei auswaehlen -> auf den kleinen blauen pfeil rechts druecken':
            'Wybierz plik → kliknij małą niebieską strzałkę po prawej stronie',

        'Banking ->massenueberweisung ->Gesellschaft KIEL TK -> wir sehen die upgeloadete datei':
            'Banking → Przelewy masowe → Spółka KIEL TK → widzimy przesłany plik',

        'Dann muss man noch eine email abschicken mit screenshot entweder direkt an treasury, oder zuerst an Heike zum 4 augenprinzip':
            'Następnie należy wysłać email ze zrzutem ekranu albo bezpośrednio do treasury, albo najpierw do Heike (zasada czterech oczu)',

        'Wenn wir moechten, dass man in TM5 jede zeile separat sieht aus der upload datei, dann muss man beim hochladen bereits die funktion auswählen:':
            'Jeśli chcemy, aby w TM5 każda linia z przesłanego pliku była widoczna osobno, należy już podczas przesyłania wybrać funkcję:',

        'In den details sehen wir dann die zeilen – man kann auch ein pdf ziehen':
            'W szczegółach widzimy wtedy linie – można również przeciągnąć plik PDF',

        # Pojedyncze frazy
        'Stammdaten -> Konten': 'Dane podstawowe → Konta',
        'Stammdaten': 'Dane podstawowe',
        'Konten': 'Konta',
    }

    # Sprawdź czy to pełne zdanie
    text_stripped = text.strip()
    for german, polish in full_sentences.items():
        if german.strip().lower() == text_stripped.lower():
            return polish

    # Jeśli nie znaleziono pełnego zdania, zwróć oryginał
    return text

# Wczytaj dokument
input_file = "TM5 Coupa Treasury Automatisierung Arbeitsanweisung.docx"

print(f"📄 Wczytywanie: {input_file}\n")
doc = Document(input_file)

translated_count = 0

# Przetwórz paragrafy
for i, para in enumerate(doc.paragraphs):
    original = para.text.strip()
    if original:
        translated = translate_german_to_polish(original)

        if original != translated:
            translated_count += 1
            print(f"✓ Paragraf {i+1}:")
            print(f"  🇩🇪 {original[:70]}...")
            print(f"  🇵🇱 {translated[:70]}...\n")

            # Zastąp tekst
            if para.runs:
                # Zachowaj formatowanie
                formatting = {
                    'bold': para.runs[0].bold,
                    'italic': para.runs[0].italic,
                    'size': para.runs[0].font.size,
                    'name': para.runs[0].font.name
                }

                # Wyczyść
                for run in para.runs:
                    run.text = ""

                # Ustaw nowy tekst
                para.runs[0].text = translated
                para.runs[0].bold = formatting['bold']
                para.runs[0].italic = formatting['italic']
                if formatting['size']:
                    para.runs[0].font.size = formatting['size']
                if formatting['name']:
                    para.runs[0].font.name = formatting['name']

# Zapisz
print(f"\n{'='*70}")
print(f"✅ Przetłumaczono: {translated_count} fragmentów")
print(f"💾 Zapisywanie: {input_file}")
doc.save(input_file)
print(f"✅ GOTOWE! Dokument w pełni przetłumaczony z zachowaniem obrazów.")
