// Database types (Supabase) - Maps 1:1 with Fakturownia Client fields + our custom fields
export interface Client {
  // Fakturownia fields (exact mapping)
  id: number;
  name: string | null;
  first_name: string | null;
  last_name: string | null;
  tax_no: string | null;
  post_code: string | null;
  city: string | null;
  street: string | null;
  street_no: string | null;
  country: string | null;
  email: string | null;
  phone: string | null;
  mobile_phone: string | null;
  www: string | null;
  fax: string | null;
  note: string | null; // Komentarz z Fakturowni zawierający [WINDYKACJA]
  bank: string | null;
  bank_account: string | null;
  shortcut: string | null;
  kind: string | null;
  token: string | null;
  discount: number | null;
  payment_to_kind: string | null;
  category_id: number | null;
  use_delivery_address: boolean | null;
  delivery_address: string | null;
  person: string | null;
  use_mass_payment: boolean | null;
  mass_payment_code: string | null;
  external_id: string | null;
  company: boolean | null;
  title: string | null;
  register_number: string | null;
  tax_no_check: string | null;
  disable_auto_reminders: boolean | null;
  created_at: string | null;
  updated_at: string | null;

  // Our custom fields
  total_unpaid: number | null; // Calculated from unpaid invoices
  list_polecony: boolean | null; // Flaga oznaczająca klienta kwalifikującego się do listu poleconego

  // UI dynamic fields (not in database)
  invoice_count?: number;
  total_debt?: number;
  qualifies_for_list_polecony?: boolean;
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

  // List polecony metadata (parsed from client.note)
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
  first_name: string;
  last_name: string;
  tax_no: string;
  post_code: string;
  city: string;
  street: string;
  street_no: string | null;
  country: string;
  email: string;
  phone: string;
  mobile_phone: string;
  www: string | null;
  fax: string | null;
  note: string; // Komentarz klienta - używamy do [WINDYKACJA]
  bank: string | null;
  bank_account: string | null;
  shortcut: string;
  kind: string;
  token: string;
  discount: number | null;
  payment_to_kind: string | null;
  category_id: number | null;
  use_delivery_address: boolean;
  delivery_address: string;
  person: string | null;
  use_mass_payment: boolean;
  mass_payment_code: string | null;
  external_id: string | null;
  company: boolean;
  title: string | null;
  register_number: string | null;
  tax_no_check: string;
  disable_auto_reminders: boolean;
  created_at: string;
  updated_at: string;
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
