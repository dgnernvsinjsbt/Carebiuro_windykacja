import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

const supabase = createClient(supabaseUrl, supabaseKey);

interface FiscalSyncData {
  EMAIL_1: boolean;
  EMAIL_1_DATE: string | null;
  EMAIL_2: boolean;
  EMAIL_2_DATE: string | null;
  EMAIL_3: boolean;
  EMAIL_3_DATE: string | null;
  SMS_1: boolean;
  SMS_1_DATE: string | null;
  SMS_2: boolean;
  SMS_2_DATE: string | null;
  SMS_3: boolean;
  SMS_3_DATE: string | null;
  STOP: boolean;
}

function parseFiscalSync(comment: string | null): FiscalSyncData | null {
  if (!comment) return null;

  const fiscalSyncRegex = /\[FISCAL_SYNC\]([\s\S]*?)\[\/FISCAL_SYNC\]/;
  const match = comment.match(fiscalSyncRegex);

  if (!match) return null;

  const content = match[1].trim();
  const lines = content.split('\n');
  const data: any = {
    EMAIL_1: false,
    EMAIL_1_DATE: null,
    EMAIL_2: false,
    EMAIL_2_DATE: null,
    EMAIL_3: false,
    EMAIL_3_DATE: null,
    SMS_1: false,
    SMS_1_DATE: null,
    SMS_2: false,
    SMS_2_DATE: null,
    SMS_3: false,
    SMS_3_DATE: null,
    STOP: false,
  };

  for (const line of lines) {
    const [key, value] = line.split('=').map(s => s.trim());
    if (!key || !value) continue;

    if (key.endsWith('_DATE')) {
      data[key] = value === 'NULL' ? null : value;
    } else {
      data[key] = value === 'TRUE';
    }
  }

  return data as FiscalSyncData;
}

function parseClientFlags(note: string | null): { windykacja: boolean } {
  const noteStr = note || '';
  const windykacja = /\[WINDYKACJA\]true\[\/WINDYKACJA\]/.test(noteStr);
  return { windykacja };
}

async function analyze() {
  console.log('='.repeat(80));
  console.log('ANALIZA WINDYKACJI - Kwalifikujące się faktury');
  console.log('Data analizy:', new Date().toISOString());
  console.log('='.repeat(80));
  console.log('');

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const threeDaysAgo = new Date(today);
  threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);

  const thirtyDaysAgo = new Date(today);
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

  const fourteenDaysAgo = new Date(today);
  fourteenDaysAgo.setDate(fourteenDaysAgo.getDate() - 14);

  // Get all clients with windykacja enabled
  const { data: allClients, error: clientsError } = await supabase
    .from('clients')
    .select('id, name, note');

  if (clientsError) {
    console.error('Error fetching clients:', clientsError);
    return;
  }

  const windykacjaClients = allClients?.filter(c => parseClientFlags(c.note).windykacja) || [];
  const windykacjaClientIds = windykacjaClients.map(c => c.id);

  console.log(`Klienci z windykacja=true: ${windykacjaClients.length}`);
  console.log('');

  // Get all unpaid invoices
  const { data: invoices, error: invoicesError } = await supabase
    .from('invoices')
    .select('*')
    .neq('status', 'paid')
    .neq('kind', 'canceled')
    .neq('kind', 'vat')
    .order('issue_date', { ascending: false });

  if (invoicesError) {
    console.error('Error fetching invoices:', invoicesError);
    return;
  }

  // Filter invoices with balance
  const unpaidInvoices = invoices?.filter(inv => {
    const balance = (inv.total || 0) - (inv.paid || 0);
    return balance > 0;
  }) || [];

  console.log(`Nieopłacone faktury (balance > 0): ${unpaidInvoices.length}`);
  console.log('');

  // Categories
  const qualifyingE1S1Initial: any[] = [];
  const qualifyingE1S1Overdue: any[] = [];
  const qualifyingE2S2: any[] = [];
  const qualifyingE3S3: any[] = [];

  for (const inv of unpaidInvoices) {
    const fiscalSync = parseFiscalSync(inv.internal_note);
    const issueDate = inv.issue_date ? new Date(inv.issue_date) : null;
    if (!issueDate) continue;

    const client = allClients?.find(c => c.id === inv.client_id);
    const clientWindykacja = client ? parseClientFlags(client.note).windykacja : false;
    const isStopped = fiscalSync?.STOP === true;

    // E1 sent check (either our system or Fakturownia)
    const e1Sent = fiscalSync?.EMAIL_1 || inv.email_status === 'sent';
    const s1Sent = fiscalSync?.SMS_1;
    const e2Sent = fiscalSync?.EMAIL_2;
    const s2Sent = fiscalSync?.SMS_2;
    const e3Sent = fiscalSync?.EMAIL_3;
    const s3Sent = fiscalSync?.SMS_3;

    // Get dates
    const e1Date = e1Sent
      ? (inv.email_status === 'sent' && inv.sent_time
          ? new Date(inv.sent_time)
          : fiscalSync?.EMAIL_1_DATE ? new Date(fiscalSync.EMAIL_1_DATE) : null)
      : null;
    const s1Date = s1Sent && fiscalSync?.SMS_1_DATE ? new Date(fiscalSync.SMS_1_DATE) : null;
    const e2Date = e2Sent && fiscalSync?.EMAIL_2_DATE ? new Date(fiscalSync.EMAIL_2_DATE) : null;
    const s2Date = s2Sent && fiscalSync?.SMS_2_DATE ? new Date(fiscalSync.SMS_2_DATE) : null;

    const balance = (inv.total || 0) - (inv.paid || 0);

    const invoiceInfo = {
      id: inv.id,
      number: inv.number,
      buyer: inv.buyer_name,
      balance: balance.toFixed(2),
      currency: inv.currency,
      issue_date: inv.issue_date,
      payment_to: inv.payment_to,
      e1_sent: e1Sent,
      e1_date: e1Date?.toISOString().split('T')[0],
      s1_sent: s1Sent,
      s1_date: s1Date?.toISOString().split('T')[0],
      e2_sent: e2Sent,
      e2_date: e2Date?.toISOString().split('T')[0],
      s2_sent: s2Sent,
      s2_date: s2Date?.toISOString().split('T')[0],
      e3_sent: e3Sent,
      s3_sent: s3Sent,
      stopped: isStopped,
      client_windykacja: clientWindykacja,
    };

    // 1. E1/S1 Initial (new invoices within 3 days)
    if (issueDate >= threeDaysAgo) {
      if (!e1Sent || !s1Sent) {
        qualifyingE1S1Initial.push({
          ...invoiceInfo,
          needs: (!e1Sent ? 'E1 ' : '') + (!s1Sent ? 'S1' : ''),
          reason: 'Nowa faktura (< 3 dni)',
        });
      }
    }

    // 2. E1/S1 Overdue (30+ days, windykacja enabled)
    if (clientWindykacja && !isStopped && issueDate <= thirtyDaysAgo) {
      if (!e1Sent || !s1Sent) {
        qualifyingE1S1Overdue.push({
          ...invoiceInfo,
          needs: (!e1Sent ? 'E1 ' : '') + (!s1Sent ? 'S1' : ''),
          reason: 'Przeterminowana > 30 dni',
        });
      }
    }

    // 3. E2/S2 (14 days after E1/S1)
    if (clientWindykacja && !isStopped) {
      const needsE2 = e1Sent && !e2Sent && e1Date && e1Date <= fourteenDaysAgo;
      const needsS2 = s1Sent && !s2Sent && s1Date && s1Date <= fourteenDaysAgo;

      if (needsE2 || needsS2) {
        const e1DaysAgo = e1Date ? Math.floor((today.getTime() - e1Date.getTime()) / (1000*60*60*24)) : 0;
        const s1DaysAgo = s1Date ? Math.floor((today.getTime() - s1Date.getTime()) / (1000*60*60*24)) : 0;

        qualifyingE2S2.push({
          ...invoiceInfo,
          needs: (needsE2 ? 'E2 ' : '') + (needsS2 ? 'S2' : ''),
          reason: `E1 wysłany ${e1DaysAgo} dni temu, S1 wysłany ${s1DaysAgo} dni temu`,
        });
      }
    }

    // 4. E3/S3 (14 days after E2/S2)
    if (clientWindykacja && !isStopped) {
      const needsE3 = e2Sent && !e3Sent && e2Date && e2Date <= fourteenDaysAgo;
      const needsS3 = s2Sent && !s3Sent && s2Date && s2Date <= fourteenDaysAgo;

      if (needsE3 || needsS3) {
        const e2DaysAgo = e2Date ? Math.floor((today.getTime() - e2Date.getTime()) / (1000*60*60*24)) : 0;
        const s2DaysAgo = s2Date ? Math.floor((today.getTime() - s2Date.getTime()) / (1000*60*60*24)) : 0;

        qualifyingE3S3.push({
          ...invoiceInfo,
          needs: (needsE3 ? 'E3 ' : '') + (needsS3 ? 'S3' : ''),
          reason: `E2 wysłany ${e2DaysAgo} dni temu, S2 wysłany ${s2DaysAgo} dni temu`,
        });
      }
    }
  }

  // Print results
  console.log('='.repeat(80));
  console.log('1. E1/S1 INITIAL - Nowe faktury (< 3 dni)');
  console.log('   (Informacyjne - wysyłane bez względu na WINDYKACJA)');
  console.log('='.repeat(80));
  if (qualifyingE1S1Initial.length === 0) {
    console.log('   Brak kwalifikujących się faktur');
  } else {
    for (const inv of qualifyingE1S1Initial) {
      console.log(`   ${inv.number} | ${inv.buyer?.substring(0,30)} | ${inv.balance} ${inv.currency} | Issue: ${inv.issue_date} | Needs: ${inv.needs}`);
    }
  }
  console.log(`   RAZEM: ${qualifyingE1S1Initial.length} faktur`);
  console.log('');

  console.log('='.repeat(80));
  console.log('2. E1/S1 OVERDUE - Przeterminowane > 30 dni (z włączonym WINDYKACJA)');
  console.log('='.repeat(80));
  if (qualifyingE1S1Overdue.length === 0) {
    console.log('   Brak kwalifikujących się faktur');
  } else {
    for (const inv of qualifyingE1S1Overdue) {
      console.log(`   ${inv.number} | ${inv.buyer?.substring(0,30)} | ${inv.balance} ${inv.currency} | Issue: ${inv.issue_date} | Needs: ${inv.needs}`);
    }
  }
  console.log(`   RAZEM: ${qualifyingE1S1Overdue.length} faktur`);
  console.log('');

  console.log('='.repeat(80));
  console.log('3. E2/S2 - 14 dni po E1/S1 (z włączonym WINDYKACJA)');
  console.log('='.repeat(80));
  if (qualifyingE2S2.length === 0) {
    console.log('   Brak kwalifikujących się faktur');
  } else {
    for (const inv of qualifyingE2S2) {
      console.log(`   ${inv.number} | ${inv.buyer?.substring(0,30)} | ${inv.balance} ${inv.currency} | ${inv.reason} | Needs: ${inv.needs}`);
    }
  }
  console.log(`   RAZEM: ${qualifyingE2S2.length} faktur`);
  console.log('');

  console.log('='.repeat(80));
  console.log('4. E3/S3 - 14 dni po E2/S2 (z włączonym WINDYKACJA)');
  console.log('='.repeat(80));
  if (qualifyingE3S3.length === 0) {
    console.log('   Brak kwalifikujących się faktur');
  } else {
    for (const inv of qualifyingE3S3) {
      console.log(`   ${inv.number} | ${inv.buyer?.substring(0,30)} | ${inv.balance} ${inv.currency} | ${inv.reason} | Needs: ${inv.needs}`);
    }
  }
  console.log(`   RAZEM: ${qualifyingE3S3.length} faktur`);
  console.log('');

  console.log('='.repeat(80));
  console.log('PODSUMOWANIE');
  console.log('='.repeat(80));
  console.log(`   E1/S1 Initial (nowe):           ${qualifyingE1S1Initial.length} faktur`);
  console.log(`   E1/S1 Overdue (30+ dni):        ${qualifyingE1S1Overdue.length} faktur`);
  console.log(`   E2/S2 (14 dni po E1/S1):        ${qualifyingE2S2.length} faktur`);
  console.log(`   E3/S3 (14 dni po E2/S2):        ${qualifyingE3S3.length} faktur`);
  console.log('');
  console.log(`   ŁĄCZNIE DO WYSŁANIA:            ${qualifyingE1S1Initial.length + qualifyingE1S1Overdue.length + qualifyingE2S2.length + qualifyingE3S3.length} faktur`);
  console.log('');
}

analyze().catch(console.error);
