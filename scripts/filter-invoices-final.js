/**
 * Filter Invoices - Final Minimal Schema
 *
 * Tylko najpotrzebniejsze pola dla analizy płatności
 */

const fs = require('fs');
const path = require('path');

const INPUT_FILE = path.join(__dirname, '../invoices.json');
const OUTPUT_FILE = path.join(__dirname, '../invoices-filtered.json');

console.log('🔍 Filtrowanie faktur (minimalny schemat)...\n');

// Wczytaj dane
const invoices = JSON.parse(fs.readFileSync(INPUT_FILE, 'utf-8'));

console.log(`📄 Znaleziono ${invoices.length} faktur`);

// Filtruj - tylko potrzebne pola
const filteredInvoices = invoices.map((invoice) => {
  return {
    id: invoice.id,
    client_id: invoice.client_id,
    from_invoice_id: invoice.from_invoice_id || null,
    paid: invoice.paid,
    price_net: invoice.price_net || null,
    price_gross: invoice.price_gross || null,
    currency: invoice.currency || null,
    status: invoice.status || null,
    sell_date: invoice.sell_date || null,
    issue_date: invoice.issue_date || null,
    paid_date: invoice.paid_date || null,
    created_at: invoice.created_at || null,
    updated_at: invoice.updated_at || null,
    buyer_name: invoice.buyer_name || null,
  };
});

// Zapisz
fs.writeFileSync(OUTPUT_FILE, JSON.stringify(filteredInvoices, null, 2), 'utf-8');

console.log(`✅ Przefiltrowano ${filteredInvoices.length} faktur`);
console.log(`📁 Zapisano do: ${OUTPUT_FILE}\n`);

// Statystyki
const withBuyerName = filteredInvoices.filter(inv => inv.buyer_name).length;
const withSellDate = filteredInvoices.filter(inv => inv.sell_date).length;
const september = filteredInvoices.filter(inv =>
  inv.sell_date && inv.sell_date >= '2025-09-01' && inv.sell_date <= '2025-09-30'
).length;

console.log('📊 Statystyki:');
console.log(`   - Faktury z buyer_name: ${withBuyerName}`);
console.log(`   - Faktury z sell_date: ${withSellDate}`);
console.log(`   - Faktury wrzesień (01-30.09): ${september}`);

// Rozmiar
const originalSize = fs.statSync(INPUT_FILE).size;
const filteredSize = fs.statSync(OUTPUT_FILE).size;
const reduction = ((1 - filteredSize / originalSize) * 100).toFixed(1);

console.log(`\n💾 Redukcja: ${reduction}% (${(originalSize / 1024).toFixed(0)} KB → ${(filteredSize / 1024).toFixed(0)} KB)`);

// Przykład
console.log('\n📋 Przykładowa faktura:');
console.log(JSON.stringify(filteredInvoices[0], null, 2));
