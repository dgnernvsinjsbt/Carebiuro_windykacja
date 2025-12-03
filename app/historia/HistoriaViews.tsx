'use client';

import { useState, useMemo } from 'react';
import {
  Mail, MessageSquare, Phone, Calendar, AlertCircle, CheckCircle,
  ChevronDown, ChevronRight, Table, Clock, Columns, X, Check, Search
} from 'lucide-react';

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

interface GroupedDay {
  date: string;
  totalMessages: number;
  clients: {
    client_id: number;
    client_name: string;
    invoices: {
      invoice_id: number;
      invoice_number: string;
      invoice_total: number;
      invoice_currency: string;
      messages: MessageHistoryRow[];
    }[];
  }[];
}

type ViewType = 'table' | 'timeline' | 'split';

interface HistoriaViewsProps {
  messages: MessageHistoryRow[];
  groupedHistory: GroupedDay[];
}

export default function HistoriaViews({ messages, groupedHistory }: HistoriaViewsProps) {
  const [currentView, setCurrentView] = useState<ViewType>('table');
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  const [clientSearch, setClientSearch] = useState('');
  const [selectedMessage, setSelectedMessage] = useState<MessageHistoryRow | null>(
    messages.length > 0 ? messages[0] : null
  );

  // Filter messages by client name
  const filteredMessages = useMemo(() => {
    if (!clientSearch.trim()) return messages;
    const searchLower = clientSearch.toLowerCase().trim();
    return messages.filter(msg =>
      msg.client_name.toLowerCase().includes(searchLower)
    );
  }, [messages, clientSearch]);

  // Filter grouped history by client name
  const filteredGroupedHistory = useMemo(() => {
    if (!clientSearch.trim()) return groupedHistory;
    const searchLower = clientSearch.toLowerCase().trim();

    return groupedHistory
      .map(day => ({
        ...day,
        clients: day.clients.filter(client =>
          client.client_name.toLowerCase().includes(searchLower)
        ),
      }))
      .filter(day => day.clients.length > 0)
      .map(day => ({
        ...day,
        totalMessages: day.clients.reduce(
          (sum, client) => sum + client.invoices.reduce(
            (invSum, inv) => invSum + inv.messages.length, 0
          ), 0
        ),
      }));
  }, [groupedHistory, clientSearch]);

  const toggleRow = (id: number) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedRows(newExpanded);
  };

  const clearSearch = () => {
    setClientSearch('');
  };

  return (
    <div>
      {/* Search and View Toggle */}
      <div className="flex flex-col sm:flex-row justify-between gap-4 mb-4">
        {/* Client Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Szukaj klienta..."
            value={clientSearch}
            onChange={(e) => setClientSearch(e.target.value)}
            className="w-full pl-10 pr-10 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm bg-white"
          />
          {clientSearch && (
            <button
              onClick={clearSearch}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* View Toggle */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-1 flex gap-1">
          <button
            onClick={() => setCurrentView('table')}
            className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors flex items-center gap-1.5 ${
              currentView === 'table'
                ? 'bg-blue-600 text-white'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <Table className="w-4 h-4" />
            Tabela
          </button>
          <button
            onClick={() => setCurrentView('timeline')}
            className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors flex items-center gap-1.5 ${
              currentView === 'timeline'
                ? 'bg-blue-600 text-white'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <Clock className="w-4 h-4" />
            Timeline
          </button>
          <button
            onClick={() => setCurrentView('split')}
            className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors flex items-center gap-1.5 ${
              currentView === 'split'
                ? 'bg-blue-600 text-white'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <Columns className="w-4 h-4" />
            Split
          </button>
        </div>
      </div>

      {/* Search Results Count */}
      {clientSearch && (
        <div className="mb-4 text-sm text-gray-600">
          Znaleziono <span className="font-semibold">{filteredMessages.length}</span> wiadomości
          {filteredMessages.length !== messages.length && (
            <span> (z {messages.length} wszystkich)</span>
          )}
          {filteredMessages.length > 0 && (
            <span> dla klienta zawierającego &quot;{clientSearch}&quot;</span>
          )}
        </div>
      )}

      {/* Empty State */}
      {filteredMessages.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
          <Calendar className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600">
            {clientSearch
              ? `Brak wiadomości dla klienta "${clientSearch}"`
              : 'Brak wiadomości w wybranym okresie'}
          </p>
          {clientSearch && (
            <button
              onClick={clearSearch}
              className="mt-3 text-blue-600 hover:text-blue-700 text-sm font-medium"
            >
              Wyczyść wyszukiwanie
            </button>
          )}
        </div>
      ) : (
        <>
          {currentView === 'table' && (
            <TableView
              messages={filteredMessages}
              expandedRows={expandedRows}
              toggleRow={toggleRow}
            />
          )}
          {currentView === 'timeline' && (
            <TimelineView groupedHistory={filteredGroupedHistory} />
          )}
          {currentView === 'split' && (
            <SplitView
              messages={filteredMessages}
              selectedMessage={selectedMessage}
              setSelectedMessage={setSelectedMessage}
            />
          )}
        </>
      )}
    </div>
  );
}

// ============================================
// TABLE VIEW
// ============================================
function TableView({
  messages,
  expandedRows,
  toggleRow
}: {
  messages: MessageHistoryRow[];
  expandedRows: Set<number>;
  toggleRow: (id: number) => void;
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Data/Czas</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Klient</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Faktura</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Kwota</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Typ</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Poziom</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Status</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Nadawca</th>
              <th className="w-10"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {messages.map((message) => (
              <TableRow
                key={message.id}
                message={message}
                isExpanded={expandedRows.has(message.id)}
                onToggle={() => toggleRow(message.id)}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TableRow({
  message,
  isExpanded,
  onToggle
}: {
  message: MessageHistoryRow;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const date = new Date(message.sent_at);
  const formattedDate = date.toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit', year: 'numeric' });
  const formattedTime = date.toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Warsaw' });
  const fullDateTime = date.toLocaleString('pl-PL', { timeZone: 'Europe/Warsaw' });

  const isFailed = message.status === 'failed';

  return (
    <>
      <tr
        className={`cursor-pointer transition-colors ${isFailed ? 'bg-red-50/50 hover:bg-red-50' : 'hover:bg-gray-50'}`}
        onClick={onToggle}
      >
        <td className="px-4 py-3">
          <div className="text-sm font-medium text-gray-900">{formattedDate}</div>
          <div className="text-xs text-gray-500">{formattedTime}</div>
        </td>
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            <ClientAvatar name={message.client_name} />
            <span className="text-sm font-medium text-gray-900 truncate max-w-[200px]">
              {message.client_name}
            </span>
          </div>
        </td>
        <td className="px-4 py-3">
          <span className="font-mono text-sm text-gray-700">{message.invoice_number}</span>
        </td>
        <td className="px-4 py-3">
          <span className="text-sm font-semibold text-gray-900">
            {parseFloat(String(message.invoice_total)).toLocaleString('pl-PL', { minimumFractionDigits: 2 })} {message.invoice_currency}
          </span>
        </td>
        <td className="px-4 py-3">
          <TypeBadge type={message.message_type} />
        </td>
        <td className="px-4 py-3">
          <LevelBadge level={message.level} />
        </td>
        <td className="px-4 py-3">
          <StatusBadge status={message.status} />
        </td>
        <td className="px-4 py-3">
          <span className="text-xs text-gray-500">{message.sent_by || 'System'}</span>
        </td>
        <td className="px-4 py-3">
          <ChevronDown
            className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          />
        </td>
      </tr>
      {isExpanded && (
        <tr className={isFailed ? 'bg-red-50' : 'bg-gray-50'}>
          <td colSpan={9} className="px-4 py-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">
                  {message.message_type === 'email' ? 'Odbiorca email' : 'Numer telefonu'}
                </p>
                <p className="text-gray-900">—</p>
              </div>
              {isFailed ? (
                <div>
                  <p className="text-red-600 text-xs uppercase tracking-wide mb-1">Błąd</p>
                  <p className="text-red-700 font-medium">{message.error_message || 'Nieznany błąd'}</p>
                </div>
              ) : (
                <div>
                  <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">
                    {message.message_type === 'email' ? 'Temat' : 'Treść'}
                  </p>
                  <p className="text-gray-900 truncate">Przypomnienie o płatności - {message.invoice_number}</p>
                </div>
              )}
              <div>
                <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">Pełna data wysyłki</p>
                <p className="text-gray-900">{fullDateTime}</p>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ============================================
// TIMELINE VIEW
// ============================================
function TimelineView({ groupedHistory }: { groupedHistory: GroupedDay[] }) {
  return (
    <div className="space-y-6">
      {groupedHistory.map((day) => (
        <DayGroup key={day.date} day={day} />
      ))}
    </div>
  );
}

function DayGroup({ day }: { day: GroupedDay }) {
  const date = new Date(day.date);
  const dayName = date.toLocaleDateString('pl-PL', { weekday: 'long' });
  const formattedDate = `${date.getDate().toString().padStart(2, '0')}.${(date.getMonth() + 1).toString().padStart(2, '0')}.${date.getFullYear()} - ${dayName}`;

  // Count message types
  const typeCounts = { email: 0, sms: 0, whatsapp: 0, failed: 0 };
  day.clients.forEach(client => {
    client.invoices.forEach(invoice => {
      invoice.messages.forEach(msg => {
        if (msg.status === 'failed') typeCounts.failed++;
        if (msg.message_type === 'email') typeCounts.email++;
        else if (msg.message_type === 'sms') typeCounts.sms++;
        else if (msg.message_type === 'whatsapp') typeCounts.whatsapp++;
      });
    });
  });

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="bg-gradient-to-r from-gray-50 to-white px-6 py-4 border-b border-gray-100">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <Calendar className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 capitalize">{formattedDate}</h2>
              <p className="text-sm text-gray-500">{day.totalMessages} wiadomości</p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {typeCounts.email > 0 && (
              <span className="px-2.5 py-1 bg-purple-100 text-purple-700 rounded-full text-xs font-medium">
                {typeCounts.email} email
              </span>
            )}
            {typeCounts.sms > 0 && (
              <span className="px-2.5 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium">
                {typeCounts.sms} sms
              </span>
            )}
            {typeCounts.whatsapp > 0 && (
              <span className="px-2.5 py-1 bg-emerald-100 text-emerald-700 rounded-full text-xs font-medium">
                {typeCounts.whatsapp} whatsapp
              </span>
            )}
            {typeCounts.failed > 0 && (
              <span className="px-2.5 py-1 bg-red-100 text-red-700 rounded-full text-xs font-medium">
                {typeCounts.failed} błąd
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="divide-y divide-gray-100">
        {day.clients.map((client) => (
          <ClientGroup key={client.client_id} client={client} />
        ))}
      </div>
    </div>
  );
}

function ClientGroup({ client }: { client: GroupedDay['clients'][0] }) {
  const totalMessages = client.invoices.reduce((sum, inv) => sum + inv.messages.length, 0);

  return (
    <div className="p-6">
      <div className="flex items-start gap-4 mb-4">
        <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center flex-shrink-0">
          <span className="text-blue-600 font-bold text-lg">
            {client.client_name.charAt(0).toUpperCase()}
          </span>
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900">{client.client_name}</h3>
          <p className="text-sm text-gray-500">
            {client.invoices.length} {client.invoices.length === 1 ? 'faktura' : 'faktury'} • {totalMessages} {totalMessages === 1 ? 'wiadomość' : 'wiadomości'}
          </p>
        </div>
      </div>

      <div className="ml-16 space-y-3">
        {client.invoices.map((invoice) => (
          <InvoiceGroup key={invoice.invoice_id} invoice={invoice} />
        ))}
      </div>
    </div>
  );
}

function InvoiceGroup({ invoice }: { invoice: GroupedDay['clients'][0]['invoices'][0] }) {
  return (
    <div className="bg-gray-50 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="font-mono text-sm font-semibold text-gray-900">{invoice.invoice_number}</span>
          <span className="text-sm font-semibold text-blue-600">
            {parseFloat(String(invoice.invoice_total)).toLocaleString('pl-PL', { minimumFractionDigits: 2 })} {invoice.invoice_currency}
          </span>
        </div>
      </div>
      <div className="flex flex-wrap gap-3">
        {invoice.messages.map((message, idx) => (
          <MessageCard key={`${message.sent_at}-${idx}`} message={message} />
        ))}
      </div>
    </div>
  );
}

function MessageCard({ message }: { message: MessageHistoryRow }) {
  const time = new Date(message.sent_at).toLocaleTimeString('pl-PL', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/Warsaw',
  });

  const isFailed = message.status === 'failed';

  const getTypeColor = () => {
    if (isFailed) return 'bg-red-50 border-red-300';
    switch (message.message_type) {
      case 'email': return 'bg-white border-purple-200';
      case 'sms': return 'bg-white border-green-200';
      case 'whatsapp': return 'bg-white border-emerald-200';
      default: return 'bg-white border-gray-200';
    }
  };

  const getIconBg = () => {
    if (isFailed) return 'bg-red-100';
    switch (message.message_type) {
      case 'email': return 'bg-purple-100';
      case 'sms': return 'bg-green-100';
      case 'whatsapp': return 'bg-emerald-100';
      default: return 'bg-gray-100';
    }
  };

  const getIconColor = () => {
    if (isFailed) return 'text-red-600';
    switch (message.message_type) {
      case 'email': return 'text-purple-600';
      case 'sms': return 'text-green-600';
      case 'whatsapp': return 'text-emerald-600';
      default: return 'text-gray-600';
    }
  };

  const getTypeLabel = () => {
    switch (message.message_type) {
      case 'email': return 'Email';
      case 'sms': return 'SMS';
      case 'whatsapp': return 'WhatsApp';
      default: return message.message_type;
    }
  };

  const getIcon = () => {
    switch (message.message_type) {
      case 'email': return <Mail className="w-4 h-4" />;
      case 'sms': return <Phone className="w-4 h-4" />;
      case 'whatsapp': return <MessageSquare className="w-4 h-4" />;
      default: return <Mail className="w-4 h-4" />;
    }
  };

  return (
    <div className="group relative">
      <div className={`flex items-center gap-2 px-3 py-2 border rounded-lg shadow-sm hover:shadow-md transition-shadow cursor-pointer ${getTypeColor()}`}>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${getIconBg()}`}>
          <span className={getIconColor()}>{getIcon()}</span>
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className={`text-sm font-medium ${isFailed ? 'text-red-900' : 'text-gray-900'}`}>
              {getTypeLabel()}
            </span>
            <LevelBadge level={message.level} small />
          </div>
          <div className={`flex items-center gap-1 text-xs ${isFailed ? 'text-red-600' : 'text-gray-500'}`}>
            {isFailed ? (
              <>
                <X className="w-3 h-3" />
                {time} - Błąd
              </>
            ) : (
              <>
                <Check className="w-3 h-3 text-green-500" />
                {time}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Hover tooltip */}
      <div className="absolute bottom-full left-0 mb-2 hidden group-hover:block z-10">
        <div className={`text-white text-xs rounded-lg px-3 py-2 whitespace-nowrap ${isFailed ? 'bg-red-900' : 'bg-gray-900'}`}>
          {isFailed ? (
            <>
              <p><strong>Błąd:</strong> {message.error_message || 'Nieznany błąd'}</p>
              <p><strong>Próba:</strong> {new Date(message.sent_at).toLocaleString('pl-PL', { timeZone: 'Europe/Warsaw' })}</p>
            </>
          ) : (
            <>
              <p><strong>Wysłano:</strong> {new Date(message.sent_at).toLocaleString('pl-PL', { timeZone: 'Europe/Warsaw' })}</p>
              <p><strong>Przez:</strong> {message.sent_by || 'System'}</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================
// SPLIT VIEW
// ============================================
function SplitView({
  messages,
  selectedMessage,
  setSelectedMessage
}: {
  messages: MessageHistoryRow[];
  selectedMessage: MessageHistoryRow | null;
  setSelectedMessage: (msg: MessageHistoryRow) => void;
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="flex" style={{ height: '600px' }}>
        {/* Left panel - message list */}
        <div className="w-2/5 border-r border-gray-200 overflow-y-auto">
          <div className="divide-y divide-gray-100">
            {messages.map((message) => (
              <SplitListItem
                key={message.id}
                message={message}
                isSelected={selectedMessage?.id === message.id}
                onClick={() => setSelectedMessage(message)}
              />
            ))}
          </div>
        </div>

        {/* Right panel - message details */}
        <div className="w-3/5 p-6 overflow-y-auto bg-gray-50/50">
          {selectedMessage ? (
            <MessageDetails message={selectedMessage} />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              Wybierz wiadomość z listy
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SplitListItem({
  message,
  isSelected,
  onClick
}: {
  message: MessageHistoryRow;
  isSelected: boolean;
  onClick: () => void;
}) {
  const time = new Date(message.sent_at).toLocaleTimeString('pl-PL', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/Warsaw',
  });

  const isFailed = message.status === 'failed';

  return (
    <div
      className={`px-4 py-3 cursor-pointer border-l-4 transition-colors ${
        isSelected
          ? 'bg-blue-50 border-l-blue-600'
          : isFailed
            ? 'bg-red-50/50 border-l-transparent hover:bg-red-50'
            : 'border-l-transparent hover:bg-gray-50'
      }`}
      onClick={onClick}
    >
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <TypeIcon type={message.message_type} failed={isFailed} />
          <span className="text-sm font-semibold text-gray-900 truncate max-w-[180px]">
            {message.client_name}
          </span>
        </div>
        <span className="text-xs text-gray-500">{time}</span>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-600 truncate">
          {message.invoice_number} • {parseFloat(String(message.invoice_total)).toLocaleString('pl-PL', { minimumFractionDigits: 2 })} {message.invoice_currency}
        </span>
        <div className="flex items-center gap-1">
          <LevelBadge level={message.level} small />
          {isFailed ? (
            <X className="w-3.5 h-3.5 text-red-500" />
          ) : (
            <Check className="w-3.5 h-3.5 text-green-500" />
          )}
        </div>
      </div>
    </div>
  );
}

function MessageDetails({ message }: { message: MessageHistoryRow }) {
  const isFailed = message.status === 'failed';
  const fullDateTime = new Date(message.sent_at).toLocaleString('pl-PL', { timeZone: 'Europe/Warsaw' });

  const getLevelLabel = () => {
    switch (message.level) {
      case 1: return 'Pierwsze przypomnienie';
      case 2: return 'Drugie przypomnienie';
      case 3: return 'Trzecie przypomnienie';
      case 4: return 'Ostateczne wezwanie';
      default: return `Poziom ${message.level}`;
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <ClientAvatar name={message.client_name} size="lg" />
          <div>
            <h3 className="text-xl font-bold text-gray-900">{message.client_name}</h3>
            <p className="text-sm text-gray-500">—</p>
          </div>
        </div>
        <StatusBadge status={message.status} large />
      </div>

      {/* Error banner */}
      {isFailed && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center flex-shrink-0">
              <AlertCircle className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-red-800">Błąd wysyłki</p>
              <p className="text-sm text-red-700 mt-1">{message.error_message || 'Nieznany błąd'}</p>
            </div>
          </div>
        </div>
      )}

      {/* Message info */}
      <div className="bg-white rounded-xl p-5 mb-6 border border-gray-200">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Typ wiadomości</p>
            <div className="flex items-center gap-2">
              <TypeIcon type={message.message_type} />
              <span className="text-sm font-semibold text-gray-900">
                {message.message_type === 'email' ? 'Email' : message.message_type === 'sms' ? 'SMS' : 'WhatsApp'}
              </span>
            </div>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Poziom przypomnienia</p>
            <div className="flex items-center gap-2">
              <LevelBadge level={message.level} />
              <span className="text-sm text-gray-600">{getLevelLabel()}</span>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
              {isFailed ? 'Próba wysłania' : 'Data i czas wysłania'}
            </p>
            <p className="text-sm font-medium text-gray-900">{fullDateTime}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Wysłano przez</p>
            <p className="text-sm font-medium text-gray-900">{message.sent_by || 'System (automatycznie)'}</p>
          </div>
        </div>
      </div>

      {/* Invoice info */}
      <div className="mb-6">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Faktura</p>
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-mono text-lg font-semibold text-gray-900">{message.invoice_number}</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-blue-600">
                {parseFloat(String(message.invoice_total)).toLocaleString('pl-PL', { minimumFractionDigits: 2 })} {message.invoice_currency}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================
// SHARED COMPONENTS
// ============================================
function ClientAvatar({ name, size = 'sm' }: { name: string; size?: 'sm' | 'lg' }) {
  const sizeClasses = size === 'lg' ? 'w-14 h-14 text-xl' : 'w-8 h-8 text-xs';

  // Generate consistent color based on first letter
  const colors = [
    'bg-blue-100 text-blue-600',
    'bg-purple-100 text-purple-600',
    'bg-green-100 text-green-600',
    'bg-orange-100 text-orange-600',
    'bg-teal-100 text-teal-600',
    'bg-pink-100 text-pink-600',
  ];
  const colorIndex = name.charCodeAt(0) % colors.length;

  return (
    <div className={`${sizeClasses} ${colors[colorIndex]} rounded-full flex items-center justify-center flex-shrink-0`}>
      <span className="font-semibold">{name.charAt(0).toUpperCase()}</span>
    </div>
  );
}

function TypeIcon({ type, failed = false }: { type: string; failed?: boolean }) {
  const bgColor = failed ? 'bg-red-100' :
    type === 'email' ? 'bg-purple-100' :
    type === 'sms' ? 'bg-green-100' : 'bg-emerald-100';

  const textColor = failed ? 'text-red-700' :
    type === 'email' ? 'text-purple-700' :
    type === 'sms' ? 'text-green-700' : 'text-emerald-700';

  const Icon = type === 'email' ? Mail : type === 'sms' ? Phone : MessageSquare;

  return (
    <span className={`w-6 h-6 ${bgColor} ${textColor} rounded flex items-center justify-center`}>
      <Icon className="w-3.5 h-3.5" />
    </span>
  );
}

function TypeBadge({ type }: { type: string }) {
  const colors = {
    email: 'bg-purple-100 text-purple-700',
    sms: 'bg-green-100 text-green-700',
    whatsapp: 'bg-emerald-100 text-emerald-700',
  };

  const labels = {
    email: 'Email',
    sms: 'SMS',
    whatsapp: 'WhatsApp',
  };

  const Icon = type === 'email' ? Mail : type === 'sms' ? Phone : MessageSquare;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${colors[type as keyof typeof colors] || 'bg-gray-100 text-gray-700'}`}>
      <Icon className="w-3.5 h-3.5" />
      {labels[type as keyof typeof labels] || type}
    </span>
  );
}

function LevelBadge({ level, small = false }: { level: number; small?: boolean }) {
  const colors = {
    1: 'bg-green-100 text-green-700',
    2: 'bg-yellow-100 text-yellow-700',
    3: 'bg-orange-100 text-orange-700',
    4: 'bg-red-100 text-red-700',
  };

  const sizeClasses = small ? 'w-5 h-5 text-[10px]' : 'w-7 h-7 text-xs';

  return (
    <span className={`inline-flex items-center justify-center ${sizeClasses} ${colors[level as keyof typeof colors] || 'bg-gray-100 text-gray-700'} rounded-lg font-bold`}>
      {level}
    </span>
  );
}

function StatusBadge({ status, large = false }: { status: string; large?: boolean }) {
  const isFailed = status === 'failed';

  const sizeClasses = large ? 'px-3 py-1.5 text-sm' : 'px-2 py-1 text-xs';

  if (isFailed) {
    return (
      <span className={`inline-flex items-center gap-1 ${sizeClasses} bg-red-100 text-red-700 rounded-full font-medium`}>
        <X className={large ? 'w-4 h-4' : 'w-3.5 h-3.5'} />
        Błąd
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center gap-1 ${sizeClasses} bg-green-50 text-green-700 rounded-full font-medium`}>
      <Check className={large ? 'w-4 h-4' : 'w-3.5 h-3.5'} />
      Wysłano
    </span>
  );
}
