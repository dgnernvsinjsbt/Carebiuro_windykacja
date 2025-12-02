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
  console.log('RAPORT WINDYKACJI - stan na ' + new Date().toLocaleDateString('pl-PL'));
  console.log('='.repeat(80));

  // Get all clients
  const { data: clients, error: clientsErr } = await supabase
    .from('clients')
    .select('id, name, email, mobile_phone, note');

  if (clientsErr || !clients) {
    console.error('Error:', clientsErr);
    return;
  }

  // Filter clients with windykacja enabled
  const windykacjaClients = clients.filter(c => parseWindykacja(c.note));

  console.log('\nKlienci z wlaczona windykacja: ' + windykacjaClients.length);
  console.log('-'.repeat(80));

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const qualifyingInvoices: any[] = [];

  for (const client of windykacjaClients) {
    // Get invoices for this client
    const { data: invoices } = await supabase
      .from('invoices')
      .select('id, number, price_gross, paid, payment_to, status, kind, internal_note, client_id')
      .eq('client_id', client.id);

    if (!invoices || invoices.length === 0) continue;

    // Filter overdue, unpaid invoices
    const overdueInvoices = invoices.filter(inv => {
      if (inv.status === 'paid') return false;
      if (inv.kind === 'canceled') return false;

      const balance = parseFloat(inv.price_gross || '0') - parseFloat(inv.paid || '0');
      if (balance <= 0) return false;

      if (!inv.payment_to) return false;
      const paymentDate = new Date(inv.payment_to);
      if (paymentDate >= today) return false;

      const fiscalSync = parseFiscalSync(inv.internal_note);
      if (fiscalSync?.STOP === true) return false;

      // Check if E1 already sent
      const e1Sent = fiscalSync?.EMAIL_1 ? true : false;
      const s1Sent = fiscalSync?.SMS_1 ? true : false;

      return !e1Sent || !s1Sent; // Qualify if either not sent
    });

    if (overdueInvoices.length > 0) {
      for (const inv of overdueInvoices) {
        const fiscalSync = parseFiscalSync(inv.internal_note);
        const balance = parseFloat(inv.price_gross || '0') - parseFloat(inv.paid || '0');
        const daysOverdue = Math.floor((today.getTime() - new Date(inv.payment_to).getTime()) / (1000 * 60 * 60 * 24));

        qualifyingInvoices.push({
          client_name: client.name,
          client_id: client.id,
          email: client.email,
          phone: client.mobile_phone,
          invoice_number: inv.number,
          invoice_id: inv.id,
          balance: balance.toFixed(2),
          days_overdue: daysOverdue,
          payment_to: inv.payment_to,
          e1_sent: fiscalSync?.EMAIL_1 ? 'TAK' : 'NIE',
          s1_sent: fiscalSync?.SMS_1 ? 'TAK' : 'NIE',
          stop: fiscalSync?.STOP ? 'STOP' : '-',
        });
      }
    }
  }

  console.log('\nFaktury kwalifikujace sie do wyslania: ' + qualifyingInvoices.length);
  console.log('-'.repeat(80));

  if (qualifyingInvoices.length === 0) {
    console.log('Brak faktur do wysylki.');
  } else {
    // Group by client
    const byClient = new Map<string, any[]>();
    for (const inv of qualifyingInvoices) {
      const key = inv.client_name;
      if (!byClient.has(key)) byClient.set(key, []);
      byClient.get(key)!.push(inv);
    }

    for (const [clientName, invs] of byClient) {
      const c = invs[0];
      console.log('\n' + clientName + ' (ID: ' + c.client_id + ')');
      console.log('   Email: ' + (c.email || 'brak') + ' | Tel: ' + (c.phone || 'brak'));

      for (const inv of invs) {
        console.log('   -> ' + inv.invoice_number + ' | ' + inv.balance + ' EUR | ' + inv.days_overdue + ' dni po terminie');
        console.log('      Termin: ' + inv.payment_to + ' | E1: ' + inv.e1_sent + ' | S1: ' + inv.s1_sent + ' | ' + inv.stop);
      }
    }
  }

  console.log('\n' + '='.repeat(80));
}

main().catch(console.error);
