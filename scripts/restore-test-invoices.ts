/**
 * Skrypt do przywrócenia flag windykacji + dodanie flag LIST_POLECONY
 */

import { fakturowniaApi } from '../lib/fakturownia';

async function restoreTestInvoices() {
  const invoices = [
    {
      id: 423246738,
      note: `[FISCAL_SYNC]
EMAIL_1=FALSE
EMAIL_1_DATE=NULL
EMAIL_2=FALSE
EMAIL_2_DATE=NULL
EMAIL_3=FALSE
EMAIL_3_DATE=NULL
SMS_1=FALSE
SMS_1_DATE=NULL
SMS_2=FALSE
SMS_2_DATE=NULL
SMS_3=FALSE
SMS_3_DATE=NULL
WHATSAPP_1=FALSE
WHATSAPP_1_DATE=NULL
WHATSAPP_2=FALSE
WHATSAPP_2_DATE=NULL
WHATSAPP_3=FALSE
WHATSAPP_3_DATE=NULL
STOP=TRUE
UPDATED=2025-10-06T21:16:16.068Z
[/FISCAL_SYNC]
[LIST_POLECONY]true[/LIST_POLECONY]
[LIST_POLECONY_SENT_DATE]2025-09-01[/LIST_POLECONY_SENT_DATE]`
    },
    {
      id: 423246698,
      note: `[FISCAL_SYNC]
EMAIL_1=FALSE
EMAIL_1_DATE=NULL
EMAIL_2=FALSE
EMAIL_2_DATE=NULL
EMAIL_3=FALSE
EMAIL_3_DATE=NULL
SMS_1=FALSE
SMS_1_DATE=NULL
SMS_2=FALSE
SMS_2_DATE=NULL
SMS_3=FALSE
SMS_3_DATE=NULL
WHATSAPP_1=FALSE
WHATSAPP_1_DATE=NULL
WHATSAPP_2=FALSE
WHATSAPP_2_DATE=NULL
WHATSAPP_3=FALSE
WHATSAPP_3_DATE=NULL
STOP=TRUE
UPDATED=2025-10-06T21:16:16.068Z
[/FISCAL_SYNC]
[LIST_POLECONY]true[/LIST_POLECONY]
[LIST_POLECONY_SENT_DATE]2025-09-01[/LIST_POLECONY_SENT_DATE]`
    }
  ];

  console.log('Restoring test invoices with full flags...');

  for (const { id, note } of invoices) {
    try {
      console.log(`\nUpdating invoice ${id}...`);
      await fakturowniaApi.updateInvoice(id, {
        internal_note: note
      });
      console.log(`✓ Invoice ${id} updated successfully`);
    } catch (error: any) {
      console.error(`✗ Error updating invoice ${id}:`, error.message);
    }
  }

  console.log('\n✓ All done!');
}

restoreTestInvoices().catch(console.error);
