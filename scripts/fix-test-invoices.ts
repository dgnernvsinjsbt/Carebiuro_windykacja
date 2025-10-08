/**
 * Skrypt do naprawy testowych faktur - dodaje flagi LIST_POLECONY bez nadpisywania istniejących
 */

import { fakturowniaApi } from '../lib/fakturownia';

async function fixTestInvoices() {
  const invoiceIds = [423246738, 423246698];

  console.log('Fixing test invoices - adding LIST_POLECONY flags without overwriting existing...');

  for (const invoiceId of invoiceIds) {
    try {
      console.log(`\nFetching invoice ${invoiceId}...`);
      const invoice = await fakturowniaApi.getInvoice(invoiceId);

      console.log(`Current internal_note:\n${invoice.internal_note || '(empty)'}`);

      // Dodaj nowe flagi na końcu (nie nadpisuj istniejących)
      const newFlags = `[LIST_POLECONY]true[/LIST_POLECONY]
[LIST_POLECONY_SENT_DATE]2025-09-01[/LIST_POLECONY_SENT_DATE]`;

      const updatedNote = invoice.internal_note
        ? `${invoice.internal_note}\n${newFlags}`
        : newFlags;

      console.log(`\nUpdated internal_note:\n${updatedNote}`);

      await fakturowniaApi.updateInvoice(invoiceId, {
        internal_note: updatedNote
      });

      console.log(`✓ Invoice ${invoiceId} updated successfully`);
    } catch (error: any) {
      console.error(`✗ Error updating invoice ${invoiceId}:`, error.message);
    }
  }

  console.log('\n✓ All done!');
}

fixTestInvoices().catch(console.error);
