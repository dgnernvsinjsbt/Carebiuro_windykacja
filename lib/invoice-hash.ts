/**
 * Invoice Hash Generation & Verification
 *
 * Purpose: Detect "Wystaw podobną" duplicates in Fakturownia
 *
 * How it works:
 * 1. Generate hash from IMMUTABLE invoice data (id, issue_date, client_id)
 * 2. Store hash in internal_note: [FISCAL_SYNC]HASH=a3f5c2d1[/FISCAL_SYNC]
 * 3. Persist mapping in invoice_hash_registry table
 * 4. During sync: verify invoice_id matches expected hash
 * 5. If mismatch → invoice was created via "Wystaw podobną" → clean internal_note
 */

import crypto from 'crypto';
import { FakturowniaInvoice } from '@/types';

/**
 * Generate MD5 hash from immutable invoice data
 *
 * @param invoice - Invoice object with id, issue_date, client_id
 * @returns First 8 characters of MD5 hash (e.g., "a3f5c2d1")
 */
export function generateInvoiceHash(invoice: {
  id: number;
  issue_date: string;
  client_id: number;
}): string {
  // Hash IMMUTABLE data that won't change even if invoice is edited
  const data = `${invoice.id}|${invoice.issue_date}|${invoice.client_id}`;

  const hash = crypto
    .createHash('md5')
    .update(data)
    .digest('hex');

  // Return first 8 chars (collision probability: ~1 in 4 billion)
  return hash.substring(0, 8);
}

/**
 * Verify invoice hash matches stored hash in internal_note
 *
 * @param invoice - Fakturownia invoice with internal_note
 * @param storedHash - Expected hash from invoice_hash_registry or internal_note
 * @returns Verification result with details
 */
export function verifyInvoiceHash(
  invoice: FakturowniaInvoice,
  storedHash: string | null
): {
  isValid: boolean;
  currentHash: string;
  storedHash: string | null;
  reason?: string;
} {
  const currentHash = generateInvoiceHash(invoice);

  // No stored hash = no verification needed (new invoice or never acted upon)
  if (!storedHash) {
    return {
      isValid: true, // Consider valid if no hash stored
      currentHash,
      storedHash: null,
      reason: 'No stored hash - new invoice or no actions taken yet',
    };
  }

  // Hash matches = valid
  if (storedHash === currentHash) {
    return {
      isValid: true,
      currentHash,
      storedHash,
    };
  }

  // Hash mismatch = DUPLICATE from "Wystaw podobną"
  return {
    isValid: false,
    currentHash,
    storedHash,
    reason: `Hash mismatch! Expected ${currentHash} but found ${storedHash}. This invoice was likely created via "Wystaw podobną" and copied internal_note from another invoice.`,
  };
}

/**
 * Check if invoice has any reminder flags set
 * Used to determine if we need to verify hash
 */
export function hasAnyReminderFlags(fiscalSync: any): boolean {
  return !!(
    fiscalSync.EMAIL_1 ||
    fiscalSync.EMAIL_2 ||
    fiscalSync.EMAIL_3 ||
    fiscalSync.SMS_1 ||
    fiscalSync.SMS_2 ||
    fiscalSync.SMS_3 ||
    fiscalSync.WHATSAPP_1 ||
    fiscalSync.WHATSAPP_2 ||
    fiscalSync.WHATSAPP_3
  );
}

/**
 * Reset all reminder flags in fiscal sync data
 * Used when we detect a "Wystaw podobną" duplicate
 */
export function resetAllReminderFlags(fiscalSync: any): any {
  return {
    ...fiscalSync,
    // Clear all reminder flags
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
    WHATSAPP_1: false,
    WHATSAPP_1_DATE: null,
    WHATSAPP_2: false,
    WHATSAPP_2_DATE: null,
    WHATSAPP_3: false,
    WHATSAPP_3_DATE: null,
    // Clear list polecony status
    LIST_POLECONY_STATUS: 'false',
    // Keep WINDYKACJA and STOP flags (user preferences)
    // Keep UPDATED timestamp
    // Clear HASH - will be regenerated if user takes action
    HASH: null,
  };
}
