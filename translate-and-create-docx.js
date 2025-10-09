const { Document, Paragraph, TextRun, ImageRun, Packer } = require("docx");
const fs = require("fs");

// Tłumaczenie treści
const translatedContent = `
TM5 Coupa Treasury - Instrukcja automatyzacji

Kwoty w pliku Excel muszą być zapisane z przecinkiem, a nie z kropką, w przeciwnym razie będą traktowane jako tekst, a nie liczby.

Nasz plik Excel musi zawierać pełne numery IBAN w polu Konto zleceniodawcy, które możemy znaleźć w TM5.

Dla każdego konta zleceniodawcy należy utworzyć osobny plik Excel.

TM5

Dane podstawowe -> Konta
`;

// Tworzenie dokumentu Word
const doc = new Document({
    sections: [{
        properties: {},
        children: [
            new Paragraph({
                children: [
                    new TextRun({
                        text: "TM5 Coupa Treasury - Instrukcja automatyzacji",
                        bold: true,
                        size: 32
                    })
                ]
            }),
            new Paragraph({
                children: [new TextRun({ text: "" })]
            }),
            new Paragraph({
                children: [
                    new TextRun({
                        text: "Kwoty w pliku Excel muszą być zapisane z przecinkiem, a nie z kropką, w przeciwnym razie będą traktowane jako tekst, a nie liczby."
                    })
                ]
            }),
            new Paragraph({
                children: [new TextRun({ text: "" })]
            }),
            new Paragraph({
                children: [
                    new TextRun({
                        text: "Nasz plik Excel musi zawierać pełne numery IBAN w polu Konto zleceniodawcy (Auftraggeberkonto), które możemy znaleźć w TM5."
                    })
                ]
            }),
            new Paragraph({
                children: [new TextRun({ text: "" })]
            }),
            new Paragraph({
                children: [
                    new TextRun({
                        text: "Dla każdego konta zleceniodawcy należy utworzyć osobny plik Excel."
                    })
                ]
            }),
            new Paragraph({
                children: [new TextRun({ text: "" })]
            }),
            new Paragraph({
                children: [
                    new TextRun({
                        text: "TM5",
                        bold: true,
                        size: 28
                    })
                ]
            }),
            new Paragraph({
                children: [new TextRun({ text: "" })]
            }),
            new Paragraph({
                children: [
                    new TextRun({
                        text: "Stammdaten (Dane podstawowe) -> Konten (Konta)"
                    })
                ]
            }),
            new Paragraph({
                children: [new TextRun({ text: "" })]
            }),
            new Paragraph({
                children: [
                    new TextRun({
                        text: "[Tutaj znajdował się obraz z oryginału - obrazy muszą być dodane ręcznie]",
                        italics: true
                    })
                ]
            })
        ]
    }]
});

// Zapisywanie pliku
Packer.toBuffer(doc).then(buffer => {
    fs.writeFileSync("TM5 Coupa Treasury Automatisierung Arbeitsanweisung.docx", buffer);
    console.log("Dokument został przetłumaczony i zapisany!");
});
