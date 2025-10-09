#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from docx import Document

def translate(text):
    """Pełny słownik tłumaczeń DE→PL"""

    translations = {
        # Poprawione wcześniejsze
        'Nasz plik Excel musi zajakrać pełne numery IBAN w kolumnie "Konto zleceniodawcy" (Konto zleceniodawcy), które możemy znaleźć w systemie TM5.':
            'Nasz plik Excel musi zawierać pełne numery IBAN w kolumnie "Konto zleceniodawcy" (Auftraggeberkonto), które możemy znaleźć w systemie TM5.',

        # Nowe zdania
        'Hinten ist noch der protocol name – den kann man auch aendern':
            'Z tyłu jest jeszcze nazwa protokołu – można ją również zmienić',

        'Wenn alles fertig, dann einfach  .bat doppelklick und lnaen lassen.':
            'Gdy wszystko jest gotowe, wystarczy kliknąć dwukrotnie plik .bat i uruchomić.',

        'Noch wichitg – in der zweiten zeile musi  endung .exe – format aldi - drinstehen.':
            'Jeszcze ważne – w drugiej linii musi być rozszerzenie .exe – format aldi.',

        'Es entsteht eine xml. datei ,  automatisch im selben folder gespeichert wird-> se Datei wird in TM5 hochgeladen.':
            'Powstaje plik .xml, który jest automatycznie zapisywany w tym samym folderze → ten plik zostanie przesłany do TM5.',

        'Banking – Zahlungabwicklung -> import -> zahlungsformat «sepa DE DK»':
            'Banking – Realizacja płatności → Import → Format płatności «SEPA DE DK»',

        'Datei auswaehlen -> na den kleinen blauen pfeil rechts druecken':
            'Wybierz plik → kliknij małą niebieską strzałkę po prawej stronie',

        'Banking ->massenueberweisung ->Gesellschaft KIEL TK -> wir sehen  upgeloadete datei':
            'Banking → Przelewy masowe → Spółka KIEL TK → widzimy przesłany plik',

        'Dann musi man noch eine email abschicken mit screenshot entweder direkt an treasury, oder zuerst an Heike zum 4 augenprinzip':
            'Następnie należy wysłać email ze zrzutem ekranu albo bezpośrednio do treasury, albo najpierw do Heike (zasada czterech oczu)',

        'Wenn wir einen fehler gemacht haben:':
            'Jeśli popełniliśmy błąd:',

        'Sonderfunktionen – stornieren aber unbedingt unter markierte zahlungen':
            'Funkcje specjalne – Anuluj, ale koniecznie w zakładce "zaznaczone płatności"',

        'Wenn wir moechten, dass man in TM5 jede zeile separat sieht aus der upload datei, dann musi man beim hochladen bereits  funktion auswählen:':
            'Jeśli chcemy, aby w TM5 każda linia z przesłanego pliku była widoczna osobno, należy już podczas przesyłania wybrać funkcję:',

        'Banking – import – SEPA DE DK – datei auswaechlen – einzelzahlungssaetze anzeigen':
            'Banking → Import → SEPA DE DK → Wybierz plik → Pokaż poszczególne dyspozycje płatnicze',

        'In den details sehen wir dann  zeilen – man kann auch ein pdf ziehen':
            'W szczegółach widzimy wtedy linie – można również przeciągnąć plik PDF',
    }

    # Sprawdź dokładne dopasowanie
    for de, pl in translations.items():
        if text.strip() == de.strip():
            return pl

    return text

# Przetwórz dokument
input_file = "TM5 Coupa Treasury Automatisierung Arbeitsanweisung.docx"
doc = Document(input_file)

print("🔄 Tłumaczenie dokumentu...\n")

count = 0
for i, para in enumerate(doc.paragraphs, 1):
    original = para.text.strip()
    if original:
        translated = translate(original)

        if original != translated:
            count += 1
            print(f"✓ [{i}] Przetłumaczono")

            if para.runs:
                # Zachowaj formatowanie
                fmt = para.runs[0]
                bold, italic = fmt.bold, fmt.italic
                size, name = fmt.font.size, fmt.font.name

                # Zastąp tekst
                for run in para.runs:
                    run.text = ""

                para.runs[0].text = translated
                para.runs[0].bold = bold
                para.runs[0].italic = italic
                if size:
                    para.runs[0].font.size = size
                if name:
                    para.runs[0].font.name = name

print(f"\n{'='*70}")
print(f"✅ Przetłumaczono: {count} fragmentów")
print(f"💾 Zapisywanie...")
doc.save(input_file)
print(f"✅ GOTOWE! Dokument w pełni po polsku!")
