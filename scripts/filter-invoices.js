/**
 * Filter Invoices Script
 *
 * Filtruje faktury z invoices.json, zachowując tylko potrzebne pola:
 * - id
 * - client_id
 * - from_invoice_id
 * - paid
 * - Wszystkie pola z datami (sell_date, issue_date, payment_to, paid_date, created_at, updated_at)
 */

const fs = require('fs');
const path = require('path');

// Ścieżki plików
const INPUT_FILE = path.join(__dirname, '../invoices.json');
const OUTPUT_FILE = path.join(__dirname, '../invoices-filtered.json');

console.log('🔍 Filtrowanie faktur...\n');

// Wczytaj dane
const invoices = JSON.parse(fs.readFileSync(INPUT_FILE, 'utf-8'));

console.log(`📄 Znaleziono ${invoices.length} faktur`);

// Filtruj dane - zachowaj tylko potrzebne pola
const filteredInvoices = invoices.map((invoice) => {
  return {
    id: invoice.id,
    client_id: invoice.client_id,
    from_invoice_id: invoice.from_invoice_id || null,
    paid: invoice.paid,

    // Wszystkie pola z datami
    sell_date: invoice.sell_date || null,
    issue_date: invoice.issue_date || null,
    payment_to: invoice.payment_to || null,
    paid_date: invoice.paid_date || null,
    created_at: invoice.created_at || null,
    updated_at: invoice.updated_at || null,
  };
});

// Zapisz przefiltrowane dane
fs.writeFileSync(OUTPUT_FILE, JSON.stringify(filteredInvoices, null, 2), 'utf-8');

console.log(`✅ Przefiltrowano ${filteredInvoices.length} faktur`);
console.log(`📁 Zapisano do: ${OUTPUT_FILE}\n`);

// Statystyki
const withFromInvoiceId = filteredInvoices.filter(inv => inv.from_invoice_id).length;
const withPaidDate = filteredInvoices.filter(inv => inv.paid_date).length;
const fullyPaid = filteredInvoices.filter(inv => parseFloat(inv.paid || 0) > 0).length;

console.log('📊 Statystyki:');
console.log(`   - Faktury z from_invoice_id: ${withFromInvoiceId}`);
console.log(`   - Faktury z paid_date: ${withPaidDate}`);
console.log(`   - Faktury opłacone (paid > 0): ${fullyPaid}`);

// Przykładowa faktura
console.log('\n📋 Przykładowa przefiltrowana faktura:');
console.log(JSON.stringify(filteredInvoices[0], null, 2));
