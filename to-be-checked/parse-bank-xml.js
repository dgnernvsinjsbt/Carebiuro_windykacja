// Parser XML wyciągu bankowego do struktury tabeli (bez DOMParser)
const xmlData = $input.first().json.data;

// Funkcja do wyciągania wartości z XML używając regex
function extractXMLValue(xml, tagName, attributeName = null) {
    if (attributeName) {
        const attrRegex = new RegExp(`<${tagName}[^>]*${attributeName}="([^"]*)"`, 'i');
        const match = xml.match(attrRegex);
        return match ? match[1] : '';
    } else {
        const regex = new RegExp(`<${tagName}[^>]*>([^<]*)</${tagName}>`, 'i');
        const match = xml.match(regex);
        return match ? match[1].trim() : '';
    }
}

// Funkcja do wyciągania wszystkich wystąpień tagu
function extractAllXMLBlocks(xml, tagName) {
    const regex = new RegExp(`<${tagName}[^>]*>(.*?)</${tagName}>`, 'gis');
    const matches = [];
    let match;

    while ((match = regex.exec(xml)) !== null) {
        matches.push(match[1]);
    }

    return matches;
}

// Wyciągnij CreDtTm z nagłówka (dla godziny)
const creDtTmMatch = xmlData.match(/<CreDtTm>([^<]*)<\/CreDtTm>/i);
const messageCreationTime = creDtTmMatch ? creDtTmMatch[1] : '';

// Wyciągnij wszystkie transakcje (bloki Ntry)
const entryBlocks = extractAllXMLBlocks(xmlData, 'Ntry');
const transactions = [];

console.log(`Znaleziono ${entryBlocks.length} transakcji w XML`);
console.log(`Czas utworzenia wiadomości: ${messageCreationTime}`);

entryBlocks.forEach((entryXML, index) => {
    try {
        // Podstawowe dane transakcji
        const amount = extractXMLValue(entryXML, 'Amt');
        const currency = entryXML.match(/<Amt[^>]*Ccy="([^"]*)"/) ? entryXML.match(/<Amt[^>]*Ccy="([^"]*)"/)[1] : 'EUR';
        const creditDebitInd = extractXMLValue(entryXML, 'CdtDbtInd');

        // Poprawne wyciąganie dat - szukamy wzorca <BookgDt><Dt>DATA</Dt></BookgDt>
        const bookingDateMatch = entryXML.match(/<BookgDt>\s*<Dt>([^<]*)<\/Dt>/i);
        const bookingDate = bookingDateMatch ? bookingDateMatch[1] : '';

        const valueDateMatch = entryXML.match(/<ValDt>\s*<Dt>([^<]*)<\/Dt>/i);
        const valueDate = valueDateMatch ? valueDateMatch[1] : '';

        // Pobierz blok TxDtls
        const txDetailsMatch = entryXML.match(/<TxDtls>(.*?)<\/TxDtls>/is);

        if (txDetailsMatch) {
            const txDetailsXML = txDetailsMatch[1];

            // Referencje
            const instrId = extractXMLValue(txDetailsXML, 'InstrId');
            const endToEndId = extractXMLValue(txDetailsXML, 'EndToEndId');

            // Dane dłużnika/płatnika - poprawa wyciągania nazwy
            const debtorNameMatch = txDetailsXML.match(/<Dbtr>\s*<Nm>([^<]*)<\/Nm>/i);
            const debtorName = debtorNameMatch ? debtorNameMatch[1] : '';

            const debtorIBAN = extractXMLValue(txDetailsXML, 'IBAN');

            // Sprawdź czy jest inne konto (Othr Id)
            let otherAccount = '';
            const otherMatch = txDetailsXML.match(/<Othr>\s*<Id>([^<]*)<\/Id>/i);
            if (otherMatch) {
                otherAccount = otherMatch[1];
            }

            // Adres dłużnika
            const addressMatch = txDetailsXML.match(/<AdrLine>([^<]*)<\/AdrLine>/i);
            const debtorAddress = addressMatch ? addressMatch[1] : '';

            // Opis transakcji
            const description = extractXMLValue(txDetailsXML, 'Ustrd');

            // Formatowanie daty dla Google Sheets (YYYY-MM-DD)
            const formatDate = (dateStr) => {
                if (!dateStr) return '';
                try {
                    const date = new Date(dateStr);
                    return date.toISOString().split('T')[0];
                } catch (e) {
                    return dateStr;
                }
            };

            // TIMESTAMP DO SORTOWANIA - używamy BookgDt + czas z CreDtTm
            // Jeśli BookgDt ma tylko datę, łączymy z godziną z CreDtTm
            const createSortableTimestamp = (dateStr, creationTime) => {
                if (!dateStr) return '';

                try {
                    // Jeśli dateStr zawiera już godzinę (format ISO z T)
                    if (dateStr.includes('T')) {
                        return new Date(dateStr).toISOString();
                    }

                    // Jeśli mamy tylko datę (YYYY-MM-DD), dodaj czas z CreDtTm
                    if (creationTime && creationTime.includes('T')) {
                        const timePart = creationTime.split('T')[1]; // Wyciągnij HH:MM:SS
                        const fullDateTime = `${dateStr}T${timePart}`;
                        return new Date(fullDateTime).toISOString();
                    }

                    // Fallback - dodaj północ jako godzinę
                    return new Date(`${dateStr}T00:00:00`).toISOString();
                } catch (e) {
                    console.log(`Błąd tworzenia timestamp: ${e.message}`);
                    return dateStr;
                }
            };

            // Określenie typu operacji
            const operationType = creditDebitInd === 'CRDT' ? 'Credit' : 'Debit';

            // Numer konta (IBAN lub inne)
            const accountNumber = debtorIBAN || otherAccount;

            // Utwórz timestamp do sortowania
            const sortableTimestamp = createSortableTimestamp(bookingDate, messageCreationTime);

            const transaction = {
                // POLE DO SORTOWANIA - najważniejsze dla Google Sheets
                timestamp: sortableTimestamp,

                // Kolumny zgodne ze screeniem
                data_transakcji: formatDate(bookingDate),
                data_ksiegowania: formatDate(valueDate),
                typ_operacji: operationType,
                kwota: parseFloat(amount) || 0,
                waluta: currency,
                kontrahent: debtorName,
                numer_konta_kontrahenta: accountNumber,
                cel_platnosci: description,
                referencja: instrId,
                ref_no: endToEndId || instrId,

                // Dodatkowe pola
                adres_kontrahenta: debtorAddress,
                kwota_formatted: `${amount} ${currency}`,

                // Debug info
                transaction_index: index + 1
            };

            transactions.push(transaction);

        } else {
            console.log(`Brak TxDtls dla transakcji ${index + 1}`);
        }

    } catch (error) {
        console.log(`Błąd przetwarzania transakcji ${index + 1}: ${error.message}`);
    }
});

// Sortuj transakcje po timestamp (najstarsze pierwsze - chronologicznie)
transactions.sort((a, b) => {
    return new Date(a.timestamp) - new Date(b.timestamp);
});

console.log(`Pomyślnie przetworzono ${transactions.length} transakcji`);

// Pokaż przykład pierwszej i ostatniej transakcji dla debugowania
if (transactions.length > 0) {
    console.log('Pierwsza transakcja (najstarsza):', JSON.stringify(transactions[0], null, 2));
    console.log('Ostatnia transakcja (najnowsza):', JSON.stringify(transactions[transactions.length - 1], null, 2));
}

// Zwróć przetworzone transakcje
return transactions.map(transaction => ({
    json: transaction
}));
