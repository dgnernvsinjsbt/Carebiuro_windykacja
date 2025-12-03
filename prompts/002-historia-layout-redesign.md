<objective>
Redesign the "Historia wysyłek" (message history) page layout to better utilize screen real estate and improve the display of sent email/SMS/WhatsApp information.

Current problems identified:
1. `max-w-7xl` container leaves significant empty space on wide screens (>1280px)
2. Message badges (E1, S1, W1 with time) are too compact - hard to see details
3. No expandable details for individual messages (recipient, subject, status)
4. Hierarchy (Date → Client → Invoice → Messages) creates deep nesting
</objective>

<context>
This is a Polish debt collection management system (windykacja). The /historia page shows a chronological log of all sent messages (email, SMS, WhatsApp) for invoice reminders.

Tech stack: Next.js 14, React 18, Tailwind CSS, Lucide icons

Current data structure per message:
- client_name, client_id
- invoice_number, invoice_total, invoice_currency
- message_type (email/sms/whatsapp)
- level (1-4 indicating reminder severity)
- status (sent/failed)
- error_message (if failed)
- sent_at (timestamp)
- sent_by (who triggered it)
- is_auto_initial (automated send indicator)

User personas: Accountants/bookkeepers who need to quickly see what was sent, when, to whom, and verify delivery status.
</context>

<research_phase>
Research modern design patterns for:

1. **Activity/audit log views** - How do tools like Stripe, Intercom, HubSpot display message history?
2. **Email client sent folders** - Gmail, Outlook patterns for showing sent message details
3. **CRM communication logs** - How Salesforce, Pipedrive show customer communication history
4. **Timeline vs Table layouts** - When to use each, hybrid approaches

Focus on patterns that:
- Maximize horizontal space usage on wide screens
- Allow quick scanning while supporting detail drill-down
- Handle high-density information without overwhelming users
- Work well with filtering/search
</research_phase>

<design_requirements>
1. **Full-width utilization**: Use available screen width (remove max-w-7xl constraint or use responsive max-width)

2. **Information density options**:
   - Compact view: For quick scanning (current-ish style)
   - Expanded view: Shows more details per message

3. **Better message details display**:
   - Visible: Type icon, level, time, status (sent/failed indicator)
   - On hover/expand: Full timestamp, sent_by, error message if failed
   - Consider: Subject line preview for emails (if available)

4. **Layout alternatives to consider**:
   - **Table layout**: Date | Client | Invoice | Type | Level | Status | Time
   - **Split view**: List on left, details on right (like email clients)
   - **Card grid**: Wider cards with more info per card
   - **Timeline + expandable rows**: Keep timeline but add expand/collapse

5. **Grouping flexibility**:
   - Current: By Date → Client → Invoice
   - Alternative: Just by Date with all messages flat
   - Consider: Tabs for different views

6. **Visual improvements**:
   - Clearer status indicators (sent vs failed)
   - Better type differentiation (email/SMS/WhatsApp)
   - Level severity indication (1-4 escalation)
</design_requirements>

<output_format>
Create a mockup as an HTML file with Tailwind CSS that can be opened directly in a browser.

Save to: `./mockups/historia-redesign.html`

The mockup should include:
1. **Header section**: Title, stats, filters (can be simplified)
2. **Main content area**: The redesigned message history view
3. **At least 2 layout variants**: e.g., Table view + Timeline view with toggle
4. **Sample data**: Use realistic Polish names and invoice numbers
5. **Interactive elements**: Hover states, expandable rows (CSS-only or minimal JS)
6. **Responsive considerations**: How it adapts from 1280px to 1920px+

Include inline Tailwind via CDN for easy viewing.
</output_format>

<sample_data>
Use this sample data in the mockup:

```
Date: 2025-12-03
- Client: PREMIUM FOODS SP. Z O.O.
  - Invoice: FV/2025/11/0847, 4,250.00 PLN
    - Email Level 1, sent 09:15, success
    - SMS Level 1, sent 09:16, success
  - Invoice: FV/2025/11/0912, 1,890.00 PLN
    - Email Level 2, sent 14:30, success

- Client: AUTO-CZĘŚCI KOWALSKI
  - Invoice: FV/2025/10/1234, 12,500.00 PLN
    - Email Level 3, sent 10:00, failed (invalid email)
    - WhatsApp Level 3, sent 10:05, success

Date: 2025-12-02
- Client: BIURO RACHUNKOWE NOWAK
  - Invoice: FV/2025/11/0756, 890.00 PLN
    - Email Level 1, sent 08:00, success
    - SMS Level 1, sent 08:01, success
```
</sample_data>

<success_criteria>
1. HTML mockup file created at ./mockups/historia-redesign.html
2. Mockup demonstrates at least 2 layout alternatives
3. Better screen space utilization visible (compare to current max-w-7xl)
4. Message details are more readable and accessible
5. Mockup includes brief annotations explaining design decisions
6. File opens correctly in browser with Tailwind styling applied
</success_criteria>

<verification>
Before completing:
1. Open the mockup file in browser to verify it renders correctly
2. Check that Tailwind CDN loads properly
3. Verify responsive behavior at different widths
4. Ensure sample data looks realistic
</verification>
