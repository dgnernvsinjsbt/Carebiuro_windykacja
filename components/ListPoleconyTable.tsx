'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Client } from '@/types';
import toast from 'react-hot-toast';

interface ListPoleconyClient extends Client {
  invoice_count?: number;
  total_debt?: number;
  qualifies_for_list_polecony?: boolean;
  earliest_sent_date?: string | null;
  days_overdue?: number;
}

interface ListPoleconyTableProps {
  clients: ListPoleconyClient[];
  hideGenerateButton?: boolean; // Opcjonalnie ukryj przycisk "Generuj dokumenty" (dla strony Wysłane)
  regenerateMode?: boolean; // Używa /regenerate endpoint (bez aktualizacji flag)
  showSentDate?: boolean; // Czy pokazywać kolumnę z datą wysłania
  showRestoreButton?: boolean; // Czy pokazywać przycisk "Przywróć" (dla strony Ignorowane)
}

export default function ListPoleconyTable({ clients, hideGenerateButton = false, regenerateMode = false, showSentDate = false, showRestoreButton = false }: ListPoleconyTableProps) {
  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('pl-PL', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
  };
  const router = useRouter();
  const [selectedClients, setSelectedClients] = useState<Set<number>>(new Set());
  const [isGenerating, setIsGenerating] = useState(false);
  const [isIgnoring, setIsIgnoring] = useState(false);
  const [isRestoring, setIsRestoring] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  const toggleClient = (clientId: number) => {
    setSelectedClients((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(clientId)) {
        newSet.delete(clientId);
      } else {
        newSet.add(clientId);
      }
      return newSet;
    });
  };

  const toggleAll = () => {
    if (selectedClients.size === clients.length) {
      setSelectedClients(new Set());
    } else {
      setSelectedClients(new Set(clients.map((c) => c.id)));
    }
  };

  const handleGenerate = async () => {
    if (selectedClients.size === 0) {
      toast.error('Wybierz co najmniej jednego klienta');
      return;
    }

    setIsGenerating(true);

    try {
      // Używaj różnych endpointów w zależności od trybu
      const endpoint = regenerateMode ? '/api/list-polecony/regenerate' : '/api/list-polecony/generate';

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          clientIds: Array.from(selectedClients),
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Błąd generowania dokumentów');
      }

      // Pobierz ZIP jako blob
      const blob = await response.blob();

      // Utwórz link do pobrania
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `list-polecony-${new Date().toISOString().split('T')[0]}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      toast.success(`Wygenerowano dokumenty dla ${selectedClients.size} klientów`);
      setSelectedClients(new Set()); // Wyczyść zaznaczenie

      // Odśwież dane z serwera
      router.refresh();
    } catch (error: any) {
      console.error('Błąd generowania:', error);
      toast.error(error.message || 'Błąd generowania dokumentów');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleIgnore = async () => {
    if (selectedClients.size === 0) {
      toast.error('Wybierz co najmniej jednego klienta');
      return;
    }

    if (!confirm(`Czy na pewno chcesz zignorować ${selectedClients.size} klientów?`)) {
      return;
    }

    setIsIgnoring(true);

    try {
      const response = await fetch('/api/list-polecony/ignore', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          clientIds: Array.from(selectedClients),
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Błąd ignorowania klientów');
      }

      const result = await response.json();

      toast.success(`Zignorowano ${selectedClients.size} klientów`);
      setSelectedClients(new Set()); // Wyczyść zaznaczenie

      // Odśwież dane z serwera
      router.refresh();
    } catch (error: any) {
      console.error('Błąd ignorowania:', error);
      toast.error(error.message || 'Błąd ignorowania klientów');
    } finally {
      setIsIgnoring(false);
    }
  };

  const handleRestore = async () => {
    if (selectedClients.size === 0) {
      toast.error('Wybierz co najmniej jednego klienta');
      return;
    }

    if (!confirm(`Czy na pewno chcesz przywrócić ${selectedClients.size} klientów?`)) {
      return;
    }

    setIsRestoring(true);

    try {
      const response = await fetch('/api/list-polecony/restore', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          clientIds: Array.from(selectedClients),
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Błąd przywracania klientów');
      }

      const result = await response.json();

      toast.success(`Przywrócono ${selectedClients.size} klientów`);
      setSelectedClients(new Set()); // Wyczyść zaznaczenie

      // Odśwież dane z serwera
      router.refresh();
    } catch (error: any) {
      console.error('Błąd przywracania:', error);
      toast.error(error.message || 'Błąd przywracania klientów');
    } finally {
      setIsRestoring(false);
    }
  };

  const handleSync = async () => {
    if (selectedClients.size === 0) {
      toast.error('Wybierz co najmniej jednego klienta');
      return;
    }

    setIsSyncing(true);

    try {
      // Synchronizuj każdego klienta osobno
      for (const clientId of Array.from(selectedClients)) {
        const response = await fetch('/api/list-polecony/sync-client', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ clientId }),
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || `Błąd synchronizacji klienta ${clientId}`);
        }
      }

      toast.success(`Zsynchronizowano ${selectedClients.size} klientów`);
      setSelectedClients(new Set()); // Wyczyść zaznaczenie

      // Odśwież dane z serwera
      router.refresh();
    } catch (error: any) {
      console.error('Błąd synchronizacji:', error);
      toast.error(error.message || 'Błąd synchronizacji klientów');
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Header z akcjami */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-semibold text-gray-900">
              Klienci do listu poleconego
            </h2>
            <span className="text-sm text-gray-600">
              ({clients.length} klientów)
            </span>
            {selectedClients.size > 0 && (
              <span className="text-sm font-medium text-teal-600">
                Zaznaczono: {selectedClients.size}
              </span>
            )}
          </div>

          <div className="flex items-center gap-3">
            {/* Przycisk Synchronizuj - na wszystkich zakładkach */}
            <button
              onClick={handleSync}
              disabled={selectedClients.size === 0 || isSyncing}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              {isSyncing ? (
                <>
                  <svg
                    className="animate-spin h-5 w-5 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  Synchronizowanie...
                </>
              ) : (
                <>
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                  Synchronizuj
                </>
              )}
            </button>

            {showRestoreButton && (
              <button
                onClick={handleRestore}
                disabled={selectedClients.size === 0 || isRestoring}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                {isRestoring ? (
                  <>
                    <svg
                      className="animate-spin h-5 w-5 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    Przywracanie...
                  </>
                ) : (
                  <>
                    <svg
                      className="w-5 h-5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"
                      />
                    </svg>
                    Przywróć
                  </>
                )}
              </button>
            )}
          </div>

          {!hideGenerateButton && (
            <div className="flex items-center gap-3">
              <button
                onClick={handleIgnore}
                disabled={selectedClients.size === 0 || isIgnoring}
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                {isIgnoring ? (
                  <>
                    <svg
                      className="animate-spin h-5 w-5 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    Ignorowanie...
                  </>
                ) : (
                  <>
                    <svg
                      className="w-5 h-5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
                      />
                    </svg>
                    Ignoruj
                  </>
                )}
              </button>

              <button
                onClick={handleGenerate}
                disabled={selectedClients.size === 0 || isGenerating}
                className="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                {isGenerating ? (
                  <>
                    <svg
                      className="animate-spin h-5 w-5 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    Generowanie...
                  </>
                ) : (
                  <>
                    <svg
                      className="w-5 h-5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                    Generuj dokumenty
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Tabela */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left w-12">
                <input
                  type="checkbox"
                  checked={selectedClients.size === clients.length && clients.length > 0}
                  onChange={toggleAll}
                  className="w-4 h-4 text-teal-600 border-gray-300 rounded focus:ring-teal-500"
                />
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Klient
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                Ilość faktur
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Zadłużenie
              </th>
              {showSentDate && (
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  List polecony
                </th>
              )}
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                Email
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {clients.length === 0 ? (
              <tr>
                <td colSpan={showSentDate ? 6 : 5} className="px-6 py-8 text-center text-gray-500">
                  Brak klientów kwalifikujących się do listu poleconego
                </td>
              </tr>
            ) : (
              clients.map((client) => (
                <tr
                  key={client.id}
                  className={`hover:bg-gray-50 transition-colors ${
                    selectedClients.has(client.id) ? 'bg-teal-50' : ''
                  }`}
                >
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedClients.has(client.id)}
                      onChange={() => toggleClient(client.id)}
                      className="w-4 h-4 text-teal-600 border-gray-300 rounded focus:ring-teal-500"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm font-medium text-gray-900">
                      {client.name || 'Brak nazwy'}
                    </div>
                    <div className="text-xs text-gray-500">ID: {client.id}</div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-sm text-gray-600">
                      {client.invoice_count || 0}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="text-sm font-semibold text-red-600">
                      €{(client.total_debt || 0).toFixed(2)}
                    </span>
                  </td>
                  {showSentDate && (
                    <td className="px-4 py-3 text-center">
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {formatDate(client.earliest_sent_date)}
                        </div>
                        {client.days_overdue && client.days_overdue > 0 && (
                          <div className="text-xs text-gray-500">
                            ({client.days_overdue} dni temu)
                          </div>
                        )}
                      </div>
                    </td>
                  )}
                  <td className="px-4 py-3 text-center">
                    <span className="text-xs text-gray-600">
                      {client.email || '-'}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      {clients.length > 0 && (
        <div className="px-6 py-3 border-t border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">
              Łącznie {clients.length} klientów kwalifikuje się do listu poleconego
            </div>
            {selectedClients.size > 0 && (
              <button
                onClick={() => setSelectedClients(new Set())}
                className="text-sm text-gray-600 hover:text-gray-900 underline"
              >
                Wyczyść zaznaczenie
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
