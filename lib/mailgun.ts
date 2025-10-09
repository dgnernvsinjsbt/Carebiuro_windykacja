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
 * Pobiera PDF faktury z Fakturowni
 */
async function downloadInvoicePdf(invoiceId: number): Promise<Buffer | null> {
  try {
    const token = process.env.FAKTUROWNIA_API_TOKEN;
    const accountName = process.env.FAKTUROWNIA_ACCOUNT;

    if (!token || !accountName) {
      console.error('[Mailgun] Missing Fakturownia credentials');
      return null;
    }

    const url = `https://${accountName}.fakturownia.pl/invoices/${invoiceId}.pdf?api_token=${token}`;

    console.log(`[Mailgun] Downloading PDF for invoice ${invoiceId}`);

    const response = await fetch(url);

    if (!response.ok) {
      console.error(`[Mailgun] Failed to download PDF: ${response.status}`);
      return null;
    }

    const arrayBuffer = await response.arrayBuffer();
    return Buffer.from(arrayBuffer);
  } catch (error: any) {
    console.error(`[Mailgun] Error downloading PDF:`, error);
    return null;
  }
}

/**
 * Wysyła email przez Mailgun
 *
 * @param templateId - ID template'u ('EMAIL_1', 'EMAIL_2', 'EMAIL_3')
 * @param recipientEmail - Email odbiorcy
 * @param emailData - Dane do podstawienia w template
 * @param invoiceId - ID faktury (opcjonalnie, do załączenia PDF)
 * @returns { success: true, mailgunId } lub { success: false, error }
 */
export async function sendEmailReminder(
  templateId: 'EMAIL_1' | 'EMAIL_2' | 'EMAIL_3',
  recipientEmail: string,
  emailData: EmailData,
  invoiceId?: number
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

    // 3. Pobierz PDF faktury (jeśli podano invoiceId)
    let pdfBuffer: Buffer | null = null;
    console.log(`[Mailgun] Invoice ID provided: ${invoiceId || 'NONE'}`);
    if (invoiceId) {
      console.log(`[Mailgun] Starting PDF download for invoice ${invoiceId}`);
      pdfBuffer = await downloadInvoicePdf(invoiceId);
      if (pdfBuffer) {
        console.log(`[Mailgun] ✅ PDF downloaded successfully (${pdfBuffer.length} bytes)`);
      } else {
        console.error(`[Mailgun] ❌ PDF download FAILED - downloadInvoicePdf returned null`);
      }
    } else {
      console.warn(`[Mailgun] ⚠️ No invoiceId provided - skipping PDF attachment`);
    }

    // 4. Wyślij przez Mailgun API
    const formData = new FormData();
    formData.append('from', process.env.MAILGUN_FROM_EMAIL!);
    formData.append('to', actualRecipient);
    formData.append('subject', subject);
    formData.append('html', bodyHtml);
    formData.append('text', bodyText);

    // Załącz PDF jeśli dostępny
    if (pdfBuffer) {
      try {
        // Konwertuj Buffer na File przez Uint8Array (type-safe dla Web API)
        const uint8Array = new Uint8Array(pdfBuffer);
        console.log(`[Mailgun] Converted Buffer to Uint8Array (${uint8Array.length} bytes)`);

        const filename = `faktura_${emailData.invoice_number}.pdf`;
        const pdfFile = new File([uint8Array], filename, {
          type: 'application/pdf'
        });
        console.log(`[Mailgun] Created File object: ${filename} (${pdfFile.size} bytes, type: ${pdfFile.type})`);

        formData.append('attachment', pdfFile);
        console.log(`[Mailgun] ✅ PDF attached to FormData: ${filename}`);
      } catch (error: any) {
        console.error(`[Mailgun] ❌ Error attaching PDF:`, error);
      }
    } else {
      console.log(`[Mailgun] No PDF buffer available - skipping attachment`);
    }

    const authHeader = `Basic ${Buffer.from(`api:${process.env.MAILGUN_API_KEY}`).toString('base64')}`;

    console.log(`[Mailgun] Sending request to Mailgun API...`);
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

    console.log(`[Mailgun] Response status: ${response.status} ${response.statusText}`);
    const result = await response.json();
    console.log(`[Mailgun] Response body:`, JSON.stringify(result, null, 2));

    if (!response.ok) {
      console.error(`[Mailgun] ❌ API returned error: ${result.message}`);
      throw new Error(result.message || `Mailgun API error: ${response.status}`);
    }

    console.log(`[Mailgun] ✅ Email sent successfully: ${result.id}`);
    return { success: true, mailgunId: result.id };

  } catch (error: any) {
    console.error(`[Mailgun] ❌ Failed to send email:`, error);
    return { success: false, error: error.message };
  }
}
