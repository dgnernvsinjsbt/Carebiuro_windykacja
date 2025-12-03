import { createClient } from '@supabase/supabase-js';
import * as dotenv from 'dotenv';
dotenv.config();

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL as string,
  process.env.SUPABASE_SERVICE_ROLE_KEY as string
);

// The 22 client IDs that WERE visible before the fix (from earlier debug)
const VISIBLE_BEFORE_FIX = new Set([
  // These are the ones that showed up with the broken sync
  // We'll identify them by checking message_history
]);

async function main() {
  const today = new Date().toISOString().split('T')[0];

  console.log('=== WINDYKACJA REPORT ===');
  console.log('Date:', today);
  console.log('');

  // 1. Get all windykacja clients
  const { data: allClients } = await supabase
    .from('clients')
    .select('id, name, note, email')
    .like('note', '%[WINDYKACJA]true%');

  console.log(`Total windykacja clients: ${allClients?.length || 0}`);
  console.log('');

  // 2. Get today's message history
  const { data: todayMessages } = await supabase
    .from('message_history')
    .select('*')
    .gte('sent_at', today + 'T00:00:00')
    .lte('sent_at', today + 'T23:59:59');

  const clientsSentToday = new Set(todayMessages?.map(m => m.client_id) || []);
  console.log(`Messages sent today: ${todayMessages?.length || 0}`);
  console.log(`Unique clients sent to today: ${clientsSentToday.size}`);
  console.log('');

  // 3. Get unpaid invoices for windykacja clients
  const windykacjaClientIds = allClients?.map(c => c.id) || [];

  const { data: unpaidInvoices } = await supabase
    .from('invoices')
    .select('*')
    .in('client_id', windykacjaClientIds)
    .neq('status', 'paid')
    .neq('kind', 'canceled')
    .neq('kind', 'correction');

  console.log(`Unpaid invoices for windykacja clients: ${unpaidInvoices?.length || 0}`);
  console.log('');

  // 4. Check which clients have overdue invoices but weren't sent to
  const overdueByClient = new Map<number, any[]>();

  for (const inv of unpaidInvoices || []) {
    if (inv.payment_to && inv.payment_to < today) {
      if (!overdueByClient.has(inv.client_id)) {
        overdueByClient.set(inv.client_id, []);
      }
      overdueByClient.get(inv.client_id)!.push(inv);
    }
  }

  console.log(`Clients with overdue invoices: ${overdueByClient.size}`);
  console.log('');

  // 5. Find clients NOT sent to today but have overdue invoices
  const missedClients: any[] = [];

  for (const [clientId, invoices] of Array.from(overdueByClient.entries())) {
    if (!clientsSentToday.has(clientId)) {
      const client = allClients?.find(c => c.id === clientId);
      missedClients.push({
        client,
        overdueInvoices: invoices,
        totalOverdue: invoices.reduce((sum, inv) => sum + ((inv.total || 0) - (inv.paid || 0)), 0)
      });
    }
  }

  console.log('=== POTENTIALLY MISSED CLIENTS ===');
  console.log(`Clients with overdue invoices NOT sent to today: ${missedClients.length}`);
  console.log('');

  // Sort by total overdue amount
  missedClients.sort((a, b) => b.totalOverdue - a.totalOverdue);

  for (const missed of missedClients.slice(0, 20)) {
    const inv = missed.overdueInvoices[0];
    const daysOverdue = Math.floor((new Date().getTime() - new Date(inv.payment_to).getTime()) / (1000 * 60 * 60 * 24));

    console.log(`- ${missed.client?.name} (ID: ${missed.client?.id})`);
    console.log(`  Email: ${missed.client?.email || 'NO EMAIL'}`);
    console.log(`  Overdue invoices: ${missed.overdueInvoices.length}`);
    console.log(`  Total overdue: ${missed.totalOverdue.toFixed(2)} EUR`);
    console.log(`  Oldest overdue: ${inv.number} (${daysOverdue} days)`);
    console.log('');
  }

  if (missedClients.length > 20) {
    console.log(`... and ${missedClients.length - 20} more`);
  }

  // 6. Summary of what WAS sent today
  console.log('');
  console.log('=== SENT TODAY ===');
  const sentByType = {
    email: todayMessages?.filter(m => m.message_type === 'email').length || 0,
    sms: todayMessages?.filter(m => m.message_type === 'sms').length || 0,
  };
  console.log(`Emails: ${sentByType.email}`);
  console.log(`SMS: ${sentByType.sms}`);

  // List clients sent to
  console.log('');
  console.log('Clients sent to today:');
  for (const clientId of Array.from(clientsSentToday)) {
    const client = allClients?.find(c => c.id === clientId);
    const msgs = todayMessages?.filter(m => m.client_id === clientId);
    console.log(`- ${client?.name || clientId}: ${msgs?.length} message(s)`);
  }
}

main().catch(console.error);
