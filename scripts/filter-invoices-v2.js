/**
 * Filter Invoices V2 - Extended Version
 *
 * Filtruje faktury z invoices.json, zachowując:
 * - Podstawowe ID (id, client_id, from_invoice_id)
 * - Wszystkie daty (sell_date, issue_date, payment_to, paid_date, created_at, updated_at)
 * - Kwoty (paid, price_net, price_gross, currency)
 * - Dane klienta (buyer_name, buyer_email, buyer_phone) - KLUCZOWE dla dopasowania
 * - Status (status)
 */

const fs = require('fs');
const path = require('path');

const INPUT_FILE = path.join(__dirname, '../invoices.json');
const OUTPUT_FILE = path.join(__dirname, '../invoices-filtered.json');

console.log('🔍 Filtrowanie faktur V2 (z danymi klienta)...\n');

// Wczytaj dane
const invoices = JSON.parse(fs.readFileSync(INPUT_FILE, 'utf-8'));

console.log(`📄 Znaleziono ${invoices.length} faktur`);

// Filtruj dane - zachowaj potrzebne pola + dane klienta
const filteredInvoices = invoices.map((invoice) => {
  return {
    // IDs
    id: invoice.id,
    client_id: invoice.client_id,
    from_invoice_id: invoice.from_invoice_id || null,

    // Kwoty
    paid: invoice.paid,
    price_net: invoice.price_net || null,
    price_gross: invoice.price_gross || null,
    currency: invoice.currency || null,

    // Status
    status: invoice.status || null,

    // Daty
    sell_date: invoice.sell_date || null,
    issue_date: invoice.issue_date || null,
    payment_to: invoice.payment_to || null,
    paid_date: invoice.paid_date || null,
    created_at: invoice.created_at || null,
    updated_at: invoice.updated_at || null,

    // KLUCZOWE: Dane klienta dla dopasowania płatności
    buyer_name: invoice.buyer_name || null,
    buyer_email: invoice.buyer_email || null,
    buyer_phone: invoice.buyer_phone || null,
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
const withBuyerName = filteredInvoices.filter(inv => inv.buyer_name).length;

console.log('📊 Statystyki:');
console.log(`   - Faktury z from_invoice_id: ${withFromInvoiceId}`);
console.log(`   - Faktury z paid_date: ${withPaidDate}`);
console.log(`   - Faktury opłacone (paid > 0): ${fullyPaid}`);
console.log(`   - Faktury z buyer_name: ${withBuyerName}`);

// Przykładowa faktura
console.log('\n📋 Przykładowa przefiltrowana faktura:');
console.log(JSON.stringify(filteredInvoices[0], null, 2));

// Porównanie rozmiaru
const originalSize = fs.statSync(INPUT_FILE).size;
const filteredSize = fs.statSync(OUTPUT_FILE).size;
const reduction = ((1 - filteredSize / originalSize) * 100).toFixed(1);

console.log(`\n💾 Redukcja rozmiaru: ${reduction}% (${(originalSize / 1024).toFixed(0)} KB → ${(filteredSize / 1024).toFixed(0)} KB)`);
