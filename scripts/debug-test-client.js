/**
 * Debug script - sprawdź dane klienta "test" i jego faktury
 */

const { createClient } = require('@supabase/supabase-js');

// Wczytaj zmienne z .env.local ręcznie
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

// Parser komentarzy
function parseFiscalSync(comment) {
  if (!comment) return null;

  const fiscalSyncRegex = /\[FISCAL_SYNC\]([\s\S]*?)\[\/FISCAL_SYNC\]/;
  const match = comment.match(fiscalSyncRegex);

  if (!match) return null;

  const content = match[1].trim();
  const lines = content.split('\n');
  const data = {};

  for (const line of lines) {
    const [key, value] = line.split('=').map(s => s.trim());
    if (!key || !value) continue;

    if (key === 'UPDATED') {
      data[key] = value;
    } else if (key.endsWith('_DATE')) {
      data[key] = value === 'NULL' ? null : value;
    } else {
      data[key] = value === 'TRUE';
    }
  }

  return data;
}

async function debugTestClient() {
  console.log('🔍 Szukam klienta "test"...\n');

  // Znajdź klienta
  const { data: clients, error: clientError } = await supabase
    .from('clients')
    .select('*')
    .ilike('name', '%test%');

  if (clientError) {
    console.error('❌ Błąd pobierania klientów:', clientError);
    return;
  }

  if (!clients || clients.length === 0) {
    console.error('❌ Nie znaleziono klienta "test"');
    return;
  }

  console.log(`✅ Znaleziono klientów (${clients.length}):`);
  clients.forEach(c => {
    console.log(`   - ID: ${c.id}, Nazwa: ${c.name}`);
  });

  // Weź pierwszego klienta
  const client = clients[0];
  console.log(`\n📋 Sprawdzam klienta: ${client.name} (ID: ${client.id})\n`);

  // Pobierz faktury
  const { data: invoices, error: invoicesError } = await supabase
    .from('invoices')
    .select('*')
    .eq('client_id', client.id);

  if (invoicesError) {
    console.error('❌ Błąd pobierania faktur:', invoicesError);
    return;
  }

  if (!invoices || invoices.length === 0) {
    console.error('❌ Klient nie ma faktur');
    return;
  }

  console.log(`📄 Faktury (${invoices.length}):\n`);

  let invoicesWithThirdReminder = 0;
  let highValueInvoicesWithThirdReminder = 0;

  invoices.forEach((inv, idx) => {
    console.log(`[${idx + 1}] Faktura: ${inv.number}`);
    console.log(`    Total: €${inv.total || 0}`);
    console.log(`    Status: ${inv.status}`);
    console.log(`    Kind: ${inv.kind}`);

    if (inv.comment) {
      const fiscalSync = parseFiscalSync(inv.comment);

      if (fiscalSync) {
        console.log(`    FISCAL_SYNC:`);
        console.log(`      EMAIL_3: ${fiscalSync.EMAIL_3}`);
        console.log(`      SMS_3: ${fiscalSync.SMS_3}`);
        console.log(`      WHATSAPP_3: ${fiscalSync.WHATSAPP_3}`);
        console.log(`      STOP: ${fiscalSync.STOP}`);

        // Sprawdź czy ma trzecie upomnienie
        const hasThird = fiscalSync.EMAIL_3 || fiscalSync.SMS_3 || fiscalSync.WHATSAPP_3;
        console.log(`      ✓ Ma trzecie upomnienie: ${hasThird ? 'TAK' : 'NIE'}`);

        if (hasThird) {
          invoicesWithThirdReminder++;
          if ((inv.total || 0) >= 190) {
            highValueInvoicesWithThirdReminder++;
          }
        }
      } else {
        console.log(`    ❌ Brak struktury [FISCAL_SYNC]`);
      }
    } else {
      console.log(`    ❌ Brak komentarza`);
    }
    console.log('');
  });

  // Oblicz sumę zadłużenia z faktur z trzecim upomnieniem
  const totalDebtWithThirdReminder = invoices
    .filter(inv => {
      const fiscalSync = parseFiscalSync(inv.comment);
      return fiscalSync && (fiscalSync.EMAIL_3 || fiscalSync.SMS_3 || fiscalSync.WHATSAPP_3);
    })
    .reduce((sum, inv) => sum + (inv.total || 0), 0);

  console.log('\n📊 PODSUMOWANIE:');
  console.log(`   Faktury z trzecim upomnieniem: ${invoicesWithThirdReminder}`);
  console.log(`   Suma zadłużenia (trzecie upomnienie): €${totalDebtWithThirdReminder.toFixed(2)}`);

  console.log('\n🎯 KWALIFIKACJA:');
  const qualifies =
    invoicesWithThirdReminder >= 3 ||
    totalDebtWithThirdReminder >= 190;

  if (qualifies) {
    console.log('   ✅ Klient KWALIFIKUJE SIĘ do listu poleconego');
    if (invoicesWithThirdReminder >= 3) {
      console.log('   → Warunek: 3+ faktury z trzecim upomnieniem');
    }
    if (totalDebtWithThirdReminder >= 190) {
      console.log('   → Warunek: Suma zadłużenia ≥€190 z trzecim upomnieniem');
    }
  } else {
    console.log('   ❌ Klient NIE kwalifikuje się do listu poleconego');
    console.log(`   → Potrzeba: ${3 - invoicesWithThirdReminder} więcej faktur z trzecim upomnieniem`);
    console.log(`   → LUB: €${(190 - totalDebtWithThirdReminder).toFixed(2)} więcej zadłużenia z trzecim upomnieniem`);
  }
}

debugTestClient()
  .then(() => {
    console.log('\n✅ Gotowe');
    process.exit(0);
  })
  .catch((error) => {
    console.error('❌ Błąd:', error);
    process.exit(1);
  });
