const fs = require('fs');

// Wczytaj plik
const data = fs.readFileSync('task.xlsx', 'utf8');
const lines = data.split('\n').slice(1);

// Parse danych
const clients = [];
lines.forEach(line => {
    const parts = line.trim().split('\t');
    if (parts.length === 2) {
        const id = parts[0].trim();
        const balance = parts[1].trim().replace(/'/g, '').replace(',', '.');
        const amount = Math.abs(parseFloat(balance));
        if (!isNaN(amount) && amount > 0) {
            clients.push({ id, amount });
        }
    }
});

// Sortuj malejąco dla szybszego pruningu
clients.sort((a, b) => b.amount - a.amount);

console.log(`Załadowano ${clients.length} klientów`);
console.log(`Największe zadłużenie: ${clients[0].amount.toFixed(2)}`);
console.log(`Najmniejsze zadłużenie: ${clients[clients.length - 1].amount.toFixed(2)}`);

// Funkcja do znajdowania kombinacji (zoptymalizowana)
function findCombinations(arr, target, tolerance = 0.01, maxCombos = 50, maxSize = 8) {
    const results = [];
    let checked = 0;

    function search(start, sum, combo, depth) {
        checked++;

        // Progress co 100k iteracji
        if (checked % 100000 === 0) {
            console.log(`Sprawdzono ${checked} kombinacji, znaleziono ${results.length}`);
        }

        // Sprawdź czy znaleźliśmy match
        const diff = Math.abs(sum - target);
        if (diff < tolerance) {
            results.push({
                clients: [...combo],
                sum: sum,
                diff: diff
            });
            console.log(`✓ Znaleziono! Suma: ${sum.toFixed(2)} (${combo.length} pozycji)`);

            if (results.length >= maxCombos) {
                return true; // Stop search
            }
        }

        // Pruning
        if (sum > target + tolerance) return false;
        if (depth >= maxSize) return false;
        if (start >= arr.length) return false;

        // Próbuj dodać kolejne elementy
        for (let i = start; i < arr.length && results.length < maxCombos; i++) {
            // Skip jeśli nawet najmniejsza pozostała wartość przekroczy target
            if (sum + arr[i].amount > target + tolerance) {
                continue;
            }

            combo.push(arr[i]);
            const shouldStop = search(i + 1, sum + arr[i].amount, combo, depth + 1);
            combo.pop();

            if (shouldStop) return true;
        }

        return false;
    }

    search(0, 0, [], 0);
    console.log(`\nSprawdzono łącznie ${checked} kombinacji`);
    return results;
}

// Szukaj dla 277.20 (mniejsza liczba - szybsze)
console.log('\n\n━━━ Szukam kombinacji dla 277.20 ━━━');
const target2 = 277.20;
const startTime2 = Date.now();
const results2 = findCombinations(clients, target2, 0.02, 20, 6);
const time2 = ((Date.now() - startTime2) / 1000).toFixed(2);

console.log(`\n✅ Znaleziono ${results2.length} kombinacji w ${time2}s`);
results2.forEach((result, idx) => {
    console.log(`\nKombinacja ${idx + 1} (suma: ${result.sum.toFixed(2)}, różnica: ${result.diff.toFixed(4)}):`);
    result.clients.forEach(c => console.log(`  Client ${c.id}: ${c.amount.toFixed(2)}`));
});

// Szukaj dla 9215.29
console.log('\n\n━━━ Szukam kombinacji dla 9215.29 ━━━');
const target1 = 9215.29;
const startTime1 = Date.now();
const results1 = findCombinations(clients, target1, 0.02, 10, 8);
const time1 = ((Date.now() - startTime1) / 1000).toFixed(2);

console.log(`\n✅ Znaleziono ${results1.length} kombinacji w ${time1}s`);
results1.forEach((result, idx) => {
    console.log(`\nKombinacja ${idx + 1} (suma: ${result.sum.toFixed(2)}, różnica: ${result.diff.toFixed(4)}):`);
    result.clients.forEach(c => console.log(`  Client ${c.id}: ${c.amount.toFixed(2)}`));
});

// Zapisz wyniki
const output = {
    analyzed_at: new Date().toISOString(),
    total_clients: clients.length,
    targets: {
        target_277_20: {
            target: target2,
            found: results2.length,
            time_seconds: parseFloat(time2),
            combinations: results2
        },
        target_9215_29: {
            target: target1,
            found: results1.length,
            time_seconds: parseFloat(time1),
            combinations: results1
        }
    }
};

fs.writeFileSync('sum-analysis-results.json', JSON.stringify(output, null, 2));
console.log('\n\n💾 Wyniki zapisane do: sum-analysis-results.json');
