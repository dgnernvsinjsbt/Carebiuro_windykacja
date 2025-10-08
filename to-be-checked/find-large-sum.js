const fs = require('fs');

// Wczytaj plik
const data = fs.readFileSync('task.xlsx', 'utf8');
const lines = data.split('\n').slice(1);

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

// Sortuj malejąco
clients.sort((a, b) => b.amount - a.amount);

console.log(`Załadowano ${clients.length} klientów`);
console.log(`TOP 20 największych zadłużeń:`);
clients.slice(0, 20).forEach((c, i) => {
    console.log(`  ${i+1}. Client ${c.id}: ${c.amount.toFixed(2)}`);
});

const target = 9215.29;
console.log(`\n\nSzukam kombinacji dla ${target}`);

// Użyj heurystyki - zacznij od największych
function findGreedy(arr, target, tolerance = 0.5) {
    const results = [];

    // Strategia 1: Zacznij od największych
    let sum = 0;
    let combo = [];

    for (let i = 0; i < arr.length; i++) {
        if (sum + arr[i].amount <= target + tolerance) {
            combo.push(arr[i]);
            sum += arr[i].amount;

            if (Math.abs(sum - target) < tolerance) {
                results.push({ sum, combo: [...combo], diff: Math.abs(sum - target) });
                console.log(`✓ Greedy znalazł: ${sum.toFixed(2)} (${combo.length} pozycji, diff: ${Math.abs(sum - target).toFixed(2)})`);
                break;
            }
        }
    }

    return results;
}

// Spróbuj podejścia zachłannego
const greedyResults = findGreedy(clients, target, 0.5);

if (greedyResults.length > 0) {
    console.log(`\n📊 Najlepsza kombinacja (greedy):`);
    const best = greedyResults[0];
    console.log(`Suma: ${best.sum.toFixed(2)} (różnica: ${best.diff.toFixed(2)})`);
    console.log(`Liczba klientów: ${best.combo.length}`);
    console.log(`\nKlienci:`);
    best.combo.forEach((c, i) => {
        console.log(`  ${i+1}. Client ${c.id}: ${c.amount.toFixed(2)}`);
    });
}

// Dynamic programming - sprawdź czy suma jest możliwa
console.log(`\n\n🔍 Sprawdzam czy dokładna suma ${target} jest możliwa...`);

function canMakeSum(arr, target, maxItems = 30) {
    // Zaokrąglij do 2 miejsc po przecinku
    const targetCents = Math.round(target * 100);
    const amounts = arr.map(c => ({ ...c, cents: Math.round(c.amount * 100) }));

    // DP - czy możemy uzyskać sumę?
    const dp = new Array(targetCents + 1).fill(false);
    const parent = new Array(targetCents + 1).fill(null);
    dp[0] = true;

    for (let i = 0; i < amounts.length && i < 500; i++) {
        const item = amounts[i];

        // Idź od tyłu, żeby nie użyć tego samego elementu dwa razy
        for (let sum = targetCents; sum >= item.cents; sum--) {
            if (dp[sum - item.cents] && !dp[sum]) {
                dp[sum] = true;
                parent[sum] = { sum: sum - item.cents, item: i };
            }
        }

        if (dp[targetCents]) {
            console.log(`✓ Znaleziono dokładną sumę przy użyciu pierwszych ${i + 1} klientów!`);

            // Odtwórz ścieżkę
            const path = [];
            let current = targetCents;
            while (parent[current]) {
                const p = parent[current];
                path.push(amounts[p.item]);
                current = p.sum;
            }

            const totalSum = path.reduce((acc, c) => acc + c.amount, 0);
            console.log(`\n✅ DOKŁADNA kombinacja (suma: ${totalSum.toFixed(2)}):`);
            path.forEach((c, idx) => {
                console.log(`  ${idx + 1}. Client ${c.id}: ${c.amount.toFixed(2)}`);
            });

            // Zapisz wynik
            fs.writeFileSync('exact-match-9215.json', JSON.stringify({
                target: target,
                found_sum: totalSum,
                difference: Math.abs(totalSum - target),
                clients: path
            }, null, 2));

            return true;
        }

        if (i % 100 === 0) {
            console.log(`Sprawdzono ${i} klientów...`);
        }
    }

    console.log(`❌ Nie znaleziono dokładnej kombinacji w pierwszych 500 klientach`);
    return false;
}

canMakeSum(clients, target);
