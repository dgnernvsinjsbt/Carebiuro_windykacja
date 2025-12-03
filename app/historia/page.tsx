import { Mail, MessageSquare, Phone, TrendingUp, ArrowLeft, RefreshCw, AlertCircle } from 'lucide-react';
import Sidebar from '@/components/Sidebar';
import HistoriaFilters from './HistoriaFilters';
import HistoriaViews from './HistoriaViews';
import Link from 'next/link';
import { supabaseAdmin } from '@/lib/supabase';

// Force dynamic rendering - no caching
export const dynamic = 'force-dynamic';
export const revalidate = 0;

interface MessageHistoryRow {
  id: number;
  client_id: number;
  client_name: string;
  invoice_id: number;
  invoice_number: string;
  invoice_total: number;
  invoice_currency: string;
  message_type: 'email' | 'sms' | 'whatsapp';
  level: number;
  status: string;
  error_message: string | null;
  sent_at: string;
  sent_by: string;
  is_auto_initial: boolean;
}

interface PageProps {
  searchParams: Promise<{
    startDate?: string;
    endDate?: string;
    type?: string;
  }>;
}

function getDateDaysAgo(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return date.toISOString().split('T')[0];
}

function getDateDaysAhead(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().split('T')[0];
}

async function fetchMessages(startDate: string, endDate: string, messageType?: string) {
  const supabase = supabaseAdmin();

  console.log('[Historia Server] Fetching messages:', { startDate, endDate, messageType });

  let query = supabase
    .from('message_history')
    .select('*')
    .order('sent_at', { ascending: false });

  // Date filters
  if (startDate) {
    query = query.gte('sent_at', `${startDate}T00:00:00Z`);
  }
  if (endDate) {
    const [year, month, day] = endDate.split('-').map(Number);
    const nextDay = new Date(Date.UTC(year, month - 1, day + 1));
    query = query.lt('sent_at', nextDay.toISOString());
  }
  if (messageType && messageType !== 'all') {
    query = query.eq('message_type', messageType);
  }

  const { data, error } = await query;

  if (error) {
    console.error('[Historia Server] Error:', error);
    throw error;
  }

  console.log('[Historia Server] Found', data?.length || 0, 'messages');
  return data || [];
}

function groupMessagesByDate(messages: MessageHistoryRow[]) {
  const grouped: Record<string, {
    date: string;
    totalMessages: number;
    clients: Record<string, {
      client_id: number;
      client_name: string;
      invoices: Record<string, {
        invoice_id: number;
        invoice_number: string;
        invoice_total: number;
        invoice_currency: string;
        messages: MessageHistoryRow[];
      }>;
    }>;
  }> = {};

  for (const msg of messages) {
    const date = new Date(msg.sent_at).toISOString().split('T')[0];

    if (!grouped[date]) {
      grouped[date] = { date, totalMessages: 0, clients: {} };
    }

    const clientKey = String(msg.client_id);
    if (!grouped[date].clients[clientKey]) {
      grouped[date].clients[clientKey] = {
        client_id: msg.client_id,
        client_name: msg.client_name,
        invoices: {},
      };
    }

    const invoiceKey = String(msg.invoice_id);
    if (!grouped[date].clients[clientKey].invoices[invoiceKey]) {
      grouped[date].clients[clientKey].invoices[invoiceKey] = {
        invoice_id: msg.invoice_id,
        invoice_number: msg.invoice_number,
        invoice_total: msg.invoice_total,
        invoice_currency: msg.invoice_currency,
        messages: [],
      };
    }

    grouped[date].clients[clientKey].invoices[invoiceKey].messages.push(msg);
    grouped[date].totalMessages++;
  }

  // Convert to arrays
  return Object.values(grouped).map(day => ({
    ...day,
    clients: Object.values(day.clients).map(client => ({
      ...client,
      invoices: Object.values(client.invoices),
    })),
  }));
}

function calculateStats(messages: MessageHistoryRow[]) {
  let email = 0, sms = 0, whatsapp = 0, failed = 0;

  for (const msg of messages) {
    if (msg.message_type === 'email') email++;
    else if (msg.message_type === 'sms') sms++;
    else if (msg.message_type === 'whatsapp') whatsapp++;
    if (msg.status === 'failed') failed++;
  }

  return { total: messages.length, email, sms, whatsapp, failed };
}

export default async function HistoriaPage({ searchParams }: PageProps) {
  const params = await searchParams;

  // Default dates: 30 days ago to 30 days ahead
  const startDate = params.startDate || getDateDaysAgo(30);
  const endDate = params.endDate || getDateDaysAhead(30);
  const messageType = params.type || 'all';

  // Fetch data on server - NO CACHING
  const messages = await fetchMessages(startDate, endDate, messageType);
  const groupedHistory = groupMessagesByDate(messages);
  const stats = calculateStats(messages);

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 p-6 lg:p-8">
        {/* WIDER CONTAINER: max-w-[1600px] instead of max-w-7xl (1280px) */}
        <div className="max-w-[1600px] mx-auto">
          {/* Header */}
          <div className="mb-6">
            <Link
              href="/"
              className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Powrót do listy klientów
            </Link>
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
              <div>
                <h1 className="text-2xl lg:text-3xl font-bold text-gray-900 mb-1">Historia wysyłek</h1>
                <p className="text-gray-600 text-sm">
                  Wszystkie wiadomości wysłane przez system
                  <span className="ml-2 text-xs text-gray-400">
                    (Załadowano: {new Date().toLocaleTimeString('pl-PL')})
                  </span>
                </p>
              </div>
              <Link
                href={`/historia?startDate=${startDate}&endDate=${endDate}&type=${messageType}&_t=${Date.now()}`}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 transition-colors text-sm font-medium self-start lg:self-auto"
              >
                <RefreshCw className="w-4 h-4" />
                Odśwież
              </Link>
            </div>
          </div>

          {/* Statistics Cards - 5 columns on xl screens */}
          <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-5 gap-4 mb-6">
            <StatCard
              title="Wszystkie"
              value={stats.total}
              icon={<TrendingUp className="w-5 h-5" />}
              color="blue"
            />
            <StatCard
              title="Email"
              value={stats.email}
              icon={<Mail className="w-5 h-5" />}
              color="purple"
            />
            <StatCard
              title="SMS"
              value={stats.sms}
              icon={<Phone className="w-5 h-5" />}
              color="green"
            />
            <StatCard
              title="WhatsApp"
              value={stats.whatsapp}
              icon={<MessageSquare className="w-5 h-5" />}
              color="emerald"
            />
            <StatCard
              title="Błędy"
              value={stats.failed}
              icon={<AlertCircle className="w-5 h-5" />}
              color="red"
              highlight={stats.failed > 0}
            />
          </div>

          {/* Filters - Client Component */}
          <HistoriaFilters
            currentStartDate={startDate}
            currentEndDate={endDate}
            currentType={messageType}
          />

          {/* History Views - Client Component with Table/Timeline/Split toggle */}
          <HistoriaViews
            messages={messages}
            groupedHistory={groupedHistory}
          />
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon, color, highlight = false }: {
  title: string;
  value: number;
  icon: React.ReactNode;
  color: string;
  highlight?: boolean;
}) {
  const colorClasses: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-600',
    purple: 'bg-purple-50 text-purple-600',
    green: 'bg-green-50 text-green-600',
    emerald: 'bg-emerald-50 text-emerald-600',
    red: 'bg-red-50 text-red-600',
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{title}</p>
          <p className={`text-2xl font-bold mt-1 ${highlight && value > 0 ? 'text-red-600' : 'text-gray-900'}`}>
            {value}
          </p>
        </div>
        <div className={`p-2.5 rounded-lg ${colorClasses[color]}`}>
          {icon}
        </div>
      </div>
    </div>
  );
}

