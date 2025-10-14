# 🧩 Claude Debug Protocol — Senior Developer Mode

Please help me debug this issue using a structured, analytical approach.

---

## 🔧 Step 0. Debug Environment Setup

Before diving into the problem, ensure proper debugging infrastructure:

**Verify debugging tools:**
- Source maps enabled (`sourceMap: true` in tsconfig/build config)
- Browser DevTools or Node debugger available
- Logging framework configured (console, Winston, Pino, etc.)
- Error tracking enabled (Sentry, LogRocket, etc.)

**Prepare debugging strategy:**
- Identify logging points for data flow inspection
- Set up breakpoints in suspected areas
- Enable verbose/debug mode if available
- Check relevant environment variables

**If using MCP Context7:**
- Query for known issues with current library versions
- Check for reported bugs in dependencies
- Verify compatibility matrix

---

## 🔍 Step 1. Understand the Context

- Read all **relevant source files** and understand how the code is supposed to work
- Identify **entry points**, **data flow**, and **dependencies**
- If there are recent commits or edits, focus on changes related to the problem
- Review related tests to understand expected behavior
- Check documentation and comments for intended functionality

---

## ⚠️ Step 2. Analyze the Problem

- Review **error messages, stack traces, and console output** for clues
- Identify **where** the failure occurs (file, line, function, or component)
- Check for:
  - Type mismatches or `undefined/null` references  
  - Race conditions or async/await issues  
  - Incorrect state or variable scope  
  - Broken imports or missing dependencies  
  - Edge cases not covered by logic
  - Memory leaks or resource exhaustion
  - Security vulnerabilities (XSS, injection, auth bypass)

---

## 🧮 Step 3. Form a Hypothesis

- Clearly state the **root cause** you suspect (e.g., "state mutation inside render", "API returning null", etc.)
- Validate by reasoning through control flow or inspecting example data
- Consider multiple potential causes and rank by likelihood
- Use debugging tools to confirm or disprove hypothesis

---

## 🧰 Step 4. Propose a Fix

- Suggest the **minimal, safe change** that resolves the issue
- Provide **exact code edits** (before → after) or a code diff
- If multiple solutions exist, rank them by:
  - Clarity and readability
  - Maintainability and future-proofing
  - Side-effect and regression risk
  - Performance impact
  - Security implications
- Highlight any trade-offs in the proposed solution

---

## 🧪 Step 5. Verify and Test

- Explain **how to test** the fix (e.g., run a specific route, test a component, call an endpoint)
- Suggest any **unit or integration tests** that should be added to prevent regressions
- Consider **edge and failure cases** to confirm stability:
  - Null/undefined inputs
  - Empty arrays or objects
  - Network failures or timeouts
  - Concurrent access or race conditions
  - Boundary values and limits
- Validate that the fix doesn't introduce new vulnerabilities

---

## 📋 Step 6. Document and Prevent

**Immediate documentation:**
- Update relevant code comments if the fix clarifies behavior
- Add JSDoc/TSDoc for complex functions if missing
- Update `CHANGELOG.md` with bug fix entry
- Create or update issue in tracker with:
  - Root cause analysis
  - Fix description
  - Steps to reproduce (original bug)
  - Test cases added

**Prevention measures:**
- Add linting rules to catch similar issues (ESLint, TypeScript strict mode)
- Suggest better error handling patterns
- Recommend additional type safety or validation
- Identify monitoring/alerting improvements
- Update testing strategy to catch this class of bugs

**Escalation path:**
- If this bug reveals **architectural issues** (tight coupling, poor separation of concerns, scalability problems), note: "Consider running /Architect Mode for deeper analysis"
- If multiple similar bugs exist, suggest refactoring session
- Document technical debt for future resolution

---

## 🧩 Additional Guidelines

- Use **precise reasoning** — reference file names, functions, and variables explicitly
- Prefer **surgical changes** over refactors unless necessary
- If the issue reveals a **deeper design flaw**, document it and suggest a follow-up improvement
- Always write explanations that another senior engineer could audit easily
- Consider backwards compatibility and deployment impact
- Think about rollback strategy if the fix causes issues

---

## 🔄 Integration with Other Modes

**When to escalate to /Architect Mode:**
- Bug indicates systemic architectural problems
- Multiple related bugs suggest design issues
- Fix requires significant refactoring
- Performance issues span multiple modules
- Security vulnerabilities require infrastructure changes

**When to use Debug Mode:**
- Specific, localized issues
- Clear error messages or stack traces
- Regression from recent changes
- Performance bottlenecks in specific functions
- Integration issues between components

---

## ✅ Goal

Deliver a fix that not only resolves the immediate bug but improves the long-term reliability, readability, and maintainability of the code. Document learnings to prevent similar issues and know when to escalate to broader architectural review.