import { supabaseAdmin } from './supabase';

interface SmsData {
  nazwa_klienta: string;
  numer_faktury: string;
  kwota: string;
  waluta: string;
  termin: string;
}

/**
 * Zamienia {{placeholder}} na wartości z data
 */
function replacePlaceholders(template: string, data: SmsData): string {
  return template.replace(/\{\{(\w+)\}\}/g, (match, key) => {
    return (data as any)[key] || match;
  });
}

/**
 * Wysyła SMS przez SMS Planet API
 *
 * @param templateKey - Klucz szablonu ('SMS_1', 'SMS_2', 'SMS_3')
 * @param recipientPhone - Numer telefonu odbiorcy
 * @param smsData - Dane do podstawienia w szablonie
 * @returns { success: true, messageId } lub { success: false, error }
 */
export async function sendSmsReminder(
  templateKey: 'SMS_1' | 'SMS_2' | 'SMS_3',
  recipientPhone: string,
  smsData: SmsData
): Promise<{ success: boolean; messageId?: string; error?: string }> {
  console.log(`[SMS] Sending ${templateKey} to ${recipientPhone}`);

  try {
    // 1. Pobierz szablon z Supabase (najnowszy jeśli jest kilka)
    const { data: templates, error: templateError } = await supabaseAdmin()
      .from('message_templates')
      .select('*')
      .eq('template_key', templateKey)
      .eq('channel', 'sms')
      .eq('is_active', true)
      .order('created_at', { ascending: false })
      .limit(1);

    if (templateError || !templates || templates.length === 0) {
      throw new Error(`Template ${templateKey} not found: ${templateError?.message || 'No templates returned'}`);
    }

    const template = templates[0];

    console.log(`[SMS] Template loaded: ${template.name}`);

    // 2. Render template z danymi (używamy body_text dla SMS)
    const messageText = replacePlaceholders(template.body_text || '', smsData);

    console.log(`[SMS] Rendered message:`, {
      templateKey,
      messageLength: messageText.length,
      messagePreview: messageText.substring(0, 50) + '...',
    });

    // 3. Wyślij przez SMS Planet API
    const smsApiToken = process.env.SMSPLANET_API_TOKEN;
    const smsFrom = process.env.SMSPLANET_FROM || 'Cbb-Office';

    if (!smsApiToken) {
      throw new Error('SMSPLANET_API_TOKEN not configured');
    }

    const formData = new URLSearchParams();
    formData.append('from', smsFrom);
    formData.append('to', recipientPhone);
    formData.append('msg', messageText);

    console.log(`[SMS] Calling SMS Planet API...`);
    const response = await fetch('https://api2.smsplanet.pl/sms', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': `Bearer ${smsApiToken}`,
      },
      body: formData.toString(),
    });

    const result = await response.text();

    console.log(`[SMS] API response:`, {
      status: response.status,
      ok: response.ok,
      body: result,
    });

    if (!response.ok) {
      console.error(`[SMS] ❌ SMS Planet API returned error: ${result}`);
      throw new Error(`SMS API error: ${response.status} ${result}`);
    }

    console.log(`[SMS] ✅ SMS sent successfully`);
    return { success: true, messageId: result };

  } catch (error: any) {
    console.error(`[SMS] ❌ Failed to send SMS:`, error);
    return { success: false, error: error.message };
  }
}
