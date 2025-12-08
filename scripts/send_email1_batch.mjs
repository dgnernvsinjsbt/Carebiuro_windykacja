import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
dotenv.config();

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

// Lista faktur do wysłania (z poprzedniego raportu)
const invoiceNumbers = [
  'FP2025/12/000775',  // Adam Lis
  'FP2025/12/000671',  // Adam Metelski
  'FP2025/12/000105',  // Adam Nowakowski
  'FP2025/11/000886',  // Aleksandra Kapala
  'FP2025/12/000848',  // Aleksandra Malgorzata Wlodarczyk
  'FP2025/12/000639',  // Aleksandra Pusdrowska
  'FP2025/12/000883',  // Andrzej Szablowski
  'FP2023/12/001122',  // Andrzej Tutka
  'FP2025/04/001166',  // Andrzej Waclaw Filipiak
  'FP2025/09/001072',  // Aneta Bernecka
  'FP2025/12/000885',  // Aneta Justyna Gorgon
  'FP2025/12/000884',  // Anita Jolanta Kielar
  'FP2025/12/000564',  // Arkadiusz Nyka
];

console.log('📧 WYSYŁANIE EMAIL_1 DLA 13 KLIENTÓW\n');
console.log('='.repeat(80));

// Pobierz invoice_id dla wszystkich faktur
console.log('\n1. Pobieranie invoice_id z Supabase...');
const { data: allInvoices } = await supabase
  .from('invoices')
  .select('id, number, buyer_name, buyer_email, kind')
  .in('number', invoiceNumbers);

if (!allInvoices || allInvoices.length === 0) {
  console.error('❌ Nie znaleziono faktur w Supabase!');
  process.exit(1);
}

// FILTRUJ - pomiń anulowane faktury
const invoices = allInvoices.filter(inv => inv.kind !== 'canceled');
const canceledCount = allInvoices.length - invoices.length;

if (canceledCount > 0) {
  console.log(`   ⚠️  Pominięto ${canceledCount} anulowanych faktur`);
}

console.log(`   ✓ Znaleziono ${invoices.length} faktur\n`);

const apiUrl = 'https://carebiuro-windykacja.vercel.app';

let successCount = 0;
let failCount = 0;
const results = [];

console.log('2. Wysyłanie emaili...\n');

for (const invoice of invoices) {
  console.log(`${successCount + failCount + 1}. ${invoice.buyer_name} - ${invoice.number}`);
  console.log(`   Email: ${invoice.buyer_email || 'BRAK'}`);

  if (!invoice.buyer_email) {
    console.log(`   ⚠️  Pominięto - brak adresu email`);
    failCount++;
    results.push({ ...invoice, status: 'skipped', error: 'Brak email' });
    continue;
  }

  try {
    // Pobierz cookie z pliku (po zalogowaniu)
    const { readFileSync } = await import('fs');
    const cookieFile = readFileSync('/tmp/cookies.txt', 'utf8');
    const authToken = cookieFile.match(/auth-token\s+([^\s]+)/)?.[1];

    // Wywołaj POST /api/reminder z cookie
    const response = await fetch(`${apiUrl}/api/reminder`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Cookie': `auth-token=${authToken}`
      },
      body: JSON.stringify({
        invoice_id: invoice.id,
        type: 'email',
        level: '1'
      })
    });

    const data = await response.json();

    if (response.ok && data.success) {
      console.log(`   ✅ Wysłano EMAIL_1`);
      successCount++;
      results.push({ ...invoice, status: 'success' });
    } else {
      console.log(`   ❌ Błąd: ${data.error || 'Unknown error'}`);
      failCount++;
      results.push({ ...invoice, status: 'failed', error: data.error });
    }

    // Delay między wysyłkami (avoid rate limiting)
    await new Promise(r => setTimeout(r, 3000)); // 3 sekundy

  } catch (err) {
    console.log(`   ❌ Błąd połączenia: ${err.message}`);
    failCount++;
    results.push({ ...invoice, status: 'error', error: err.message });
  }
}

console.log('\n' + '='.repeat(80));
console.log('\n📊 PODSUMOWANIE:');
console.log(`   Wysłane pomyślnie: ${successCount}`);
console.log(`   Błędy/Pominięte: ${failCount}`);
console.log(`   Łącznie: ${successCount + failCount}`);

if (failCount > 0) {
  console.log('\n❌ Faktury z błędami:');
  results.filter(r => r.status !== 'success').forEach(r => {
    console.log(`   - ${r.buyer_name} (${r.number}): ${r.error}`);
  });
}

console.log('\n' + '='.repeat(80));
