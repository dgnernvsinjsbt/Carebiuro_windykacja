import { FiscalSyncData } from '@/types';

/**
 * Default Fiscal Sync structure with all flags set to false
 */
const DEFAULT_FISCAL_SYNC: FiscalSyncData = {
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

/**
 * Parse [FISCAL_SYNC] section from comment string
 *
 * @param comment - Full comment text from Fakturownia
 * @returns Parsed FiscalSyncData or null if not found
 */
export function parseFiscalSync(comment: string | null): FiscalSyncData | null {
  if (!comment) return null;

  const fiscalSyncRegex = /\[FISCAL_SYNC\]([\s\S]*?)\[\/FISCAL_SYNC\]/;
  const match = comment.match(fiscalSyncRegex);

  if (!match) return null;

  const content = match[1].trim();
  const lines = content.split('\n');
  const data: Partial<FiscalSyncData> = {};

  for (const line of lines) {
    const [key, value] = line.split('=').map(s => s.trim());
    if (!key || !value) continue;

    if (key === 'UPDATED') {
      data[key] = value;
    } else if (key === 'HASH') {
      // Parse hash field (8-char string or null)
      (data as any)[key] = value === 'NULL' ? null : value;
    } else if (key.endsWith('_DATE')) {
      // Parse date fields (null if 'NULL', otherwise the date string)
      (data as any)[key] = value === 'NULL' ? null : value;
    } else {
      // Parse boolean fields
      (data as any)[key] = value === 'TRUE';
    }
  }

  return {
    ...DEFAULT_FISCAL_SYNC,
    ...data,
  } as FiscalSyncData;
}

/**
 * Generate [FISCAL_SYNC] section as string
 *
 * @param data - FiscalSyncData object
 * @returns Formatted [FISCAL_SYNC] block
 */
export function generateFiscalSync(data: FiscalSyncData): string {
  const lines = [
    '[FISCAL_SYNC]',
    `HASH=${data.HASH || 'NULL'}`, // Hash first for easy visibility
    `EMAIL_1=${data.EMAIL_1 ? 'TRUE' : 'FALSE'}`,
    `EMAIL_1_DATE=${data.EMAIL_1_DATE || 'NULL'}`,
    `EMAIL_2=${data.EMAIL_2 ? 'TRUE' : 'FALSE'}`,
    `EMAIL_2_DATE=${data.EMAIL_2_DATE || 'NULL'}`,
    `EMAIL_3=${data.EMAIL_3 ? 'TRUE' : 'FALSE'}`,
    `EMAIL_3_DATE=${data.EMAIL_3_DATE || 'NULL'}`,
    `SMS_1=${data.SMS_1 ? 'TRUE' : 'FALSE'}`,
    `SMS_1_DATE=${data.SMS_1_DATE || 'NULL'}`,
    `SMS_2=${data.SMS_2 ? 'TRUE' : 'FALSE'}`,
    `SMS_2_DATE=${data.SMS_2_DATE || 'NULL'}`,
    `SMS_3=${data.SMS_3 ? 'TRUE' : 'FALSE'}`,
    `SMS_3_DATE=${data.SMS_3_DATE || 'NULL'}`,
    `WHATSAPP_1=${data.WHATSAPP_1 ? 'TRUE' : 'FALSE'}`,
    `WHATSAPP_1_DATE=${data.WHATSAPP_1_DATE || 'NULL'}`,
    `WHATSAPP_2=${data.WHATSAPP_2 ? 'TRUE' : 'FALSE'}`,
    `WHATSAPP_2_DATE=${data.WHATSAPP_2_DATE || 'NULL'}`,
    `WHATSAPP_3=${data.WHATSAPP_3 ? 'TRUE' : 'FALSE'}`,
    `WHATSAPP_3_DATE=${data.WHATSAPP_3_DATE || 'NULL'}`,
    `STOP=${data.STOP ? 'TRUE' : 'FALSE'}`,
    `WINDYKACJA=${data.WINDYKACJA ? 'TRUE' : 'FALSE'}`,
    `UPDATED=${data.UPDATED}`,
    '[/FISCAL_SYNC]',
  ];

  return lines.join('\n');
}

/**
 * Update a single field in existing comment
 *
 * @param comment - Current comment text
 * @param field - Field to update (e.g., 'EMAIL_1', 'STOP')
 * @param value - New boolean value
 * @param date - Optional date to set (for reminder fields)
 * @returns Updated comment with modified [FISCAL_SYNC] section
 */
export function updateFiscalSync(
  comment: string | null,
  field: keyof Omit<FiscalSyncData, 'UPDATED'>,
  value: boolean,
  date?: string
): string {
  // Parse existing or create new
  const existing = parseFiscalSync(comment);
  const fiscalData: FiscalSyncData = existing || { ...DEFAULT_FISCAL_SYNC };

  // Update field
  (fiscalData as any)[field] = value;

  // If date is provided and this is a reminder field, update the corresponding date field
  if (date && !field.endsWith('_DATE') && field !== 'STOP' && field !== 'WINDYKACJA') {
    const dateField = `${field}_DATE`;
    (fiscalData as any)[dateField] = date;
  }

  fiscalData.UPDATED = new Date().toISOString();

  // Generate new section
  const newSection = generateFiscalSync(fiscalData);

  // If comment had existing section, replace it
  if (comment && comment.includes('[FISCAL_SYNC]')) {
    return comment.replace(
      /\[FISCAL_SYNC\][\s\S]*?\[\/FISCAL_SYNC\]/,
      newSection
    );
  }

  // Otherwise, append to existing comment or create new
  const existingText = comment ? comment.trim() : '';
  return existingText ? `${existingText}\n\n${newSection}` : newSection;
}

/**
 * Initialize Fiscal Sync section in comment if it doesn't exist
 *
 * @param comment - Current comment text
 * @returns Comment with [FISCAL_SYNC] section
 */
export function ensureFiscalSync(comment: string | null): string {
  if (!comment || !comment.includes('[FISCAL_SYNC]')) {
    const fiscalSection = generateFiscalSync(DEFAULT_FISCAL_SYNC);
    return comment ? `${comment.trim()}\n\n${fiscalSection}` : fiscalSection;
  }
  return comment;
}

/**
 * Check if comment has valid Fiscal Sync structure
 */
export function hasFiscalSync(comment: string | null): boolean {
  if (!comment) return false;
  return /\[FISCAL_SYNC\][\s\S]*?\[\/FISCAL_SYNC\]/.test(comment);
}

/**
 * Initialize or update EMAIL_1 flag based on invoice email status
 * Used during sync to automatically mark invoices that were sent from Fakturownia
 *
 * @param comment - Current internal_note from invoice
 * @param emailStatus - email_status from Fakturownia ('sent', 'sent_error', or null)
 * @param sentTime - sent_time from Fakturownia (ISO date string)
 * @returns Updated comment with EMAIL_1 marked if email was sent or had error
 */
export function initializeFromEmailStatus(
  comment: string | null,
  emailStatus: string | null,
  sentTime: string | null
): string {
  // If email was sent from Fakturownia, mark EMAIL_1 as sent
  if (emailStatus === 'sent' && sentTime) {
    return updateFiscalSync(comment, 'EMAIL_1', true, sentTime);
  }

  // If email sending failed (sent_error), also mark EMAIL_1 but with error flag
  // This will allow UI to show red badge with "Email nie istnieje" message
  if (emailStatus === 'sent_error' && sentTime) {
    return updateFiscalSync(comment, 'EMAIL_1', true, sentTime);
  }

  // Otherwise, ensure fiscal sync structure exists
  return ensureFiscalSync(comment);
}
