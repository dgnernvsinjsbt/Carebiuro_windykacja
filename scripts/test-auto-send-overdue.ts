/**
 * Test script for auto-send-overdue endpoint
 *
 * Usage:
 *   npx tsx scripts/test-auto-send-overdue.ts
 */

async function testAutoSendOverdue() {
  console.log('\n🧪 Testing auto-send-overdue endpoint...\n');

  const apiUrl = process.env.NEXT_PUBLIC_VERCEL_URL
    ? `https://${process.env.NEXT_PUBLIC_VERCEL_URL}/api/windykacja/auto-send-overdue`
    : 'http://localhost:3000/api/windykacja/auto-send-overdue';

  console.log(`📡 Calling: ${apiUrl}\n`);

  try {
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });

    const data = await response.json();

    if (data.success) {
      console.log('✅ Success!\n');
      console.log(`📊 Results:`);
      console.log(`   Clients processed: ${data.clients_processed}`);
      console.log(`   Total sent: ${data.sent.total}`);
      console.log(`   - E1 (email): ${data.sent.email}`);
      console.log(`   - S1 (SMS): ${data.sent.sms}`);
      console.log(`   Failed: ${data.failed}\n`);

      if (data.results && data.results.length > 0) {
        console.log('📋 Detailed results:');
        data.results.forEach((result: any, index: number) => {
          console.log(`\n   ${index + 1}. ${result.client_name} - ${result.invoice_number}`);
          if (result.email_sent) console.log(`      ✓ E1 sent`);
          if (result.sms_sent) console.log(`      ✓ S1 sent`);
          if (result.error) console.log(`      ✗ Error: ${result.error}`);
        });
      }

      console.log(`\n💬 Message: ${data.message}\n`);
    } else {
      console.log('❌ Failed!\n');
      console.log(`Error: ${data.error}\n`);
    }
  } catch (error: any) {
    console.error('❌ Request failed:', error.message);
  }
}

testAutoSendOverdue();
