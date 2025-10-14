// Template types for unified message system

export type TemplateChannel = 'email' | 'sms' | 'whatsapp' | 'letter';

export type TemplateKey =
  | 'REMINDER_1'
  | 'REMINDER_2'
  | 'REMINDER_3'
  | 'FORMAL_NOTICE'
  | 'EMAIL_1' // Legacy email templates
  | 'EMAIL_2'
  | 'EMAIL_3';

export interface TemplatePlaceholder {
  key: string;
  description: string;
}

export interface MessageTemplate {
  id: string;
  channel: TemplateChannel;
  template_key: TemplateKey;
  name: string;
  description?: string;
  is_active: boolean;

  // Email-specific
  subject?: string;
  body_html?: string;

  // SMS/WhatsApp
  body_text?: string;

  // Letter-specific
  body_top?: string;
  body_bottom?: string;

  // Shared
  placeholders: TemplatePlaceholder[];
  created_at: string;
  updated_at: string;
  created_by?: string;
}

export interface MessageTemplateVersion {
  id: string;
  template_id: string;
  version_number: number;
  subject?: string;
  body_html?: string;
  body_text?: string;
  body_top?: string;
  body_bottom?: string;
  placeholders?: TemplatePlaceholder[];
  changed_by?: string;
  changed_at: string;
  change_note?: string;
}

// Data types for template rendering
export interface TemplateData {
  nazwa_klienta?: string;
  numer_faktury?: string;
  kwota?: string;
  termin?: string;
  waluta?: string;
  suma_zadluzenia?: string;
  [key: string]: string | undefined;
}

// Formatted message types
export interface FormattedEmail {
  subject: string;
  html: string;
  text: string;
}

export interface FormattedSMS {
  text: string;
  length: number;
  segments: number;
  encoding: 'GSM-7' | 'UCS-2';
  isValid: boolean;
  warnings: string[];
}

export interface FormattedWhatsApp {
  text: string;
  length: number;
}

export interface FormattedLetter {
  body_top: string;
  body_bottom: string;
  // Table data will be added dynamically
}

export type FormattedMessage =
  | FormattedEmail
  | FormattedSMS
  | FormattedWhatsApp
  | FormattedLetter;

// API response types
export interface TemplateUpdateRequest {
  template_id: string;
  subject?: string;
  body_text?: string;
  body_html?: string;
  body_top?: string;
  body_bottom?: string;
  changed_by?: string;
  change_note?: string;
}

export interface TemplateUpdateResponse {
  success: boolean;
  template?: MessageTemplate;
  error?: string;
}
