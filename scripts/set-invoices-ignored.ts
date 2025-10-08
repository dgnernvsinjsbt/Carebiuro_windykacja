/**
 * Skrypt do ustawienia flag LIST_POLECONY_IGNORED na fakturach testowych
 */

import { fakturowniaApi } from '../lib/fakturownia';

async function setInvoicesIgnored() {
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
[LIST_POLECONY]false[/LIST_POLECONY]
[LIST_POLECONY_SENT_DATE][/LIST_POLECONY_SENT_DATE]
[LIST_POLECONY_IGNORED]true[/LIST_POLECONY_IGNORED]
[LIST_POLECONY_IGNORED_DATE]2025-10-07[/LIST_POLECONY_IGNORED_DATE]`
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
[LIST_POLECONY]false[/LIST_POLECONY]
[LIST_POLECONY_SENT_DATE][/LIST_POLECONY_SENT_DATE]
[LIST_POLECONY_IGNORED]true[/LIST_POLECONY_IGNORED]
[LIST_POLECONY_IGNORED_DATE]2025-10-07[/LIST_POLECONY_IGNORED_DATE]`
    }
  ];

  console.log('Setting LIST_POLECONY_IGNORED=true on test invoices...');

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

setInvoicesIgnored().catch(console.error);
