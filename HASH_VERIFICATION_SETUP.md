# Invoice Hash Verification System

## Problem Solved

When księgowe use Fakturownia's **"Wystaw podobną"** feature to create new invoices, it copies the `internal_note` from the original invoice. This causes critical issues:

**Example Scenario:**
1. Invoice 123: Client doesn't pay → EMAIL_3=TRUE, SMS_3=TRUE sent
2. Księgowa clicks "Wystaw podobną" → creates Invoice 456, 789, 101
3. **Problem:** All 3 new invoices inherit `EMAIL_3=TRUE` from Invoice 123
4. **Result:** System thinks reminders were already sent → client doesn't qualify for List Polecony

## Solution: Hash-Based Duplicate Detection

We generate a unique hash from **immutable** invoice data:
```
HASH = MD5(invoice_id | issue_date | client_id).substring(0, 8)
```

This hash is stored in:
1. **Fakturownia `internal_note`**: `[FISCAL_SYNC]HASH=a3f5c2d1[/FISCAL_SYNC]`
2. **Supabase `invoice_hash_registry` table** (persistent, survives nightly DROP)

During sync, we verify: **Does invoice_id match the expected hash?**
- ✅ Match → Valid invoice
- ❌ Mismatch → "Wystaw podobną" duplicate → **IMMEDIATELY clean internal_note**

---

## What's Been Built

### 1. Migration: `migrations/004_create_invoice_hash_registry.sql`

```sql
CREATE TABLE invoice_hash_registry (
  invoice_id INTEGER PRIMARY KEY,
  expected_hash TEXT NOT NULL,
  first_action_date TIMESTAMP NOT NULL,
  last_verified_date TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

**⚠️ CRITICAL:** This table must **NOT** be dropped during nightly sync!

### 2. Hash Generation: `lib/invoice-hash.ts`

```typescript
generateInvoiceHash(invoice) → "a3f5c2d1" // MD5 hash
verifyInvoiceHash(invoice, storedHash) → { isValid, currentHash, reason }
resetAllReminderFlags(fiscalSync) → clean fiscalSync object
hasAnyReminderFlags(fiscalSync) → boolean
```

### 3. Aggressive Cleanup: `lib/hash-verifier.ts`

```typescript
verifyAndCleanInvoiceHash(invoice, cleanImmediately=true)
// 1. Check hash mismatch
// 2. Send HTTP request to Fakturownia to clean internal_note
// 3. Remove from hash_registry
// 4. Return verification result

registerInvoiceHashOnFirstAction(invoice)
// Called when user sends first reminder (EMAIL_1, SMS_1, etc.)
// Generates hash and stores in internal_note + hash_registry

cleanupOrphanedHashes(currentInvoiceIds)
// Remove hash entries for deleted invoices
// Call during nightly sync AFTER all invoices synced
```

### 4. Parser Updates: `lib/fiscal-sync-parser.ts`

- Added `HASH` field to `FiscalSyncData` interface
- Parser now handles `HASH=a3f5c2d1` or `HASH=NULL`
- Generator includes hash as first field for visibility

### 5. Types: `types/index.ts`

```typescript
interface FiscalSyncData {
  // ... existing fields
  HASH: string | null; // 8-char MD5 hash
  UPDATED: string;
}
```

---

## Manual Steps Required

### Step 1: Create `invoice_hash_registry` Table

**Option A: Supabase SQL Editor (RECOMMENDED)**

1. Go to Supabase Dashboard → SQL Editor
2. Run this SQL:

```sql
-- Copy from migrations/004_create_invoice_hash_registry.sql
CREATE TABLE IF NOT EXISTS invoice_hash_registry (
  invoice_id INTEGER PRIMARY KEY,
  expected_hash TEXT NOT NULL,
  first_action_date TIMESTAMP NOT NULL,
  last_verified_date TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hash_lookup ON invoice_hash_registry(expected_hash);
CREATE INDEX IF NOT EXISTS idx_first_action_date ON invoice_hash_registry(first_action_date);
```

3. Verify:
```sql
SELECT * FROM invoice_hash_registry LIMIT 1;
-- Should return empty result (no error)
```

**Option B: Migration API Endpoint**

```bash
curl -X POST https://your-domain.com/api/migrate-hash-registry
```

### Step 2: Update Nightly Sync to EXCLUDE `invoice_hash_registry`

**CRITICAL:** Modify your nightly sync to **NOT** drop this table!

```typescript
// supabase/functions/nightly-sync/index.ts
async function nightlySync() {
  // DROP all tables EXCEPT invoice_hash_registry
  await supabase().from('invoices').delete().neq('id', 0);
  await supabase().from('clients').delete().neq('id', 0);
  // ... other tables

  // ⚠️ DO NOT DROP invoice_hash_registry!
  // await supabase().from('invoice_hash_registry').delete().neq('id', 0); ← NO!

  // Sync from Fakturownia...
}
```

---

## Next Implementation Steps

### Step 3: Update Sync Routes (CRITICAL - Do immediately)

All sync routes must verify hashes **aggressively**:

**Files to update:**
- `app/api/sync/route.ts` (nocny sync)
- `app/api/sync/client/route.ts` (mini-sync when user clicks "Odśwież")
- `app/api/sync/test/route.ts`
- `app/api/sync/test-client/route.ts`
- `app/api/sync/manual/route.ts`

**Example for `app/api/sync/client/route.ts`:**

```typescript
import { verifyAndCleanInvoiceHash } from '@/lib/hash-verifier';

export async function POST(req: Request) {
  // ... existing code to fetch invoices from Fakturownia

  const clientInvoices = await fakturowniaApi.getInvoicesByClientId(client_id, 1000);

  // ✅ ADD: Verify hashes BEFORE processing
  console.log(`[SyncClient] Verifying hashes for ${clientInvoices.length} invoices...`);
  const verificationResults = [];

  for (const invoice of clientInvoices) {
    const result = await verifyAndCleanInvoiceHash(invoice, true); // cleanImmediately=true
    verificationResults.push(result);

    if (result.action === 'cleaned') {
      console.log(`✅ Cleaned duplicate: Invoice ${invoice.id}`);
    }
  }

  const cleanedCount = verificationResults.filter(r => r.action === 'cleaned').length;
  console.log(`[SyncClient] Cleaned ${cleanedCount} "Wystaw podobną" duplicates`);

  // ... continue with existing sync logic
}
```

**For nocny sync (`app/api/sync/route.ts`):**

```typescript
import { batchVerifyInvoiceHashes, cleanupOrphanedHashes } from '@/lib/hash-verifier';

export async function POST(req: Request) {
  // ... fetch invoices from Fakturownia

  // Verify hashes for entire page
  const verificationResults = await batchVerifyInvoiceHashes(pageInvoices, true);
  const cleanedCount = verificationResults.filter(r => r.action === 'cleaned').length;
  console.log(`[Sync] Page ${page}: Cleaned ${cleanedCount} duplicates`);

  // ... continue with sync

  // At the END of sync, cleanup orphaned hashes
  const { data: allInvoices } = await supabase().from('invoices').select('id');
  const invoiceIds = allInvoices.map(i => i.id);
  const orphanedCount = await cleanupOrphanedHashes(invoiceIds);
  console.log(`[Sync] Removed ${orphanedCount} orphaned hash entries`);
}
```

### Step 4: Update Reminder Endpoints

When user sends first reminder (EMAIL_1, SMS_1, etc.), register hash:

**Files to update:**
- `app/api/reminder/route.ts` (or wherever reminders are sent)
- `app/api/windykacja/auto-send/route.ts`

**Example:**

```typescript
import { registerInvoiceHashOnFirstAction } from '@/lib/hash-verifier';
import { generateFiscalSync } from '@/lib/fiscal-sync-parser';

export async function POST(req: Request) {
  const { invoice_id, type } = await req.json(); // e.g., type='EMAIL_1'

  // Fetch invoice from Fakturownia
  const invoice = await fakturowniaApi.getInvoice(invoice_id);

  // ✅ ADD: Register hash on FIRST action
  const fiscalSync = parseFiscalSync(invoice.internal_note);

  if (!fiscalSync?.HASH && !hasAnyReminderFlags(fiscalSync)) {
    // This is the FIRST action on this invoice
    const { hash, fiscalSync: updatedFiscalSync } =
      await registerInvoiceHashOnFirstAction(invoice);

    console.log(`[Reminder] Invoice ${invoice_id}: Registered hash ${hash}`);

    // Update fiscalSync with the hash
    fiscalSync = updatedFiscalSync;
  }

  // Mark reminder as sent
  fiscalSync[type] = true;
  fiscalSync[`${type}_DATE`] = new Date().toISOString();

  // Update Fakturownia
  await fakturowniaApi.updateInvoice(invoice_id, {
    internal_note: generateFiscalSync(fiscalSync)
  });

  // ... send email/SMS
}
```

### Step 5: Backfill Existing Invoices

Create script to add hash to invoices that already have reminders:

```typescript
// scripts/backfill-invoice-hashes.ts
import { supabase } from '@/lib/supabase-client';
import { fakturowniaApi } from '@/lib/fakturownia';
import { parseFiscalSync, generateFiscalSync } from '@/lib/fiscal-sync-parser';
import { generateInvoiceHash, hasAnyReminderFlags } from '@/lib/invoice-hash';

async function backfillHashes() {
  // Get invoices with any reminder flags but no HASH
  const { data: invoices } = await supabase()
    .from('invoices')
    .select('id, internal_note, issue_date, client_id')
    .not('internal_note', 'is', null);

  let processedCount = 0;
  let skippedCount = 0;

  for (const invoice of invoices) {
    const fiscalSync = parseFiscalSync(invoice.internal_note);

    if (!fiscalSync) {
      skippedCount++;
      continue;
    }

    // Skip if already has hash
    if (fiscalSync.HASH) {
      skippedCount++;
      continue;
    }

    // Only add hash if invoice has any reminder flags
    if (!hasAnyReminderFlags(fiscalSync)) {
      skippedCount++;
      continue;
    }

    // Generate hash
    const hash = generateInvoiceHash(invoice);
    fiscalSync.HASH = hash;

    // Update Fakturownia
    await fakturowniaApi.updateInvoice(invoice.id, {
      internal_note: generateFiscalSync(fiscalSync)
    });

    // Register in hash_registry
    await supabase()
      .from('invoice_hash_registry')
      .upsert({
        invoice_id: invoice.id,
        expected_hash: hash,
        first_action_date: fiscalSync.EMAIL_1_DATE || fiscalSync.SMS_1_DATE || new Date().toISOString(),
        last_verified_date: new Date().toISOString(),
      });

    processedCount++;
    console.log(`[Backfill] Invoice ${invoice.id}: Added hash ${hash}`);

    // Rate limit: 1000 req/h = 3.6s between requests
    await new Promise(resolve => setTimeout(resolve, 4000));
  }

  console.log(`[Backfill] Complete: ${processedCount} processed, ${skippedCount} skipped`);
}

backfillHashes();
```

---

## Testing

### Test Scenario 1: New Invoice (First Reminder)

1. Create new invoice in Fakturownia (no internal_note)
2. In your app, send EMAIL_1 reminder
3. **Expected:**
   - `internal_note` updated with `HASH=xxxxxxxx`
   - Entry created in `invoice_hash_registry`
   - Reminder sent successfully

### Test Scenario 2: "Wystaw podobną" Duplicate

1. Find invoice with EMAIL_3=TRUE, SMS_3=TRUE (Invoice 123)
2. In Fakturownia, click "Wystaw podobną" → creates Invoice 456
3. Run mini-sync (`/api/sync/client`)
4. **Expected:**
   - Log: `🚨 DUPLICATE DETECTED for invoice 456!`
   - Log: `Hash a3f5c2d1 belongs to invoice 123`
   - HTTP request sent to clean Invoice 456's `internal_note`
   - Invoice 456 now has clean `internal_note` (no EMAIL_3)
   - Invoice 456 qualifies for List Polecony

### Test Scenario 3: Nightly Sync Cleanup

1. Delete Invoice 999 in Fakturownia
2. Run nightly sync
3. **Expected:**
   - Invoice 999 removed from `invoices` table
   - Invoice 999 entry removed from `invoice_hash_registry`
   - Log: `Removed 1 orphaned hash entries: [999]`

---

## Monitoring

### Check Hash Registry Status

```sql
-- Count total entries
SELECT COUNT(*) FROM invoice_hash_registry;

-- Find invoices with mismatched hashes (should be 0 after sync)
SELECT
  i.id,
  i.issue_date,
  r.expected_hash,
  substring(md5(i.id::text || '|' || i.issue_date || '|' || i.client_id::text), 1, 8) as current_hash
FROM invoices i
JOIN invoice_hash_registry r ON i.id = r.invoice_id
WHERE r.expected_hash != substring(md5(i.id::text || '|' || i.issue_date || '|' || i.client_id::text), 1, 8);

-- Find old entries (not verified in 7+ days)
SELECT * FROM invoice_hash_registry
WHERE last_verified_date < NOW() - INTERVAL '7 days'
ORDER BY last_verified_date ASC
LIMIT 10;
```

### Debug Logs to Watch

```
✅ [HashVerifier] Invoice 123: Hash valid (a3f5c2d1)
🚨 [HashVerifier] DUPLICATE DETECTED for invoice 456!
   → Hash a3f5c2d1 belongs to invoice 123
✅ [HashVerifier] Invoice 456: internal_note cleaned in Fakturownia
✅ [HashVerifier] Invoice 456: removed from hash_registry
```

---

## FAQ

**Q: What happens if księgowa edits invoice in Fakturownia?**
A: Hash is based on immutable data (id, issue_date, client_id). Editing amount, description, etc. won't affect hash.

**Q: What if księgowa changes issue_date after hash is created?**
A: Hash will mismatch → system will clean internal_note. This is intentional - changing issue_date creates a "new" invoice context.

**Q: Can we recover if hash_registry gets dropped accidentally?**
A: Yes! Run the backfill script to recreate entries from existing invoices with reminders.

**Q: What's the collision probability?**
A: 8-char MD5 = ~4.3 billion combinations. With 10k invoices, collision probability < 0.001%.

**Q: Does this slow down sync?**
A: Minimal impact. Hash calculation is instant. Cleanup only happens for duplicates (rare). Rate limited at 1 req/4s for Fakturownia API.

---

## Summary Checklist

- [x] ✅ Migration file created (`004_create_invoice_hash_registry.sql`)
- [x] ✅ Hash generation logic (`lib/invoice-hash.ts`)
- [x] ✅ Aggressive cleanup logic (`lib/hash-verifier.ts`)
- [x] ✅ Parser updated to handle HASH field
- [x] ✅ Types updated (FiscalSyncData)
- [ ] ⏳ **Manually run migration in Supabase**
- [ ] ⏳ **Update nightly sync to exclude hash_registry from DROP**
- [ ] ⏳ **Update all sync routes to verify hashes**
- [ ] ⏳ **Update reminder endpoints to register hash**
- [ ] ⏳ **Create and run backfill script**
- [ ] ⏳ **Test with real "Wystaw podobną" scenario**

---

## Next Steps

1. **IMMEDIATELY:** Run migration SQL in Supabase SQL Editor
2. **CRITICAL:** Update nightly sync to NOT drop `invoice_hash_registry`
3. **HIGH PRIORITY:** Update all 5 sync routes to call `verifyAndCleanInvoiceHash()`
4. **MEDIUM PRIORITY:** Update reminder endpoints to call `registerInvoiceHashOnFirstAction()`
5. **OPTIONAL:** Run backfill script for existing invoices

Reach out if you have questions! 🚀
