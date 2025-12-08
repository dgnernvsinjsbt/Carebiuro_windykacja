import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
dotenv.config();

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

console.log('Checking STATUS of duplicate invoices in Supabase:\n');

// Check specific duplicate pairs
const duplicateIds = [
  [250157192, 440746880], // FP2023/11/001043
  [261274212, 420986258], // FP2023/12/001122
  [263922810, 421011621], // FP2024/02/001052
  [263926983, 420050381], // FP2024/02/001056
];

for (const [originalId, duplicateId] of duplicateIds) {
  const { data } = await supabase
    .from('invoices')
    .select('id, number, status, created_at, sent_time')
    .in('id', [originalId, duplicateId])
    .order('id');

  if (data && data.length === 2) {
    console.log(`=== ${data[0].number} ===`);
    console.log(`  Original  (${originalId}): status="${data[0].status}", created=${data[0].created_at}, sent=${data[0].sent_time || 'null'}`);
    console.log(`  Duplicate (${duplicateId}): status="${data[1].status}", created=${data[1].created_at}, sent=${data[1].sent_time || 'null'}`);
    console.log();
  }
}

// Now check: how many invoices with status "canceled" are in the system?
const { data: canceledInvoices, count: canceledCount } = await supabase
  .from('invoices')
  .select('id, number, status', { count: 'exact' })
  .eq('status', 'canceled');

console.log(`\n📊 Total invoices with status="canceled": ${canceledCount}`);

if (canceledInvoices && canceledInvoices.length > 0) {
  console.log('\nFirst 10 canceled invoices:');
  canceledInvoices.slice(0, 10).forEach(inv => {
    console.log(`  ${inv.number} (ID: ${inv.id})`);
  });
}
