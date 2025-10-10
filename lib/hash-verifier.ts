/**
 * Aggressive Hash Verification & Cleanup
 *
 * This module handles immediate detection and cleanup of "Wystaw podobną" duplicates.
 * When a hash mismatch is detected, we IMMEDIATELY clean the internal_note in Fakturownia.
 */

import { FakturowniaInvoice } from '@/types';
import { generateInvoiceHash, verifyInvoiceHash, resetAllReminderFlags } from './invoice-hash';
import { parseFiscalSync, generateFiscalSync } from './fiscal-sync-parser';
import { supabase } from './supabase';
import { fakturowniaApi } from './fakturownia';

export interface HashVerificationResult {
  invoice_id: number;
  isValid: boolean;
  action: 'ok' | 'cleaned' | 'registered' | 'error';
  message: string;
  registryEntry?: {
    invoice_id: number;
    expected_hash: string;
  };
}

/**
 * Verify invoice hash and AGGRESSIVELY clean if mismatch
 *
 * Steps:
 * 1. Parse internal_note to get stored HASH
 * 2. Check invoice_hash_registry for expected hash
 * 3. If mismatch → IMMEDIATELY clean internal_note in Fakturownia
 * 4. Update Supabase invoice_hash_registry
 *
 * @param invoice - Fakturownia invoice to verify
 * @param cleanImmediately - If true, send HTTP request to Fakturownia to clean (default: true)
 * @returns Verification result with action taken
 */
export async function verifyAndCleanInvoiceHash(
  invoice: FakturowniaInvoice,
  cleanImmediately: boolean = true
): Promise<HashVerificationResult> {
  const invoiceId = invoice.id;
  const currentHash = generateInvoiceHash(invoice);

  // Parse internal_note
  const fiscalSync = parseFiscalSync(invoice.internal_note);
  const storedHashInNote = fiscalSync?.HASH || null;

  // Check registry for expected hash
  const { data: registryEntry } = await supabase()
    .from('invoice_hash_registry')
    .select('*')
    .eq('invoice_id', invoiceId)
    .single();

  const expectedHash = registryEntry?.expected_hash || null;

  // CASE 1: No hash stored anywhere → New invoice, never acted upon
  if (!storedHashInNote && !expectedHash) {
    return {
      invoice_id: invoiceId,
      isValid: true,
      action: 'ok',
      message: `Invoice ${invoiceId}: No hash stored. This is a new invoice with no actions taken yet.`,
    };
  }

  // CASE 2: Hash in internal_note matches current hash → Valid
  if (storedHashInNote === currentHash) {
    // Update registry if needed
    if (!registryEntry) {
      // Register this invoice
      await supabase()
        .from('invoice_hash_registry')
        .upsert({
          invoice_id: invoiceId,
          expected_hash: currentHash,
          first_action_date: new Date().toISOString(),
          last_verified_date: new Date().toISOString(),
        });

      return {
        invoice_id: invoiceId,
        isValid: true,
        action: 'registered',
        message: `Invoice ${invoiceId}: Hash valid (${currentHash}). Registered in hash_registry.`,
        registryEntry: {
          invoice_id: invoiceId,
          expected_hash: currentHash,
        },
      };
    }

    // Update last_verified_date
    await supabase()
      .from('invoice_hash_registry')
      .update({ last_verified_date: new Date().toISOString() })
      .eq('invoice_id', invoiceId);

    return {
      invoice_id: invoiceId,
      isValid: true,
      action: 'ok',
      message: `Invoice ${invoiceId}: Hash valid (${currentHash}).`,
    };
  }

  // CASE 3: Hash mismatch OR hash belongs to different invoice → DUPLICATE!
  console.warn(`🚨 [HashVerifier] DUPLICATE DETECTED for invoice ${invoiceId}!`);
  console.warn(`   Current hash: ${currentHash}`);
  console.warn(`   Stored hash in internal_note: ${storedHashInNote}`);
  console.warn(`   Expected hash from registry: ${expectedHash}`);

  // Check if this hash belongs to another invoice
  if (storedHashInNote) {
    const { data: otherInvoice } = await supabase()
      .from('invoice_hash_registry')
      .select('*')
      .eq('expected_hash', storedHashInNote)
      .single();

    if (otherInvoice && otherInvoice.invoice_id !== invoiceId) {
      console.warn(`   → Hash ${storedHashInNote} belongs to invoice ${otherInvoice.invoice_id}`);
      console.warn(`   → This invoice (${invoiceId}) was created via "Wystaw podobną" from invoice ${otherInvoice.invoice_id}`);
    }
  }

  // AGGRESSIVE CLEANUP
  if (cleanImmediately) {
    try {
      // Reset all reminder flags
      const cleanedFiscalSync = fiscalSync ? resetAllReminderFlags(fiscalSync) : null;
      const cleanedInternalNote = cleanedFiscalSync
        ? generateFiscalSync(cleanedFiscalSync)
        : '[FISCAL_SYNC]\n[/FISCAL_SYNC]';

      // Send HTTP request to Fakturownia to clean internal_note
      console.log(`[HashVerifier] Cleaning internal_note for invoice ${invoiceId}...`);
      await fakturowniaApi.updateInvoice(invoiceId, {
        internal_note: cleanedInternalNote,
      });

      console.log(`✅ [HashVerifier] Invoice ${invoiceId}: internal_note cleaned in Fakturownia`);

      // Remove from registry if exists
      if (registryEntry) {
        await supabase()
          .from('invoice_hash_registry')
          .delete()
          .eq('invoice_id', invoiceId);
        console.log(`✅ [HashVerifier] Invoice ${invoiceId}: removed from hash_registry`);
      }

      return {
        invoice_id: invoiceId,
        isValid: false,
        action: 'cleaned',
        message: `Invoice ${invoiceId}: Hash mismatch detected! Cleaned internal_note in Fakturownia. This invoice was likely created via "Wystaw podobną".`,
      };
    } catch (error: any) {
      console.error(`❌ [HashVerifier] Failed to clean invoice ${invoiceId}:`, error);
      return {
        invoice_id: invoiceId,
        isValid: false,
        action: 'error',
        message: `Invoice ${invoiceId}: Hash mismatch detected but cleanup failed: ${error.message}`,
      };
    }
  }

  // If cleanImmediately = false, just report the issue
  return {
    invoice_id: invoiceId,
    isValid: false,
    action: 'error',
    message: `Invoice ${invoiceId}: Hash mismatch detected but cleanImmediately=false. Manual intervention needed.`,
  };
}

/**
 * Register invoice hash on first action (e.g., sending first reminder)
 *
 * Call this when user takes the first action on an invoice (e.g., sends EMAIL_1).
 * This creates the hash and stores it in both internal_note and hash_registry.
 *
 * @param invoice - Fakturownia invoice
 * @returns Updated fiscal sync data with HASH field
 */
export async function registerInvoiceHashOnFirstAction(
  invoice: FakturowniaInvoice
): Promise<{ hash: string; fiscalSync: any }> {
  const hash = generateInvoiceHash(invoice);

  // Parse existing fiscal sync
  const fiscalSync = parseFiscalSync(invoice.internal_note) || {
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
    STOP: false,
    WINDYKACJA: false,
    HASH: null,
    UPDATED: new Date().toISOString(),
  };

  // Set hash
  fiscalSync.HASH = hash;

  // Register in hash_registry
  await supabase()
    .from('invoice_hash_registry')
    .upsert({
      invoice_id: invoice.id,
      expected_hash: hash,
      first_action_date: new Date().toISOString(),
      last_verified_date: new Date().toISOString(),
    });

  console.log(`✅ [HashVerifier] Invoice ${invoice.id}: Registered hash ${hash}`);

  return { hash, fiscalSync };
}

/**
 * Cleanup orphaned hashes (invoices that no longer exist in Fakturownia)
 *
 * Call this during nightly sync AFTER all invoices have been synced to Supabase.
 *
 * @param currentInvoiceIds - Array of invoice IDs currently in Supabase
 * @returns Number of orphaned entries removed
 */
export async function cleanupOrphanedHashes(currentInvoiceIds: number[]): Promise<number> {
  // Get all registry entries
  const { data: registryEntries } = await supabase()
    .from('invoice_hash_registry')
    .select('invoice_id');

  if (!registryEntries || registryEntries.length === 0) {
    return 0;
  }

  const currentIds = new Set(currentInvoiceIds);
  const orphanedIds = registryEntries
    .map((r) => r.invoice_id)
    .filter((id) => !currentIds.has(id));

  if (orphanedIds.length > 0) {
    console.log(`[HashVerifier] Removing ${orphanedIds.length} orphaned hash entries:`, orphanedIds.slice(0, 10));

    await supabase()
      .from('invoice_hash_registry')
      .delete()
      .in('invoice_id', orphanedIds);
  }

  return orphanedIds.length;
}

/**
 * Batch verify multiple invoices (used in sync routes)
 *
 * @param invoices - Array of Fakturownia invoices
 * @param cleanImmediately - If true, clean mismatched invoices immediately
 * @returns Array of verification results
 */
export async function batchVerifyInvoiceHashes(
  invoices: FakturowniaInvoice[],
  cleanImmediately: boolean = true
): Promise<HashVerificationResult[]> {
  const results: HashVerificationResult[] = [];

  for (const invoice of invoices) {
    const result = await verifyAndCleanInvoiceHash(invoice, cleanImmediately);
    results.push(result);

    // Add small delay to avoid rate limiting (1000 req/h = ~3.6s between requests)
    if (cleanImmediately && result.action === 'cleaned') {
      await new Promise((resolve) => setTimeout(resolve, 4000)); // 4 second delay
    }
  }

  return results;
}
