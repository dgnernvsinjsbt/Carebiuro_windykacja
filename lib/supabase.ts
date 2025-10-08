import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { Client, Invoice, InvoiceComment } from '@/types';

// Lazy initialization - only validate and create clients when actually used
let _supabase: SupabaseClient | null = null;
let _supabaseAdmin: SupabaseClient | null = null;

function getSupabaseUrl(): string {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  if (!url) {
    throw new Error('Missing NEXT_PUBLIC_SUPABASE_URL environment variable');
  }
  return url;
}

function getSupabaseAnonKey(): string {
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!key) {
    throw new Error('Missing NEXT_PUBLIC_SUPABASE_ANON_KEY environment variable');
  }
  return key;
}

function getSupabaseServiceKey(): string {
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!key) {
    throw new Error('Missing SUPABASE_SERVICE_ROLE_KEY environment variable');
  }
  return key;
}

// Getter functions for lazy initialization
function getSupabase(): SupabaseClient {
  if (!_supabase) {
    _supabase = createClient(getSupabaseUrl(), getSupabaseAnonKey());
  }
  return _supabase;
}

function getSupabaseAdmin(): SupabaseClient {
  if (!_supabaseAdmin) {
    _supabaseAdmin = createClient(getSupabaseUrl(), getSupabaseServiceKey());
  }
  return _supabaseAdmin;
}

// Export getter functions directly - callers must invoke them
// This ensures lazy initialization while preserving Supabase query builder functionality
export const supabase = getSupabase;
export const supabaseAdmin = getSupabaseAdmin;

/**
 * Database operations for Clients table
 */
export const clientsDb = {
  /**
   * Get all clients with unpaid invoices
   */
  async getAll() {
    const { data, error } = await getSupabase()
      .from('clients')
      .select('*')
      .order('updated_at', { ascending: false });

    if (error) throw error;
    return data as Client[];
  },

  /**
   * Get client by ID
   */
  async getById(id: number) {
    const { data, error } = await getSupabase()
      .from('clients')
      .select('*')
      .eq('id', id)
      .single();

    if (error) throw error;
    return data as Client;
  },

  /**
   * Get client by Fakturownia ID
   */
  async getByFakturowniaId(fakturowniaId: number) {
    const { data, error } = await getSupabase()
      .from('clients')
      .select('*')
      .eq('fakturownia_id', fakturowniaId)
      .single();

    if (error) throw error;
    return data as Client;
  },

  /**
   * Create new client
   */
  async create(client: Partial<Client>) {
    const { data, error } = await getSupabaseAdmin()
      .from('clients')
      .insert(client)
      .select()
      .single();

    if (error) throw error;
    return data as Client;
  },

  /**
   * Update client
   */
  async update(id: number, updates: Partial<Client>) {
    const { data, error } = await getSupabaseAdmin()
      .from('clients')
      .update({ ...updates, updated_at: new Date().toISOString() })
      .eq('id', id)
      .select()
      .single();

    if (error) throw error;
    return data as Client;
  },

  /**
   * Delete client
   */
  async delete(id: number) {
    const { error } = await getSupabaseAdmin()
      .from('clients')
      .delete()
      .eq('id', id);

    if (error) throw error;
  },

  /**
   * Get clients with unpaid invoices
   */
  async getClientsWithUnpaidInvoices() {
    const { data, error } = await getSupabase()
      .from('clients')
      .select(`
        *,
        invoices!inner(*)
      `)
      .eq('invoices.status', 'unpaid')
      .order('updated_at', { ascending: false });

    if (error) throw error;
    return data as Client[];
  },

  /**
   * Update notes using admin client
   */
  async updateNotes(clientId: number, notes: string) {
    const { data, error } = await getSupabaseAdmin()
      .from('clients')
      .update({ notes, updated_at: new Date().toISOString() })
      .eq('id', clientId)
      .select()
      .single();

    if (error) throw error;
    return data as Client;
  },

  /**
   * Upsert client (insert or update)
   */
  async upsert(client: Partial<Client>) {
    const { data, error } = await getSupabaseAdmin()
      .from('clients')
      .upsert(client, {
        onConflict: 'id',
        ignoreDuplicates: false,
      })
      .select()
      .single();

    if (error) throw error;
    return data as Client;
  },

  /**
   * Delete all clients (dangerous - use with caution)
   */
  async deleteAll() {
    const { error } = await getSupabaseAdmin()
      .from('clients')
      .delete()
      .neq('id', 0); // Delete all where id != 0 (always true)

    if (error) throw error;
  },

  /**
   * Bulk upsert clients (insert or update)
   */
  async bulkUpsert(clients: Partial<Client>[]) {
    const { data, error } = await getSupabaseAdmin()
      .from('clients')
      .upsert(clients, {
        onConflict: 'id',
        ignoreDuplicates: false,
      })
      .select();

    if (error) throw error;
    return data as Client[];
  },
};

/**
 * Database operations for Invoices table
 */
export const invoicesDb = {
  /**
   * Get all invoices for a client
   */
  async getByClientId(clientId: number) {
    const { data, error } = await getSupabase()
      .from('invoices')
      .select('*')
      .eq('client_id', clientId)
      .order('issue_date', { ascending: false });

    if (error) throw error;
    return data as Invoice[];
  },

  /**
   * Get invoice by ID
   */
  async getById(id: number) {
    const { data, error } = await getSupabase()
      .from('invoices')
      .select('*')
      .eq('id', id)
      .single();

    if (error) throw error;
    return data as Invoice;
  },

  /**
   * Get invoice by Fakturownia ID
   */
  async getByFakturowniaId(fakturowniaId: number) {
    const { data, error } = await getSupabase()
      .from('invoices')
      .select('*')
      .eq('fakturownia_id', fakturowniaId)
      .single();

    if (error) throw error;
    return data as Invoice;
  },

  /**
   * Create new invoice
   */
  async create(invoice: Partial<Invoice>) {
    const { data, error } = await getSupabaseAdmin()
      .from('invoices')
      .insert(invoice)
      .select()
      .single();

    if (error) throw error;
    return data as Invoice;
  },

  /**
   * Update invoice
   */
  async update(id: number, updates: Partial<Invoice>) {
    const { data, error } = await getSupabaseAdmin()
      .from('invoices')
      .update({ ...updates, updated_at: new Date().toISOString() })
      .eq('id', id)
      .select()
      .single();

    if (error) throw error;
    return data as Invoice;
  },

  /**
   * Get unpaid invoices
   */
  async getUnpaid() {
    const { data, error } = await getSupabase()
      .from('invoices')
      .select('*, clients(*)')
      .eq('status', 'unpaid')
      .order('issue_date', { ascending: false });

    if (error) throw error;
    return data;
  },

  /**
   * Get invoices with payment_date set
   */
  async getPaid() {
    const { data, error } = await getSupabase()
      .from('invoices')
      .select('*, clients(*)')
      .not('payment_date', 'is', null)
      .order('payment_date', { ascending: false });

    if (error) throw error;
    return data;
  },

  /**
   * Get overdue invoices
   */
  async getOverdue() {
    const today = new Date().toISOString().split('T')[0];
    const { data, error} = await getSupabase()
      .from('invoices')
      .select('*, clients(*)')
      .eq('status', 'unpaid')
      .lt('sell_date', today)
      .order('sell_date', { ascending: true});

    if (error) throw error;
    return data;
  },

  /**
   * Update invoice internal_note
   */
  async updateComment(id: number, internal_note: string) {
    const { data, error } = await getSupabaseAdmin()
      .from('invoices')
      .update({ internal_note, updated_at: new Date().toISOString() })
      .eq('id', id)
      .select()
      .single();

    if (error) throw error;
    return data as Invoice;
  },

  /**
   * Bulk upsert invoices (insert or update)
   */
  async bulkUpsert(invoices: Partial<Invoice>[]) {
    const { data, error } = await getSupabaseAdmin()
      .from('invoices')
      .upsert(invoices, {
        onConflict: 'fakturownia_id',
        ignoreDuplicates: false,
      })
      .select();

    if (error) throw error;
    return data as Invoice[];
  },

  /**
   * Delete all invoices (dangerous - use with caution)
   */
  async deleteAll() {
    const { error } = await getSupabaseAdmin()
      .from('invoices')
      .delete()
      .neq('id', 0); // Delete all where id != 0 (always true)

    if (error) throw error;
  },
};

/**
 * Database operations for Invoice Comments
 */
export const commentsDb = {
  /**
   * Get all comments for an invoice
   */
  async getByInvoiceId(invoiceId: number) {
    const { data, error } = await getSupabase()
      .from('invoice_comments')
      .select('*')
      .eq('invoice_id', invoiceId)
      .order('created_at', { ascending: true });

    if (error) throw error;
    return data as InvoiceComment[];
  },

  /**
   * Create new comment
   */
  async create(comment: Partial<InvoiceComment>) {
    const { data, error } = await getSupabaseAdmin()
      .from('invoice_comments')
      .insert(comment)
      .select()
      .single();

    if (error) throw error;
    return data as InvoiceComment;
  },

  /**
   * Delete comment
   */
  async delete(id: number) {
    const { error } = await getSupabaseAdmin()
      .from('invoice_comments')
      .delete()
      .eq('id', id);

    if (error) throw error;
  },

  /**
   * Log an action related to invoice
   */
  async logAction(invoiceId: number, action: string, details?: string) {
    const { data, error } = await getSupabaseAdmin()
      .from('invoice_comments')
      .insert({
        invoice_id: invoiceId,
        body: `[${action.toUpperCase()}] ${details || ''}`,
        created_at: new Date().toISOString(),
      })
      .select()
      .single();

    if (error) throw error;
    return data as InvoiceComment;
  },
};

/**
 * Helper function to safely prepare invoice data for message history logging
 * Handles all nullable fields from Invoice type
 */
export function prepareMessageHistoryEntry(
  invoice: {
    id: number;
    client_id: number | null;
    number: string | null;
    buyer_name: string | null;
    total: number | null;
    currency: string | null;
  },
  messageType: 'email' | 'sms' | 'whatsapp',
  level: 1 | 2 | 3,
  options?: {
    status?: 'sent' | 'failed';
    error_message?: string;
    sent_by?: string;
    is_auto_initial?: boolean;
  }
) {
  if (!invoice.client_id) {
    throw new Error(`Cannot log message: invoice ${invoice.id} has no client_id`);
  }

  return {
    client_id: invoice.client_id,
    invoice_id: invoice.id,
    invoice_number: invoice.number || `INV-${invoice.id}`,
    client_name: invoice.buyer_name || 'Unknown Client',
    message_type: messageType,
    level,
    status: options?.status || 'sent',
    error_message: options?.error_message,
    sent_by: options?.sent_by || 'system',
    is_auto_initial: options?.is_auto_initial || false,
    invoice_total: invoice.total ?? 0,
    invoice_currency: invoice.currency || 'EUR',
  };
}

/**
 * Database operations for Message History
 */
export const messageHistoryDb = {
  /**
   * Get all message history for a client
   */
  async getByClientId(clientId: number) {
    const { data, error } = await getSupabase()
      .from('message_history')
      .select('*')
      .eq('client_id', clientId)
      .order('sent_at', { ascending: false });

    if (error) throw error;
    return data;
  },

  /**
   * Create new message history entry
   */
  async create(entry: any) {
    const { data, error } = await getSupabaseAdmin()
      .from('message_history')
      .insert(entry)
      .select()
      .single();

    if (error) throw error;
    return data;
  },

  /**
   * Get recent messages for a client
   */
  async getRecentByClientId(clientId: number, limit: number = 10) {
    const { data, error } = await getSupabase()
      .from('message_history')
      .select('*')
      .eq('client_id', clientId)
      .order('sent_at', { ascending: false })
      .limit(limit);

    if (error) throw error;
    return data;
  },

  /**
   * Get message history with filters
   */
  async getHistory(filters: {
    startDate?: string;
    endDate?: string;
    clientId?: number;
    messageType?: 'email' | 'sms' | 'whatsapp';
    limit?: number;
  }) {
    let query = getSupabase()
      .from('message_history')
      .select('*')
      .order('sent_at', { ascending: false });

    if (filters.startDate) {
      query = query.gte('sent_at', filters.startDate);
    }
    if (filters.endDate) {
      query = query.lte('sent_at', filters.endDate);
    }
    if (filters.clientId) {
      query = query.eq('client_id', filters.clientId);
    }
    if (filters.messageType) {
      query = query.eq('message_type', filters.messageType);
    }
    if (filters.limit) {
      query = query.limit(filters.limit);
    }

    const { data, error } = await query;

    if (error) throw error;
    return data || [];
  },

  /**
   * Get aggregate statistics for message history
   */
  async getStats(filters: {
    startDate?: string;
    endDate?: string;
  }) {
    const history = await this.getHistory(filters);

    const stats = {
      total: history.length,
      byType: {
        email: history.filter((m: any) => m.message_type === 'email').length,
        sms: history.filter((m: any) => m.message_type === 'sms').length,
        whatsapp: history.filter((m: any) => m.message_type === 'whatsapp').length,
      },
      byStatus: {
        sent: history.filter((m: any) => m.status === 'sent').length,
        failed: history.filter((m: any) => m.status === 'failed').length,
        pending: history.filter((m: any) => m.status === 'pending').length,
      },
    };

    return stats;
  },

  /**
   * Get daily statistics for the last N days
   */
  async getDailyStats(days: number = 30) {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);

    const history = await this.getHistory({
      startDate: startDate.toISOString(),
      endDate: endDate.toISOString(),
    });

    // Group by date
    const dailyMap: Record<string, any> = {};

    history.forEach((msg: any) => {
      const date = msg.sent_at?.split('T')[0] || 'unknown';
      if (!dailyMap[date]) {
        dailyMap[date] = {
          date,
          total: 0,
          email: 0,
          sms: 0,
          whatsapp: 0,
          sent: 0,
          failed: 0,
        };
      }

      dailyMap[date].total++;
      dailyMap[date][msg.message_type]++;
      dailyMap[date][msg.status]++;
    });

    return Object.values(dailyMap).sort((a: any, b: any) => a.date.localeCompare(b.date));
  },

  /**
   * Log a message sent to a client
   */
  async logMessage(entry: {
    client_id: number;
    invoice_id?: number;
    invoice_number: string;
    client_name: string;
    message_type: 'email' | 'sms' | 'whatsapp';
    level: 1 | 2 | 3;
    status: 'sent' | 'failed';
    error_message?: string;
    sent_by?: string;
    is_auto_initial?: boolean;
    invoice_total?: number | string;
    invoice_currency?: string;
  }) {
    const { data, error } = await getSupabaseAdmin()
      .from('message_history')
      .insert({
        ...entry,
        sent_at: new Date().toISOString(),
        sent_by: entry.sent_by || 'system',
        is_auto_initial: entry.is_auto_initial || false,
      })
      .select()
      .single();

    if (error) throw error;
    return data;
  },
};
