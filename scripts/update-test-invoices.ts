/**
 * Skrypt do aktualizacji testowych faktur z flagami LIST_POLECONY
 */

import { fakturowniaApi } from '../lib/fakturownia';

async function updateTestInvoices() {
  const invoiceIds = [423246738, 423246698];
  const internalNote = `[LIST_POLECONY]true[/LIST_POLECONY]
[LIST_POLECONY_SENT_DATE]2025-09-01[/LIST_POLECONY_SENT_DATE]`;

  console.log('Updating test invoices with LIST_POLECONY flags...');

  for (const invoiceId of invoiceIds) {
    try {
      console.log(`\nUpdating invoice ${invoiceId}...`);
      await fakturowniaApi.updateInvoice(invoiceId, {
        internal_note: internalNote
      });
      console.log(`✓ Invoice ${invoiceId} updated successfully`);
    } catch (error: any) {
      console.error(`✗ Error updating invoice ${invoiceId}:`, error.message);
    }
  }

  console.log('\n✓ All done!');
}

updateTestInvoices().catch(console.error);
