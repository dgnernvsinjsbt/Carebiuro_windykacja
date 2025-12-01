import { Mail, MessageSquare, Phone, Calendar, AlertCircle, CheckCircle, TrendingUp, ArrowLeft, RefreshCw } from 'lucide-react';
import Sidebar from '@/components/Sidebar';
import HistoriaFilters from './HistoriaFilters';
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
  let email = 0, sms = 0, whatsapp = 0;

  for (const msg of messages) {
    if (msg.message_type === 'email') email++;
    else if (msg.message_type === 'sms') sms++;
    else if (msg.message_type === 'whatsapp') whatsapp++;
  }

  return { total: messages.length, email, sms, whatsapp };
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
      <div className="flex-1 p-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <Link
              href="/"
              className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Powrót do listy klientów
            </Link>
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900 mb-2">Historia wysyłek</h1>
                <p className="text-gray-600">
                  Wszystkie wiadomości wysłane przez system
                  <span className="ml-2 text-xs text-gray-400">
                    (Załadowano: {new Date().toLocaleTimeString('pl-PL')})
                  </span>
                </p>
              </div>
              <Link
                href={`/historia?startDate=${startDate}&endDate=${endDate}&type=${messageType}&_t=${Date.now()}`}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Odśwież
              </Link>
            </div>
          </div>

          {/* Statistics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
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
          </div>

          {/* Filters - Client Component */}
          <HistoriaFilters
            currentStartDate={startDate}
            currentEndDate={endDate}
            currentType={messageType}
          />

          {/* History Timeline */}
          {groupedHistory.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <Calendar className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">Brak wiadomości w wybranym okresie</p>
            </div>
          ) : (
            <div className="space-y-6">
              {groupedHistory.map((day) => (
                <DayGroup key={day.date} day={day} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon, color }: { title: string; value: number; icon: React.ReactNode; color: string }) {
  const colorClasses: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-600',
    purple: 'bg-purple-50 text-purple-600',
    green: 'bg-green-50 text-green-600',
    emerald: 'bg-emerald-50 text-emerald-600',
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600 mb-1">{title}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          {icon}
        </div>
      </div>
    </div>
  );
}

function DayGroup({ day }: { day: any }) {
  const date = new Date(day.date);
  const dayName = date.toLocaleDateString('pl-PL', { weekday: 'long' });
  const formattedDate = `${date.getDate().toString().padStart(2, '0')}.${(date.getMonth() + 1).toString().padStart(2, '0')}.${date.getFullYear()} - ${dayName}`;

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="bg-gray-50 px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 capitalize">{formattedDate}</h2>
          <span className="text-sm text-gray-600">{day.totalMessages} wiadomości</span>
        </div>
      </div>
      <div className="divide-y divide-gray-200">
        {day.clients.map((client: any) => (
          <ClientGroup key={client.client_id} client={client} />
        ))}
      </div>
    </div>
  );
}

function ClientGroup({ client }: { client: any }) {
  const totalMessages = client.invoices.reduce((sum: number, inv: any) => sum + inv.messages.length, 0);

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
          <span className="text-blue-600 font-semibold text-sm">
            {client.client_name.charAt(0).toUpperCase()}
          </span>
        </div>
        <div>
          <h3 className="font-semibold text-gray-900">{client.client_name}</h3>
          <p className="text-sm text-gray-600">
            {client.invoices.length} {client.invoices.length === 1 ? 'faktura' : 'faktury'} • {totalMessages} {totalMessages === 1 ? 'wiadomość' : 'wiadomości'}
          </p>
        </div>
      </div>

      <div className="ml-13 space-y-3">
        {client.invoices.map((invoice: any) => (
          <InvoiceGroup key={invoice.invoice_id} invoice={invoice} />
        ))}
      </div>
    </div>
  );
}

function InvoiceGroup({ invoice }: { invoice: any }) {
  return (
    <div className="bg-gray-50 rounded-lg p-4 ml-13">
      <div className="flex items-center justify-between mb-3">
        <div>
          <span className="font-mono text-sm font-semibold text-gray-900">{invoice.invoice_number}</span>
          <span className="ml-3 text-sm text-gray-600">
            {parseFloat(invoice.invoice_total).toFixed(2)} {invoice.invoice_currency}
          </span>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {invoice.messages.map((message: any, idx: number) => (
          <MessageBadge key={`${message.sent_at}-${idx}`} message={message} />
        ))}
      </div>
    </div>
  );
}

function MessageBadge({ message }: { message: any }) {
  const getIcon = () => {
    switch (message.message_type) {
      case 'email': return <Mail className="w-3 h-3" />;
      case 'sms': return <Phone className="w-3 h-3" />;
      case 'whatsapp': return <MessageSquare className="w-3 h-3" />;
    }
  };

  const getColor = () => {
    if (message.status === 'failed') return 'bg-red-100 text-red-700 border-red-200';
    switch (message.message_type) {
      case 'email': return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'sms': return 'bg-green-100 text-green-700 border-green-200';
      case 'whatsapp': return 'bg-emerald-100 text-emerald-700 border-emerald-200';
    }
  };

  const getLabel = () => {
    const typeLabel = message.message_type === 'email' ? 'E' : message.message_type === 'sms' ? 'S' : 'W';
    return `${typeLabel}${message.level}`;
  };

  const time = new Date(message.sent_at).toLocaleTimeString('pl-PL', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/Warsaw',
  });

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border ${getColor()}`}
      title={message.error_message || `Wysłano: ${time}`}
    >
      {getIcon()}
      <span>{getLabel()}</span>
      {message.status === 'failed' && <AlertCircle className="w-3 h-3" />}
      {message.status === 'sent' && <CheckCircle className="w-3 h-3" />}
      {message.is_auto_initial && message.level !== 1 && <span className="ml-1 text-[10px]">🤖</span>}
      <span className="text-[10px] opacity-70">{time}</span>
    </div>
  );
}
