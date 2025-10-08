const fs = require('fs');

// Wczytaj plik
const data = fs.readFileSync('task.xlsx', 'utf8');
const lines = data.split('\n').slice(1); // Pomiń nagłówek

// Parse danych - usuń apostrofy i zmień na liczby dodatnie
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

console.log(`Załadowano ${clients.length} klientów z zadłużeniem`);

// Funkcja do znajdowania kombinacji sumujących się do target
function findSubsetSum(arr, target, tolerance = 0.01, maxDepth = 10) {
    const results = [];

    function backtrack(start, currentSum, currentSet, depth) {
        // Jeśli suma jest w tolerancji
        if (Math.abs(currentSum - target) < tolerance) {
            results.push([...currentSet]);
            return;
        }

        // Jeśli przekroczyliśmy target lub głębokość
        if (currentSum > target + tolerance || depth >= maxDepth) {
            return;
        }

        // Próbuj dodawać kolejne elementy
        for (let i = start; i < arr.length; i++) {
            currentSet.push(arr[i]);
            backtrack(i + 1, currentSum + arr[i].amount, currentSet, depth + 1);
            currentSet.pop();
        }
    }

    backtrack(0, 0, [], 0);
    return results;
}

// Szukaj dla 9215.29
console.log('\n=== Szukam kombinacji dla 9215.29 ===');
const target1 = 9215.29;
const combinations1 = findSubsetSum(clients, target1, 0.01, 15);

console.log(`\nZnaleziono ${combinations1.length} kombinacji dla ${target1}:`);
combinations1.forEach((combo, idx) => {
    const sum = combo.reduce((acc, c) => acc + c.amount, 0);
    console.log(`\nKombinacja ${idx + 1} (suma: ${sum.toFixed(2)}):`);
    combo.forEach(c => console.log(`  - Client ${c.id}: ${c.amount.toFixed(2)}`));
});

// Szukaj dla 277.20
console.log('\n\n=== Szukam kombinacji dla 277.20 ===');
const target2 = 277.20;
const combinations2 = findSubsetSum(clients, target2, 0.01, 10);

console.log(`\nZnaleziono ${combinations2.length} kombinacji dla ${target2}:`);
combinations2.slice(0, 20).forEach((combo, idx) => {
    const sum = combo.reduce((acc, c) => acc + c.amount, 0);
    console.log(`\nKombinacja ${idx + 1} (suma: ${sum.toFixed(2)}):`);
    combo.forEach(c => console.log(`  - Client ${c.id}: ${c.amount.toFixed(2)}`));
});

if (combinations2.length > 20) {
    console.log(`\n... i ${combinations2.length - 20} więcej kombinacji`);
}

// Zapisz wyniki do pliku JSON
const results = {
    target_9215_29: {
        target: target1,
        found: combinations1.length,
        combinations: combinations1.map(combo => ({
            sum: combo.reduce((acc, c) => acc + c.amount, 0),
            clients: combo
        }))
    },
    target_277_20: {
        target: target2,
        found: combinations2.length,
        combinations: combinations2.map(combo => ({
            sum: combo.reduce((acc, c) => acc + c.amount, 0),
            clients: combo
        }))
    }
};

fs.writeFileSync('sum-analysis-results.json', JSON.stringify(results, null, 2));
console.log('\n\n✅ Wyniki zapisane do: sum-analysis-results.json');
