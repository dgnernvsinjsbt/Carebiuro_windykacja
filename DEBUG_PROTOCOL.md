# 🔍 DEBUG PROTOCOL — Systematic Bug Investigation Framework

## **CRITICAL RULE**: Never assume. Always verify.

When you encounter a bug or unexpected behavior, you MUST follow this protocol **methodically and completely**. Do NOT skip steps. Do NOT make assumptions. Each step builds evidence for the next.

---

## Phase 1: STOP & DEFINE (5 minutes)

### 1.1 Acknowledge the Problem
```
❌ BAD:  "I'll fix the email sending issue"
✅ GOOD: "PROBLEM IDENTIFIED: E1 emails are going to sandbox instead of production"
```

**Required Actions:**
- [ ] Write down the EXACT symptom (what is broken)
- [ ] Write down the EXPECTED behavior (what should happen)
- [ ] Write down the ACTUAL behavior (what is happening instead)
- [ ] Identify WHO reported it (user screenshot, error log, test failure)
- [ ] Identify WHEN it started (after which commit/deployment/change)

### 1.2 Reproduce the Bug
**Never debug something you can't reproduce.**

- [ ] Can you reproduce it locally? (Yes/No)
- [ ] Can you reproduce it in staging? (Yes/No)
- [ ] Can you reproduce it in production? (Yes/No)
- [ ] What are the EXACT steps to reproduce?
- [ ] Does it happen 100% of the time or intermittently?
- [ ] Are there specific conditions (time, data, user role)?

**Output Template:**
```markdown
## Bug Reproduction
- **Environment**: [Local / Staging / Production]
- **Frequency**: [Always / Sometimes / Rare]
- **Steps**:
  1. Navigate to /client/123
  2. Click "E1" button on invoice #456
  3. Check email destination
- **Expected**: Email sent to client@example.com
- **Actual**: Email sent to cbb.krd@gmail.com
```

---

## Phase 2: GATHER EVIDENCE (10 minutes)

### 2.1 Collect All Error Messages
- [ ] Browser console errors (with full stack trace)
- [ ] Network tab errors (API failures, 4xx/5xx responses)
- [ ] Server logs (Vercel, Supabase, n8n)
- [ ] Database errors (Supabase logs)
- [ ] Email/SMS service logs (Mailgun, Twilio)

**For EACH error:**
```markdown
### Error #1
- **Source**: Browser console
- **Timestamp**: 2025-10-10 14:32:15
- **Full Message**:
  ```
  TypeError: Cannot read property 'email' of undefined
      at sendEmail (/app/api/email/route.ts:42)
      at POST (/app/api/email/route.ts:18)
  ```
- **Context**: Occurred when clicking E1 button for invoice #789
```

### 2.2 Trace Data Flow
**Draw the complete path from UI to database and back.**

Example:
```
[UI Button Click]
    ↓
[onClick handler] → What data is passed?
    ↓
[API Route /api/email] → What does request.body contain?
    ↓
[Mailgun API call] → What email/domain is used?
    ↓
[Response] → What comes back?
    ↓
[UI Update] → What does user see?
```

**For EACH step, verify:**
- [ ] What INPUT does this step receive?
- [ ] What PROCESSING happens?
- [ ] What OUTPUT does it produce?
- [ ] What ASSUMPTIONS are made? (e.g., "email field exists")

### 2.3 Check Environment Variables
**Never trust environment variables. Always verify.**

- [ ] List ALL env vars related to the bug
- [ ] Check if they're set in `.env.local` (local)
- [ ] Check if they're set in Vercel (production/preview)
- [ ] Verify the VALUES are correct (not just that they exist)
- [ ] Check for typos in variable NAMES
- [ ] Check for trailing spaces in VALUES

**Template:**
```bash
# Local (.env.local)
MAILGUN_DOMAIN=cbb-office.pl ✅
MAILGUN_API_KEY=key-abc123... ✅
EMAIL_MODE=production ✅

# Vercel (Production)
MAILGUN_DOMAIN=??? ❓ (NEED TO CHECK)
MAILGUN_API_KEY=??? ❓
EMAIL_MODE=??? ❓

# Vercel (Preview)
[same as above]
```

### 2.4 Check Database State
**The database is the source of truth.**

- [ ] Query the EXACT data involved in the bug
- [ ] Check for NULL values, unexpected data types, truncated strings
- [ ] Verify relationships (FK constraints, joins)
- [ ] Check timestamps (is data stale?)

**Example:**
```sql
-- Get the invoice that failed
SELECT * FROM invoices WHERE id = 789;

-- Check the client
SELECT * FROM clients WHERE id = (SELECT client_id FROM invoices WHERE id = 789);

-- Verify fiscal_sync data
SELECT id, number, internal_note FROM invoices WHERE id = 789;
```

**Output:**
```markdown
### Database Evidence
- **Invoice #789**:
  - number: "FV2025/10/123"
  - client_id: 456
  - internal_note: `[FISCAL_SYNC]{"EMAIL_1":true}[/FISCAL_SYNC]` ✅

- **Client #456**:
  - name: "ACME Corp"
  - email: NULL ❌ ← PROBLEM FOUND
  - phone: "+48123456789" ✅
```

---

## Phase 3: ISOLATE THE ROOT CAUSE (15 minutes)

### 3.1 Binary Search Through Code
**Narrow down the exact line where the bug occurs.**

Start with the WIDEST scope, then zoom in:

1. **Module level**: Which file contains the bug?
   - [ ] UI component? (`components/`, `app/`)
   - [ ] API route? (`app/api/`)
   - [ ] Database query? (`lib/supabase.ts`)
   - [ ] External API? (`lib/fakturownia.ts`, `lib/mailgun.ts`)

2. **Function level**: Which function is faulty?
   - [ ] Add `console.log` at ENTRY of each function
   - [ ] Add `console.log` at EXIT of each function
   - [ ] Log the INPUT and OUTPUT of each function

3. **Line level**: Which exact line causes the issue?
   - [ ] Comment out half the function
   - [ ] Does bug still occur? (Yes → bug is in other half)
   - [ ] Repeat until you find the exact line

**Template:**
```typescript
// BEFORE (buggy)
async function sendEmail(invoiceId: string) {
  const invoice = await getInvoice(invoiceId);
  const client = await getClient(invoice.client_id);
  await mailgun.send(client.email, template); // ❌ Crashes here if client.email is NULL
}

// AFTER (with debug logs)
async function sendEmail(invoiceId: string) {
  console.log('[sendEmail] START', { invoiceId });

  const invoice = await getInvoice(invoiceId);
  console.log('[sendEmail] invoice =', invoice);

  const client = await getClient(invoice.client_id);
  console.log('[sendEmail] client =', client);
  console.log('[sendEmail] client.email =', client.email); // ← NULL!

  await mailgun.send(client.email, template);
  console.log('[sendEmail] END');
}
```

### 3.2 Test Hypothesis
**Form a hypothesis, then TEST it.**

```markdown
### Hypothesis #1: Email field is NULL in database
- **Evidence**: Query shows `SELECT email FROM clients WHERE id=456` returns NULL
- **Test**: Insert test email, retry → WORKS ✅
- **Conclusion**: Bug is NULL email, not Mailgun config

### Hypothesis #2: Environment variable not set in Vercel
- **Evidence**: Local works, production fails
- **Test**: Check Vercel dashboard → MAILGUN_DOMAIN missing ❌
- **Conclusion**: Env var missing in production
```

### 3.3 Identify Assumptions
**Every bug is a broken assumption.**

Ask yourself:
- [ ] What did the code ASSUME about the data?
  - "email field always exists"
  - "internal_note is always valid JSON"
  - "Mailgun API never fails"

- [ ] Which assumption is FALSE?
  - Test each one systematically

**Example:**
```typescript
// ASSUMPTION: client.email is always a valid string
await mailgun.send(client.email, template);
          // ↑ BREAKS if client.email = NULL

// FIX: Validate assumption
if (!client.email) {
  throw new Error(`Client ${client.id} has no email address`);
}
await mailgun.send(client.email, template);
```

---

## Phase 4: FIX WITH PRECISION (10 minutes)

### 4.1 Choose the Right Fix
**Not all fixes are equal.**

| Fix Type | When to Use | Example |
|----------|-------------|---------|
| **Guard Clause** | Missing data validation | `if (!email) throw new Error(...)` |
| **Default Value** | Harmless to substitute | `const mode = process.env.EMAIL_MODE \|\| 'sandbox'` |
| **Null Check** | Optional field | `client.email ?? 'noreply@example.com'` |
| **Schema Change** | Database constraint missing | `ALTER TABLE clients ADD CONSTRAINT email_not_null` |
| **Refactor** | Architectural problem | Move logic from UI to API route |

### 4.2 Implement the Minimal Fix
**Fix the ROOT CAUSE, not the symptom.**

```typescript
// ❌ BAD: Fixing symptom
await mailgun.send(client.email || 'default@example.com', template);
// Problem: Hides the real issue (missing client email)

// ✅ GOOD: Fixing root cause
if (!client.email) {
  console.error(`[sendEmail] Client ${client.id} has no email`);
  toast.error('Klient nie ma adresu email');
  return { success: false, error: 'NO_EMAIL' };
}
await mailgun.send(client.email, template);
```

### 4.3 Add Defensive Checks
**Prevent the bug from happening again.**

- [ ] Add TypeScript type guards
- [ ] Add runtime validation (Zod schema)
- [ ] Add database constraints (NOT NULL, CHECK)
- [ ] Add error boundaries (try/catch)
- [ ] Add user-facing error messages

**Example:**
```typescript
// Type safety
interface Client {
  id: number;
  email: string; // NOT string | null
}

// Runtime validation
const ClientSchema = z.object({
  id: z.number(),
  email: z.string().email(),
});

// Database constraint
ALTER TABLE clients
ADD CONSTRAINT email_required
CHECK (email IS NOT NULL AND email != '');
```

---

## Phase 5: TEST THE FIX (10 minutes)

### 5.1 Test the Original Bug
- [ ] Reproduce the EXACT steps that caused the bug
- [ ] Verify the bug is GONE (not just hidden)
- [ ] Check the error message / user feedback is clear

### 5.2 Test Edge Cases
- [ ] What if input is NULL?
- [ ] What if input is empty string `""`?
- [ ] What if input is invalid (e.g., `"not-an-email"`)?
- [ ] What if API is down?
- [ ] What if database query returns 0 rows?
- [ ] What if user clicks button 10 times rapidly?

### 5.3 Test Related Features
**Did the fix break anything else?**

- [ ] Test other features that use the same code
- [ ] Test other features that use the same data
- [ ] Check for UI regressions (layout, styling)
- [ ] Check for performance regressions (slow queries)

**Template:**
```markdown
## Test Results
### Original Bug: ✅ FIXED
- E1 email now goes to client email (not sandbox)

### Edge Cases:
- [x] Client with NULL email → Shows error toast ✅
- [x] Client with empty email → Shows error toast ✅
- [x] Client with invalid email → Mailgun rejects, shows error ✅

### Related Features:
- [x] E2 emails → Still work ✅
- [x] E3 emails → Still work ✅
- [x] SMS sending → Unaffected ✅
```

---

## Phase 6: DOCUMENT & PREVENT (5 minutes)

### 6.1 Write a Clear Commit Message
**Future you will thank you.**

```bash
git commit -m "fix: Validate client email before sending E1 reminder

PROBLEM:
- E1 emails were crashing when client.email was NULL
- No user feedback, silent failure

ROOT CAUSE:
- Code assumed client.email always exists
- No validation in sendEmail() function

FIX:
- Add email validation before Mailgun API call
- Show toast.error() if email missing
- Log error to console for debugging

TESTING:
- Tested with NULL email → shows error ✅
- Tested with valid email → sends successfully ✅
- Verified E2/E3 still work ✅

🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 6.2 Update Documentation
- [ ] Add to `LESSONS_LEARNED.md`
- [ ] Update `README.md` if relevant
- [ ] Add code comments explaining the fix
- [ ] Update TypeScript types if needed

**Example:**
```markdown
## Lesson Learned: Always Validate Email Before Sending

**Date**: 2025-10-10
**Bug**: E1 emails crashed for clients without email addresses
**Root Cause**: Missing validation, assumed email field always populated
**Fix**: Added guard clause with user-facing error message
**Prevention**:
- Added `email_required` database constraint
- Added Zod validation schema
- Added TypeScript type guard

**Code Pattern to Use:**
```typescript
if (!client.email) {
  console.error(`[Action] Client ${client.id} missing email`);
  toast.error('Klient nie ma adresu email');
  return { success: false, error: 'NO_EMAIL' };
}
```
```

### 6.3 Add Monitoring/Logging
**Catch the bug BEFORE users report it.**

- [ ] Add error tracking (Sentry, LogRocket)
- [ ] Add metrics (count of failed emails)
- [ ] Add alerts (notify if >10 failures/hour)
- [ ] Add dashboard (visualize email delivery rate)

---

## DEBUGGING CHECKLIST

Use this for every bug:

```markdown
## Bug: [SHORT DESCRIPTION]

### Phase 1: STOP & DEFINE ✅
- [x] Exact symptom documented
- [x] Expected vs Actual behavior written
- [x] Reproduction steps confirmed
- [x] Environment identified (local/staging/prod)

### Phase 2: GATHER EVIDENCE ✅
- [x] All error messages collected
- [x] Data flow traced end-to-end
- [x] Environment variables verified
- [x] Database state checked

### Phase 3: ISOLATE ROOT CAUSE ✅
- [x] Narrowed down to specific file
- [x] Narrowed down to specific function
- [x] Narrowed down to specific line
- [x] Tested hypothesis
- [x] Identified broken assumption

### Phase 4: FIX WITH PRECISION ✅
- [x] Chose appropriate fix strategy
- [x] Implemented minimal fix
- [x] Added defensive checks
- [x] Code reviewed

### Phase 5: TEST THE FIX ✅
- [x] Original bug is gone
- [x] Edge cases tested
- [x] Related features tested
- [x] No regressions

### Phase 6: DOCUMENT & PREVENT ✅
- [x] Clear commit message written
- [x] Documentation updated
- [x] Lesson learned recorded
- [x] Monitoring added
```

---

## RED FLAGS 🚩

**STOP immediately if you find yourself:**

1. **"I'll just try this and see if it works"**
   → NO. Form hypothesis first, then test.

2. **"This is a quick fix, I don't need to test edge cases"**
   → NO. Quick fixes create slow bugs.

3. **"I'm not sure why this works, but it does"**
   → NO. Understand the WHY before merging.

4. **"Let me add a try/catch to hide the error"**
   → NO. Fix the error, don't hide it.

5. **"I'll debug this by adding random console.logs everywhere"**
   → NO. Use systematic binary search.

6. **"The bug only happens sometimes, so it's probably not important"**
   → NO. Intermittent bugs are the most dangerous.

7. **"I changed 10 things at once, one of them should fix it"**
   → NO. Change ONE thing at a time.

8. **"I'll skip testing because the fix is obvious"**
   → NO. Test EVERY fix, no exceptions.

---

## COMMUNICATION PROTOCOL

When debugging with others (user, team, Claude):

### Report Format
```markdown
## Debug Status: [IN PROGRESS / BLOCKED / SOLVED]

**Time Spent**: 25 minutes
**Current Phase**: Isolating root cause

**What I've Tried**:
1. Checked environment variables → All correct ✅
2. Checked database → Invoice exists ✅
3. Checked Mailgun logs → API key invalid ❌

**Current Hypothesis**:
Mailgun API key in Vercel doesn't match .env.local

**Next Step**:
Verify API key in Vercel dashboard

**Blockers**:
Need access to Vercel dashboard (user has credentials)

**ETA**:
10 minutes (if API key is the issue)
```

### Ask for Help When:
- Stuck for >30 minutes
- Need external access (Vercel, Supabase dashboard)
- Need domain knowledge (business rules)
- Found a security issue
- Need to modify production database

---

## METRICS FOR SUCCESS

A bug is TRULY fixed when:

1. ✅ You can explain the root cause in 2 sentences
2. ✅ You can reproduce it 100% of the time (before fix)
3. ✅ You CANNOT reproduce it anymore (after fix)
4. ✅ You tested ≥5 edge cases
5. ✅ You added prevention (validation/types/constraints)
6. ✅ You documented the lesson learned
7. ✅ You committed with a clear message
8. ✅ Another developer could understand your fix in 5 minutes

---

## FINAL RULE

> **"If you can't explain it simply, you don't understand it well enough."**
> — Albert Einstein

Before you mark a bug as "fixed", explain it to a rubber duck (or the user). If you can't explain:
- WHY it happened
- HOW you fixed it
- WHAT prevents it from happening again

...then you're not done debugging yet. 🦆

---

**Now go debug like a professional. 🔍**
