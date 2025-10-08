// Database types (Supabase)
export interface Client {
  id: number;
  name: string | null;
  first_name: string | null; // Imię klienta z Fakturowni
  last_name: string | null; // Nazwisko klienta z Fakturowni
  email: string | null;
  phone: string | null;
  total_unpaid: number | null;
  note: string | null; // Komentarz z Fakturowni zawierający [WINDYKACJA] i [LIST_POLECONY]
  list_polecony: boolean | null; // Flaga oznaczająca klienta kwalifikującego się do listu poleconego
  updated_at: string | null;
  invoice_count?: number; // Added dynamically in UI
  total_debt?: number; // Added dynamically for list polecony
  qualifies_for_list_polecony?: boolean; // Added dynamically for list polecony
}

export interface Invoice {
  id: number;
  client_id: number | null;
  number: string | null;
  total: number | null;
  status: string | null;
  internal_note: string | null; // Renamed from comment - maps to Fakturownia internal_note
  email_status: string | null;
  sent_time: string | null;
  updated_at: string | null;

  // Core invoice dates
  issue_date: string | null;
  sell_date: string | null;
  payment_to: string | null;
  paid_date: string | null;
  created_at: string | null;

  // Financial data
  price_net: number | null;
  price_tax: number | null;
  paid: number | null;
  currency: string | null;
  payment_type: string | null;

  // Buyer information
  buyer_name: string | null;
  buyer_email: string | null;
  buyer_phone: string | null;
  buyer_tax_no: string | null;
  buyer_street: string | null;
  buyer_city: string | null;
  buyer_post_code: string | null;
  buyer_country: string | null;

  // Document metadata
  kind: string | null;
  description: string | null;
  place: string | null;
  view_url: string | null;
  payment_url: string | null;

  // Status fields
  overdue: boolean | null;

  // Optimization flags
  has_third_reminder: boolean | null; // true if EMAIL_3/SMS_3/WHATSAPP_3 = true in [FISCAL_SYNC]
  list_polecony_sent_date: string | null; // Data wysłania listu poleconego (parsowane z [LIST_POLECONY_SENT])
  list_polecony_ignored_date: string | null; // Data ignorowania faktury (parsowane z [LIST_POLECONY_IGNORED])
}

export interface InvoiceComment {
  id: number;
  invoice_id: number;
  body: string;
  created_at: string;
  source: 'fakturownia' | 'local';
}

// Fakturownia API types
export interface FakturowniaInvoice {
  id: number;
  client_id: number;
  number: string;
  price_gross: string;
  price_net: string;
  price_tax: string;
  currency: string;
  status: string;
  paid: string;

  // Dates
  issue_date: string;
  sell_date: string;
  payment_to: string;
  paid_date: string | null;
  created_at: string;
  updated_at: string;

  // Payment
  payment_type: string;

  // Buyer information
  buyer_name: string;
  buyer_email: string;
  buyer_phone: string;
  buyer_tax_no: string;
  buyer_street: string;
  buyer_city: string;
  buyer_post_code: string;
  buyer_country: string;

  // Document metadata
  kind: string;
  description: string | null;
  place: string | null;
  view_url: string;
  payment_url: string | null;

  // Notes and status
  internal_note: string; // Notatka prywatna - niewidoczna na wydruku (używamy do [FISCAL_SYNC])
  email_status: string | null; // Status emaila: 'sent' jeśli faktura została wysłana mailem
  sent_time: string | null; // Data i czas wysłania emaila (jeśli email_status='sent')

  // Status fields (Fakturownia uses "overdue?" as key)
  'overdue?': boolean;
}

export interface FakturowniaClient {
  id: number;
  name: string;
  email: string;
  phone: string;
  tax_no: string;
  street: string;
  city: string;
  post_code: string;
  country: string;
  note: string; // Komentarz klienta - używamy do [WINDYKACJA]
}

// Fiscal Sync structure
export interface FiscalSyncData {
  EMAIL_1: boolean;
  EMAIL_1_DATE: string | null;
  EMAIL_2: boolean;
  EMAIL_2_DATE: string | null;
  EMAIL_3: boolean;
  EMAIL_3_DATE: string | null;
  SMS_1: boolean;
  SMS_1_DATE: string | null;
  SMS_2: boolean;
  SMS_2_DATE: string | null;
  SMS_3: boolean;
  SMS_3_DATE: string | null;
  WHATSAPP_1: boolean;
  WHATSAPP_1_DATE: string | null;
  WHATSAPP_2: boolean;
  WHATSAPP_2_DATE: string | null;
  WHATSAPP_3: boolean;
  WHATSAPP_3_DATE: string | null;
  STOP: boolean;
  WINDYKACJA: boolean; // Auto-reminders enabled (default: false)
  UPDATED: string;
}

// API response types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
}

export interface SyncResponse {
  synced_clients: number;
  synced_invoices: number;
  errors: string[];
}

export interface ReminderRequest {
  invoice_id: number;
  type: 'email' | 'sms' | 'whatsapp';
  level: 1 | 2 | 3;
}

// UI types
export interface InvoiceWithClient extends Invoice {
  client: Client | null;
  fiscal_sync: FiscalSyncData | null;
}
