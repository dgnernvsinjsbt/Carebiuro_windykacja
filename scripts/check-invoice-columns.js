/**
 * Sprawdź strukturę faktur w Supabase - jakie kolumny mają faktury
 */

const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');
const path = require('path');

const envPath = path.join(__dirname, '..', '.env');
if (fs.existsSync(envPath)) {
  const envFile = fs.readFileSync(envPath, 'utf8');
  envFile.split('\n').forEach(line => {
    const [key, ...values] = line.split('=');
    if (key && values.length) {
      process.env[key.trim()] = values.join('=').trim();
    }
  });
}

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error('❌ Brak zmiennych środowiskowych Supabase');
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

async function checkInvoiceColumns() {
  console.log('🔍 Sprawdzam faktury klienta "test" w Supabase...\n');

  // Znajdź klienta test
  const { data: client, error: clientError } = await supabase
    .from('clients')
    .select('id, name')
    .ilike('name', '%test%')
    .single();

  if (clientError || !client) {
    console.error('❌ Nie znaleziono klienta test:', clientError);
    return;
  }

  console.log(`✅ Klient: ${client.name} (ID: ${client.id})\n`);

  // Pobierz faktury
  const { data: invoices, error: invoicesError } = await supabase
    .from('invoices')
    .select('*')
    .eq('client_id', client.id)
    .limit(1);

  if (invoicesError) {
    console.error('❌ Błąd pobierania faktur:', invoicesError);
    return;
  }

  if (!invoices || invoices.length === 0) {
    console.error('❌ Brak faktur');
    return;
  }

  console.log('📋 Przykładowa faktura (struktura kolumn):\n');
  const invoice = invoices[0];

  console.log('Kolumny w tabeli invoices:');
  Object.keys(invoice).forEach(key => {
    const value = invoice[key];
    const type = typeof value;
    const preview = value ? (type === 'string' && value.length > 50 ? value.substring(0, 50) + '...' : value) : 'null';
    console.log(`  ${key}: ${type} = ${preview}`);
  });

  console.log('\n📄 Sprawdzam kolumnę "comment":');

  const { data: allInvoices, error: allError } = await supabase
    .from('invoices')
    .select('number, comment')
    .eq('client_id', client.id);

  if (allError) {
    console.log('  ❌ Błąd pobierania faktur:', allError);
  }

  if (allInvoices) {
    allInvoices.forEach(inv => {
      console.log(`\n  Faktura: ${inv.number}`);
      if (inv.comment) {
        console.log(`    comment (długość: ${inv.comment.length}):`);
        console.log(`    ${inv.comment.substring(0, 200)}...`);
      } else {
        console.log(`    comment: NULL`);
      }
    });
  }
}

checkInvoiceColumns()
  .then(() => {
    console.log('\n✅ Gotowe');
    process.exit(0);
  })
  .catch((error) => {
    console.error('❌ Błąd:', error);
    process.exit(1);
  });
