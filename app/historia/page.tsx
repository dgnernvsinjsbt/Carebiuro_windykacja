'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Mail, MessageSquare, Phone, Calendar, AlertCircle, CheckCircle, TrendingUp, ArrowLeft } from 'lucide-react';
import Sidebar from '@/components/Sidebar';

interface MessageGroup {
  date: string;
  totalMessages: number;
  clients: ClientGroup[];
}

interface ClientGroup {
  client_id: number;
  client_name: string;
  invoices: InvoiceGroup[];
}

interface InvoiceGroup {
  invoice_id: number;
  invoice_number: string;
  invoice_total: string;
  invoice_currency: string;
  messages: Message[];
}

interface Message {
  id: number;
  type: 'email' | 'sms' | 'whatsapp';
  level: number;
  status: 'sent' | 'failed';
  error_message?: string;
  sent_at: string;
  sent_by: string;
  is_auto_initial: boolean;
}

interface Stats {
  total: number;
  sent: number;
  failed: number;
  byType: {
    email: number;
    sms: number;
    whatsapp: number;
  };
  byLevel: {
    level1: number;
    level2: number;
    level3: number;
  };
}

/**
 * Format ISO date (yyyy-mm-dd) to Polish format (dd.mm.rrrr)
 */
function formatDateToPolish(isoDate: string): string {
  if (!isoDate) return '';
  const [year, month, day] = isoDate.split('-');
  return `${day}.${month}.${year}`;
}

/**
 * Parse Polish date (dd.mm.rrrr) to ISO format (yyyy-mm-dd)
 */
function parsePolishDate(polishDate: string): string | null {
  if (!polishDate) return null;

  // Remove extra spaces
  const cleaned = polishDate.trim();

  // Match dd.mm.rrrr or dd/mm/rrrr or dd-mm-rrrr
  const match = cleaned.match(/^(\d{1,2})[\.\/-](\d{1,2})[\.\/-](\d{4})$/);

  if (!match) return null;

  const day = match[1].padStart(2, '0');
  const month = match[2].padStart(2, '0');
  const year = match[3];

  // Validate date
  const date = new Date(`${year}-${month}-${day}`);
  if (isNaN(date.getTime())) return null;

  return `${year}-${month}-${day}`;
}

function getDateDaysAgo(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return date.toISOString().split('T')[0];
}

function getTodayDate(): string {
  return new Date().toISOString().split('T')[0];
}

export default function HistoriaPage() {
  const router = useRouter();
  const [history, setHistory] = useState<MessageGroup[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState({
    startDate: getDateDaysAgo(30),
    endDate: getTodayDate(),
  });
  const [selectedType, setSelectedType] = useState<string>('all');

  useEffect(() => {
    fetchHistory();
  }, [dateRange, selectedType]);

  async function fetchHistory() {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        startDate: dateRange.startDate,
        endDate: dateRange.endDate,
        limit: '1000',
      });

      if (selectedType !== 'all') {
        params.append('messageType', selectedType);
      }

      console.log('[Historia Frontend] Fetching with params:', {
        startDate: dateRange.startDate,
        endDate: dateRange.endDate,
        selectedType,
      });

      const response = await fetch(`/api/historia?${params}`);
      const data = await response.json();

      console.log('[Historia Frontend] Response:', {
        success: data.success,
        total: data.total,
        days: data.data?.length || 0,
        data: data.data,
      });

      if (data.success) {
        console.log('[Historia Frontend] Setting history with', data.data.length, 'days');
        setHistory(data.data);

        // Calculate stats from the SAME data (guaranteed consistency!)
        calculateStatsFromHistory(data.data);
      }
    } catch (error) {
      console.error('Failed to fetch history:', error);
    } finally {
      setLoading(false);
    }
  }

  function calculateStatsFromHistory(historyData: MessageGroup[]) {
    let totalEmail = 0;
    let totalSms = 0;
    let totalWhatsapp = 0;

    // Count messages from history data (single source of truth)
    for (const day of historyData) {
      for (const client of day.clients) {
        for (const invoice of client.invoices) {
          for (const message of invoice.messages) {
            if (message.type === 'email') totalEmail++;
            else if (message.type === 'sms') totalSms++;
            else if (message.type === 'whatsapp') totalWhatsapp++;
          }
        }
      }
    }

    const total = totalEmail + totalSms + totalWhatsapp;

    setStats({
      total,
      sent: total, // All messages from FISCAL_SYNC are sent
      failed: 0,
      byType: {
        email: totalEmail,
        sms: totalSms,
        whatsapp: totalWhatsapp,
      },
      byLevel: {
        level1: 0, // Can calculate if needed
        level2: 0,
        level3: 0,
      },
    });
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 p-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <button
              onClick={() => router.back()}
              className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Powrót do listy klientów
            </button>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Historia wysyłek</h1>
            <p className="text-gray-600">Wszystkie wiadomości wysłane przez system</p>
          </div>

        {/* Statistics Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <StatCard
              title="Wszystkie"
              value={stats.total}
              icon={<TrendingUp className="w-5 h-5" />}
              color="blue"
            />
            <StatCard
              title="Email"
              value={stats.byType.email}
              icon={<Mail className="w-5 h-5" />}
              color="purple"
            />
            <StatCard
              title="SMS"
              value={stats.byType.sms}
              icon={<Phone className="w-5 h-5" />}
              color="green"
            />
            <StatCard
              title="WhatsApp"
              value={stats.byType.whatsapp}
              icon={<MessageSquare className="w-5 h-5" />}
              color="emerald"
            />
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Data od</label>
              <input
                type="date"
                value={dateRange.startDate}
                onChange={(e) => setDateRange({ ...dateRange, startDate: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Data do</label>
              <input
                type="date"
                value={dateRange.endDate}
                onChange={(e) => setDateRange({ ...dateRange, endDate: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Typ wiadomości</label>
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">Wszystkie</option>
                <option value="email">Email</option>
                <option value="sms">SMS</option>
                <option value="whatsapp">WhatsApp</option>
              </select>
            </div>
          </div>
        </div>

        {/* History Timeline */}
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Ładowanie historii...</p>
          </div>
        ) : history.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <Calendar className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">Brak wiadomości w wybranym okresie</p>
          </div>
        ) : (
          <div className="space-y-6">
            {history.map((day) => (
              <DayGroup key={day.date} day={day} />
            ))}
          </div>
        )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon, color }: any) {
  const colorClasses = {
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
        <div className={`p-3 rounded-lg ${colorClasses[color as keyof typeof colorClasses]}`}>
          {icon}
        </div>
      </div>
    </div>
  );
}

function DayGroup({ day }: { day: MessageGroup }) {
  // Format: dd.mm.rrrr + dzień tygodnia
  const date = new Date(day.date);
  const dayName = date.toLocaleDateString('pl-PL', { weekday: 'long' });
  const formattedDate = `${date.getDate().toString().padStart(2, '0')}.${(date.getMonth() + 1).toString().padStart(2, '0')}.${date.getFullYear()} - ${dayName}`;

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      {/* Date Header */}
      <div className="bg-gray-50 px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 capitalize">{formattedDate}</h2>
          <span className="text-sm text-gray-600">{day.totalMessages} wiadomości</span>
        </div>
      </div>

      {/* Clients */}
      <div className="divide-y divide-gray-200">
        {day.clients.map((client) => (
          <ClientGroup key={client.client_id} client={client} />
        ))}
      </div>
    </div>
  );
}

function ClientGroup({ client }: { client: ClientGroup }) {
  const [expanded, setExpanded] = useState(true);

  // Calculate total messages for this client
  const totalMessages = client.invoices.reduce((sum, inv) => sum + inv.messages.length, 0);

  return (
    <div className="p-6">
      {/* Client Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between mb-4 hover:bg-gray-50 p-3 rounded-lg transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
            <span className="text-blue-600 font-semibold text-sm">
              {client.client_name.charAt(0).toUpperCase()}
            </span>
          </div>
          <div className="text-left">
            <h3 className="font-semibold text-gray-900">{client.client_name}</h3>
            <p className="text-sm text-gray-600">
              {client.invoices.length} {client.invoices.length === 1 ? 'faktura' : 'faktury'} • {totalMessages} {totalMessages === 1 ? 'wiadomość' : 'wiadomości'}
            </p>
          </div>
        </div>
        <span className="text-gray-400">{expanded ? '−' : '+'}</span>
      </button>

      {/* Invoices */}
      {expanded && (
        <div className="ml-16 space-y-3">
          {client.invoices.map((invoice) => (
            <InvoiceGroup key={invoice.invoice_id} invoice={invoice} />
          ))}
        </div>
      )}
    </div>
  );
}

function InvoiceGroup({ invoice }: { invoice: InvoiceGroup }) {
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      {/* Invoice Header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <span className="font-mono text-sm font-semibold text-gray-900">{invoice.invoice_number}</span>
          <span className="ml-3 text-sm text-gray-600">
            {parseFloat(invoice.invoice_total).toFixed(2)} {invoice.invoice_currency}
          </span>
        </div>
      </div>

      {/* Messages - Compact display */}
      <div className="flex flex-wrap gap-2">
        {invoice.messages.map((message) => (
          <MessageBadge key={message.id} message={message} />
        ))}
      </div>
    </div>
  );
}

function MessageBadge({ message }: { message: Message }) {
  const getIcon = () => {
    switch (message.type) {
      case 'email':
        return <Mail className="w-3 h-3" />;
      case 'sms':
        return <Phone className="w-3 h-3" />;
      case 'whatsapp':
        return <MessageSquare className="w-3 h-3" />;
    }
  };

  const getColor = () => {
    if (message.status === 'failed') return 'bg-red-100 text-red-700 border-red-200';
    switch (message.type) {
      case 'email':
        return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'sms':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'whatsapp':
        return 'bg-emerald-100 text-emerald-700 border-emerald-200';
    }
  };

  const getLabel = () => {
    const typeLabel = message.type === 'email' ? 'E' : message.type === 'sms' ? 'S' : 'W';
    return `${typeLabel}${message.level}`;
  };

  // Parse sent_at and ensure it's displayed in Europe/Warsaw timezone
  // Supabase returns UTC timestamps, we need to convert to local Polish time
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
