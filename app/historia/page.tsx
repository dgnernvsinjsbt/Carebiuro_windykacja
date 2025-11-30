'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import useSWR from 'swr';
import { Mail, MessageSquare, Phone, Calendar, AlertCircle, CheckCircle, TrendingUp, ArrowLeft, RefreshCw } from 'lucide-react';
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

// SWR fetcher with cache buster
const fetcher = async (url: string) => {
  // Add timestamp to bypass ALL caches (Vercel Edge, CDN, browser)
  const cacheBuster = `_t=${Date.now()}&_r=${Math.random()}`;
  const fullUrl = url.includes('?') ? `${url}&${cacheBuster}` : `${url}?${cacheBuster}`;

  console.log('[Historia SWR] Fetching:', fullUrl);
  const res = await fetch(fullUrl, {
    cache: 'no-store',
    headers: {
      'Cache-Control': 'no-cache',
      'Pragma': 'no-cache',
    }
  });
  if (!res.ok) throw new Error('Failed to fetch');
  const data = await res.json();
  console.log('[Historia SWR] Response:', { total: data.total, days: data.data?.length });
  return data;
};

function getDateDaysAgo(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() - days);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function getDateDaysAhead(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export default function HistoriaPage() {
  const router = useRouter();

  // Initialize dates - endDate 30 days ahead to ensure ALL messages are visible
  const [startDate, setStartDate] = useState(() => getDateDaysAgo(30));
  const [endDate, setEndDate] = useState(() => getDateDaysAhead(30));
  const [selectedType, setSelectedType] = useState<string>('all');

  // Build API URL
  const buildUrl = useCallback(() => {
    const params = new URLSearchParams({
      startDate,
      endDate,
      limit: '1000',
    });
    if (selectedType !== 'all') {
      params.append('messageType', selectedType);
    }
    return `/api/historia?${params}`;
  }, [startDate, endDate, selectedType]);

  // SWR hook - automatic revalidation on focus, reconnect, and interval
  const { data, error, isLoading, mutate } = useSWR(
    buildUrl(),
    fetcher,
    {
      revalidateOnFocus: true,        // Refetch when window gains focus
      revalidateOnReconnect: true,    // Refetch on network reconnect
      refreshInterval: 0,              // No polling (manual refresh only)
      dedupingInterval: 2000,          // Dedupe requests within 2s
      keepPreviousData: true,          // Show old data while fetching new
    }
  );

  // Extract history data
  const history: MessageGroup[] = data?.data || [];

  // Calculate stats from history
  const stats = calculateStatsFromHistory(history);

  // Manual refresh function
  const handleRefresh = () => {
    console.log('[Historia] Manual refresh triggered');
    mutate();
  };

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
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900 mb-2">Historia wysyłek</h1>
                <p className="text-gray-600">Wszystkie wiadomości wysłane przez system</p>
              </div>
              <button
                onClick={handleRefresh}
                disabled={isLoading}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 transition-colors ${isLoading ? 'opacity-50' : ''}`}
                title="Odśwież dane"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                Odśwież
              </button>
            </div>
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
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Data do</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
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

          {/* Error state */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6 mb-8">
              <p className="text-red-600">Błąd ładowania danych. Spróbuj odświeżyć.</p>
            </div>
          )}

          {/* History Timeline */}
          {isLoading && history.length === 0 ? (
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
              {isLoading && (
                <div className="text-center text-sm text-gray-500 mb-4">
                  Odświeżanie danych...
                </div>
              )}
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

function calculateStatsFromHistory(historyData: MessageGroup[]): Stats {
  let totalEmail = 0;
  let totalSms = 0;
  let totalWhatsapp = 0;

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

  return {
    total,
    sent: total,
    failed: 0,
    byType: {
      email: totalEmail,
      sms: totalSms,
      whatsapp: totalWhatsapp,
    },
    byLevel: {
      level1: 0,
      level2: 0,
      level3: 0,
    },
  };
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
        {day.clients.map((client) => (
          <ClientGroup key={client.client_id} client={client} />
        ))}
      </div>
    </div>
  );
}

function ClientGroup({ client }: { client: ClientGroup }) {
  const [expanded, setExpanded] = useState(true);
  const totalMessages = client.invoices.reduce((sum, inv) => sum + inv.messages.length, 0);

  return (
    <div className="p-6">
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
      <div className="flex items-center justify-between mb-3">
        <div>
          <span className="font-mono text-sm font-semibold text-gray-900">{invoice.invoice_number}</span>
          <span className="ml-3 text-sm text-gray-600">
            {parseFloat(invoice.invoice_total).toFixed(2)} {invoice.invoice_currency}
          </span>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {invoice.messages.map((message, idx) => (
          <MessageBadge key={`${message.sent_at}-${idx}`} message={message} />
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
