import { supabaseAdmin } from './supabase';

interface EmailData {
  client_name: string;
  invoice_number: string;
  amount: string;
  due_date: string;
}

/**
 * Zamienia {{placeholder}} na wartości z data
 */
function replacePlaceholders(template: string, data: EmailData): string {
  return template.replace(/\{\{(\w+)\}\}/g, (match, key) => {
    return (data as any)[key] || match;
  });
}

/**
 * Wysyła email przez Mailgun
 *
 * @param templateId - ID template'u ('EMAIL_1', 'EMAIL_2', 'EMAIL_3')
 * @param recipientEmail - Email odbiorcy
 * @param emailData - Dane do podstawienia w template
 * @returns { success: true, mailgunId } lub { success: false, error }
 */
export async function sendEmailReminder(
  templateId: 'EMAIL_1' | 'EMAIL_2' | 'EMAIL_3',
  recipientEmail: string,
  emailData: EmailData
): Promise<{ success: boolean; mailgunId?: string; error?: string }> {
  const isSandbox = process.env.EMAIL_MODE === 'sandbox';

  // W sandbox mode, wszystkie emaile idą na EMAIL_SANDBOX_RECIPIENT
  const actualRecipient = isSandbox
    ? process.env.EMAIL_SANDBOX_RECIPIENT!
    : recipientEmail;

  console.log(`[Mailgun] Sending ${templateId} to ${actualRecipient} (sandbox: ${isSandbox})`);

  try {
    // 1. Pobierz template z Supabase
    const { data: template, error: templateError } = await supabaseAdmin()
      .from('email_templates')
      .select('*')
      .eq('id', templateId)
      .single();

    if (templateError || !template) {
      throw new Error(`Template ${templateId} not found: ${templateError?.message}`);
    }

    console.log(`[Mailgun] Template loaded: ${template.name}`);

    // 2. Render template z danymi
    const subject = replacePlaceholders(template.subject, emailData);
    const bodyHtml = replacePlaceholders(template.body_html, emailData);
    const bodyText = replacePlaceholders(template.body_text, emailData);

    console.log(`[Mailgun] Rendered email:`, {
      subject,
      bodyTextLength: bodyText.length,
      bodyHtmlLength: bodyHtml.length,
    });

    // 3. Wyślij przez Mailgun API
    const formData = new FormData();
    formData.append('from', process.env.MAILGUN_FROM_EMAIL!);
    formData.append('to', actualRecipient);
    formData.append('subject', subject);
    formData.append('html', bodyHtml);
    formData.append('text', bodyText);

    const authHeader = `Basic ${Buffer.from(`api:${process.env.MAILGUN_API_KEY}`).toString('base64')}`;

    const response = await fetch(
      `${process.env.MAILGUN_BASE_URL}/${process.env.MAILGUN_DOMAIN}/messages`,
      {
        method: 'POST',
        headers: {
          Authorization: authHeader,
        },
        body: formData,
      }
    );

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.message || `Mailgun API error: ${response.status}`);
    }

    console.log(`[Mailgun] ✅ Email sent successfully: ${result.id}`);
    return { success: true, mailgunId: result.id };

  } catch (error: any) {
    console.error(`[Mailgun] ❌ Failed to send email:`, error);
    return { success: false, error: error.message };
  }
}
