import { createClient } from '@supabase/supabase-js';
import { Client, Invoice, InvoiceComment } from '@/types';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables');
}

// Client for browser (public operations)
export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// Client for server (admin operations)
export const supabaseAdmin = createClient(supabaseUrl, supabaseServiceKey);

/**
 * Database operations for Clients table
 */
export const clientsDb = {
  /**
   * Get all clients with unpaid invoices
   */
  async getAll() {
    const { data, error } = await supabase
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
    const { data, error } = await supabase
      .from('clients')
      .select('*')
      .eq('id', id)
      .single();

    if (error) throw error;
    return data as Client;
  },

  /**
   * Upsert client (insert or update)
   */
  async upsert(client: Client) {
    const { data, error } = await supabaseAdmin
      .from('clients')
      .upsert(client, { onConflict: 'id' })
      .select()
      .single();

    if (error) throw error;
    return data as Client;
  },

  /**
   * Bulk upsert clients
   */
  async bulkUpsert(clients: Client[]) {
    const { data, error } = await supabaseAdmin
      .from('clients')
      .upsert(clients, { onConflict: 'id' })
      .select();

    if (error) throw error;
    return data as Client[];
  },

  /**
   * Delete clients not in provided IDs (cleanup)
   */
  async deleteNotIn(ids: number[]) {
    const { error } = await supabaseAdmin
      .from('clients')
      .delete()
      .not('id', 'in', `(${ids.join(',')})`);

    if (error) throw error;
  },

  /**
   * Delete ALL clients (for full sync: clear → fetch → insert)
   */
  async deleteAll() {
    const { error } = await supabaseAdmin
      .from('clients')
      .delete()
      .neq('id', 0); // Delete all rows (id != 0 matches everything)

    if (error) throw error;
  },
};

/**
 * Database operations for Invoices table
 */
export const invoicesDb = {
  /**
   * Get all invoices with client data
   */
  async getAll() {
    const { data, error } = await supabase
      .from('invoices')
      .select('*, client:clients(*)')
      .order('updated_at', { ascending: false });

    if (error) throw error;
    return data;
  },

  /**
   * Get unpaid invoices
   */
  async getUnpaid() {
    const { data, error } = await supabase
      .from('invoices')
      .select('*, client:clients(*)')
      .in('status', ['issued', 'sent', 'not_paid'])
      .order('updated_at', { ascending: false });

    if (error) throw error;
    return data;
  },

  /**
   * Get invoice by ID
   */
  async getById(id: number) {
    const { data, error } = await supabase
      .from('invoices')
      .select('*, client:clients(*)')
      .eq('id', id)
      .single();

    if (error) throw error;
    return data;
  },

  /**
   * Get invoices by client ID
   */
  async getByClientId(clientId: number) {
    const { data, error } = await supabase
      .from('invoices')
      .select('*')
      .eq('client_id', clientId)
      .order('updated_at', { ascending: false });

    if (error) throw error;
    return data as Invoice[];
  },

  /**
   * Upsert invoice
   */
  async upsert(invoice: Invoice) {
    const { data, error } = await supabaseAdmin
      .from('invoices')
      .upsert(invoice, { onConflict: 'id' })
      .select()
      .single();

    if (error) throw error;
    return data as Invoice;
  },

  /**
   * Bulk upsert invoices
   */
  async bulkUpsert(invoices: Invoice[]) {
    const { data, error } = await supabaseAdmin
      .from('invoices')
      .upsert(invoices, { onConflict: 'id' })
      .select();

    if (error) throw error;
    return data as Invoice[];
  },

  /**
   * Update invoice comment
   */
  async updateComment(id: number, comment: string) {
    const { data, error } = await supabaseAdmin
      .from('invoices')
      .update({ comment, updated_at: new Date().toISOString() })
      .eq('id', id)
      .select()
      .single();

    if (error) throw error;
    return data as Invoice;
  },

  /**
   * Delete invoices not in provided IDs (cleanup)
   */
  async deleteNotIn(ids: number[]) {
    const { error } = await supabaseAdmin
      .from('invoices')
      .delete()
      .not('id', 'in', `(${ids.join(',')})`);

    if (error) throw error;
  },

  /**
   * Delete ALL invoices (for full sync: clear → fetch → insert)
   */
  async deleteAll() {
    const { error } = await supabaseAdmin
      .from('invoices')
      .delete()
      .neq('id', 0); // Delete all rows (id != 0 matches everything)

    if (error) throw error;
  },
};

/**
 * Database operations for Invoice Comments table
 */
export const commentsDb = {
  /**
   * Get comments for invoice
   */
  async getByInvoiceId(invoiceId: number) {
    const { data, error } = await supabase
      .from('invoice_comments')
      .select('*')
      .eq('invoice_id', invoiceId)
      .order('created_at', { ascending: false });

    if (error) throw error;
    return data as InvoiceComment[];
  },

  /**
   * Create new comment
   */
  async create(comment: Omit<InvoiceComment, 'id' | 'created_at'>) {
    const { data, error } = await supabaseAdmin
      .from('invoice_comments')
      .insert(comment)
      .select()
      .single();

    if (error) throw error;
    return data as InvoiceComment;
  },

  /**
   * Log action to invoice comments
   */
  async logAction(
    invoiceId: number,
    action: string,
    source: 'fakturownia' | 'local' = 'local'
  ) {
    return this.create({
      invoice_id: invoiceId,
      body: action,
      source,
    });
  },
};

/**
 * Database operations for Message History table
 */
export const messageHistoryDb = {
  /**
   * Log a sent message
   */
  async logMessage(data: {
    client_id: number;
    invoice_id: number;
    invoice_number: string;
    client_name: string;
    message_type: 'email' | 'sms' | 'whatsapp';
    level: 1 | 2 | 3;
    status: 'sent' | 'failed';
    error_message?: string;
    sent_by?: 'system' | 'manual';
    is_auto_initial?: boolean;
    invoice_total?: string;
    invoice_currency?: string;
  }) {
    const { data: result, error } = await supabaseAdmin
      .from('message_history')
      .insert(data)
      .select()
      .single();

    if (error) throw error;
    return result;
  },

  /**
   * Get message history with grouping by date, client, and invoices
   */
  async getHistory(filters?: {
    startDate?: string;
    endDate?: string;
    clientId?: number;
    messageType?: 'email' | 'sms' | 'whatsapp';
    limit?: number;
  }) {
    let query = supabase
      .from('message_history')
      .select('*')
      .order('sent_at', { ascending: false });

    if (filters?.startDate) {
      query = query.gte('sent_at', filters.startDate);
    }

    if (filters?.endDate) {
      // Append end of day time to include all messages sent on the end date
      const endDateTime = filters.endDate.includes('T') ? filters.endDate : `${filters.endDate}T23:59:59.999Z`;
      query = query.lte('sent_at', endDateTime);
    }

    if (filters?.clientId) {
      query = query.eq('client_id', filters.clientId);
    }

    if (filters?.messageType) {
      query = query.eq('message_type', filters.messageType);
    }

    if (filters?.limit) {
      query = query.limit(filters.limit);
    }

    const { data, error } = await query;

    if (error) throw error;
    return data;
  },

  /**
   * Get statistics summary
   */
  async getStats(filters?: {
    startDate?: string;
    endDate?: string;
  }) {
    let query = supabase
      .from('message_history')
      .select('message_type, status, level');

    if (filters?.startDate) {
      query = query.gte('sent_at', filters.startDate);
    }

    if (filters?.endDate) {
      // Append end of day time to include all messages sent on the end date
      const endDateTime = filters.endDate.includes('T') ? filters.endDate : `${filters.endDate}T23:59:59.999Z`;
      query = query.lte('sent_at', endDateTime);
    }

    const { data, error } = await query;

    if (error) throw error;

    // Calculate statistics
    const stats = {
      total: data.length,
      sent: data.filter(m => m.status === 'sent').length,
      failed: data.filter(m => m.status === 'failed').length,
      byType: {
        email: data.filter(m => m.message_type === 'email').length,
        sms: data.filter(m => m.message_type === 'sms').length,
        whatsapp: data.filter(m => m.message_type === 'whatsapp').length,
      },
      byLevel: {
        level1: data.filter(m => m.level === 1).length,
        level2: data.filter(m => m.level === 2).length,
        level3: data.filter(m => m.level === 3).length,
      },
    };

    return stats;
  },

  /**
   * Get daily statistics for last N days
   */
  async getDailyStats(days: number = 30) {
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);

    const { data, error } = await supabase
      .from('message_history')
      .select('sent_at, message_type, status')
      .gte('sent_at', startDate.toISOString())
      .order('sent_at', { ascending: false });

    if (error) throw error;

    // Group by date
    const dailyStats: Record<string, any> = {};

    data.forEach((msg: any) => {
      const date = new Date(msg.sent_at).toISOString().split('T')[0];

      if (!dailyStats[date]) {
        dailyStats[date] = {
          date,
          total: 0,
          sent: 0,
          failed: 0,
          email: 0,
          sms: 0,
          whatsapp: 0,
        };
      }

      dailyStats[date].total++;
      if (msg.status === 'sent') dailyStats[date].sent++;
      if (msg.status === 'failed') dailyStats[date].failed++;
      if (msg.message_type === 'email') dailyStats[date].email++;
      if (msg.message_type === 'sms') dailyStats[date].sms++;
      if (msg.message_type === 'whatsapp') dailyStats[date].whatsapp++;
    });

    return Object.values(dailyStats);
  },
};
