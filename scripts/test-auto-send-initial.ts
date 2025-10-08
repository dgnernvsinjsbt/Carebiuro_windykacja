/**
 * Test script for auto-send initial messages (E1/S1/W1)
 *
 * Usage:
 *   npx ts-node scripts/test-auto-send-initial.ts
 *
 * This will call the auto-send endpoint and display results
 */

async function testAutoSendInitial() {
  console.log('🧪 Testing auto-send initial messages (E1/S1/W1)...\n');

  const apiUrl = process.env.API_URL || 'http://localhost:3000';
  const endpoint = `${apiUrl}/api/windykacja/auto-send-initial`;

  console.log(`📡 Calling: ${endpoint}\n`);

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });

    const result = await response.json();

    if (response.ok) {
      console.log('✅ Success!\n');
      console.log('📊 Summary:');
      console.log(`  - Total sent: ${result.sent.total}`);
      console.log(`  - E1 (email): ${result.sent.email}`);
      console.log(`  - S1 (SMS): ${result.sent.sms}`);
      console.log(`  - W1 (WhatsApp): ${result.sent.whatsapp}`);
      console.log(`  - Failed: ${result.failed}\n`);

      if (result.results && result.results.length > 0) {
        console.log('📋 Detailed results:');
        result.results.forEach((invoice: any) => {
          console.log(`\n  Invoice ${invoice.invoice_number} (#${invoice.invoice_id}):`);
          if (invoice.sent.length > 0) {
            console.log(`    ✅ Sent: ${invoice.sent.join(', ')}`);
          }
          if (invoice.failed.length > 0) {
            console.log(`    ❌ Failed:`);
            invoice.failed.forEach((fail: any) => {
              console.log(`       - ${fail.type}: ${fail.error}`);
            });
          }
        });
      }
    } else {
      console.error('❌ Error:', result.error);
      if (result.details) {
        console.error('Details:', result.details);
      }
    }
  } catch (error: any) {
    console.error('❌ Exception:', error.message);
    console.error(error.stack);
  }
}

// Run test
testAutoSendInitial();
