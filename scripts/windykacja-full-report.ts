import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

function parseWindykacja(note: string | null): boolean {
  if (!note) return false;
  const match = note.match(/\[WINDYKACJA\](true|false)\[\/WINDYKACJA\]/i);
  return match ? match[1].toLowerCase() === 'true' : false;
}

function parseFiscalSync(internalNote: string | null): Record<string, any> | null {
  if (!internalNote) return null;
  const match = internalNote.match(/\[FISCAL_SYNC\]([\s\S]*?)\[\/FISCAL_SYNC\]/);
  if (!match) return null;
  try {
    return JSON.parse(match[1]);
  } catch {
    return null;
  }
}

async function main() {
  console.log('RAPORT WINDYKACJI - ' + new Date().toISOString());
  console.log('='.repeat(100));

  // Get clients with windykacja
  const { data: clients } = await supabase
    .from('clients')
    .select('id, name, email, mobile_phone, note')
    .like('note', '%[WINDYKACJA]true[/WINDYKACJA]%');

  console.log('\nKlienci z windykacja=true: ' + (clients?.length || 0));

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const qualifying: any[] = [];
  const alreadySent: any[] = [];
  const stopped: any[] = [];
  const notOverdue: any[] = [];
  const paid: any[] = [];

  for (const client of clients || []) {
    const { data: invoices } = await supabase
      .from('invoices')
      .select('id, number, price_gross, paid, payment_to, status, kind, internal_note')
      .eq('client_id', client.id);

    for (const inv of invoices || []) {
      const balance = parseFloat(inv.price_gross || '0') - parseFloat(inv.paid || '0');
      const paymentDate = inv.payment_to ? new Date(inv.payment_to) : null;
      const isOverdue = paymentDate && paymentDate < today;
      const daysOverdue = paymentDate ? Math.floor((today.getTime() - paymentDate.getTime()) / (1000*60*60*24)) : 0;
      const fiscalSync = parseFiscalSync(inv.internal_note);

      const item = {
        client: client.name,
        client_id: client.id,
        email: client.email || '-',
        phone: client.mobile_phone || '-',
        invoice: inv.number,
        balance: balance.toFixed(2) + ' EUR',
        days_overdue: daysOverdue,
        payment_to: inv.payment_to,
        e1: fiscalSync?.EMAIL_1 ? 'TAK' : 'NIE',
        s1: fiscalSync?.SMS_1 ? 'TAK' : 'NIE',
        stop: fiscalSync?.STOP ? 'STOP' : '-'
      };

      if (inv.status === 'paid' || balance <= 0) {
        paid.push(item);
      } else if (fiscalSync?.STOP === true) {
        stopped.push(item);
      } else if (!isOverdue) {
        notOverdue.push(item);
      } else if (fiscalSync?.EMAIL_1 && fiscalSync?.SMS_1) {
        alreadySent.push(item);
      } else {
        qualifying.push(item);
      }
    }
  }

  // Sort qualifying by days overdue
  qualifying.sort((a, b) => b.days_overdue - a.days_overdue);

  console.log('\n' + '='.repeat(100));
  console.log('FAKTURY KWALIFIKUJACE SIE DO WYSLANIA JUTRO: ' + qualifying.length);
  console.log('='.repeat(100));
  
  if (qualifying.length === 0) {
    console.log('Brak faktur do wyslania.');
  } else {
    for (const q of qualifying) {
      console.log('\n' + q.client + ' (ID: ' + q.client_id + ')');
      console.log('  Email: ' + q.email + ' | Tel: ' + q.phone);
      console.log('  Faktura: ' + q.invoice + ' | Kwota: ' + q.balance + ' | ' + q.days_overdue + ' dni po terminie');
      console.log('  E1=' + q.e1 + ' | S1=' + q.s1 + ' | ' + q.stop);
    }
  }

  console.log('\n' + '-'.repeat(100));
  console.log('PODSUMOWANIE:');
  console.log('  Do wyslania:     ' + qualifying.length);
  console.log('  Juz wyslane E1+S1: ' + alreadySent.length);
  console.log('  STOP:            ' + stopped.length);
  console.log('  Nie po terminie: ' + notOverdue.length);
  console.log('  Zaplacone:       ' + paid.length);
  console.log('='.repeat(100));
}

main().catch(console.error);
