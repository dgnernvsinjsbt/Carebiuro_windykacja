'use client';

import { useState, useMemo } from 'react';
import { InvoiceWithClient } from '@/types';
import ProgressiveReminderButtons from './ProgressiveReminderButtons';
import StopToggle from './StopToggle';
import toast from 'react-hot-toast';

interface ClientInvoicesTableProps {
  invoices: InvoiceWithClient[];
  clientPhone?: string;
  windykacjaEnabled: boolean;
}

type SortDirection = 'asc' | 'desc';

export default function ClientInvoicesTable({
  invoices,
  clientPhone,
  windykacjaEnabled,
}: ClientInvoicesTableProps) {
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [selectedInvoices, setSelectedInvoices] = useState<Set<number>>(new Set());
  const [isCreatingInvoice, setIsCreatingInvoice] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  const sortedInvoices = useMemo(() => {
    return [...invoices].sort((a, b) => {
      const dateA = a.issue_date ? new Date(a.issue_date).getTime() : 0;
      const dateB = b.issue_date ? new Date(b.issue_date).getTime() : 0;

      return sortDirection === 'desc' ? dateB - dateA : dateA - dateB;
    });
  }, [invoices, sortDirection]);

  const toggleSort = () => {
    setSortDirection((prev) => (prev === 'desc' ? 'asc' : 'desc'));
  };

  const toggleInvoiceSelection = (invoiceId: number) => {
    setSelectedInvoices((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(invoiceId)) {
        newSet.delete(invoiceId);
      } else {
        newSet.add(invoiceId);
      }
      return newSet;
    });
  };

  const toggleAllUnpaid = () => {
    const unpaidInvoices = sortedInvoices.filter((inv) => {
      // Exclude corrective invoices (FK prefix) from selection
      const isCorrectiveInvoice = inv.number && inv.number.startsWith('FK');
      const balance = (inv.total ?? 0) - (inv.paid ?? 0);
      return balance > 0 && inv.kind !== 'canceled' && !isCorrectiveInvoice;
    });

    if (selectedInvoices.size === unpaidInvoices.length) {
      // Deselect all
      setSelectedInvoices(new Set());
    } else {
      // Select all unpaid
      setSelectedInvoices(new Set(unpaidInvoices.map((inv) => inv.id)));
    }
  };

  const syncClientInvoices = async () => {
    // Get client_id from first invoice
    const firstInvoice = invoices[0];
    if (!firstInvoice?.client_id) {
      toast.error('Nie można określić klienta');
      return;
    }

    setIsSyncing(true);

    try {
      const response = await fetch('/api/sync/client', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: firstInvoice.client_id,
        }),
      });

      const result = await response.json();

      if (result.success) {
        toast.success(`Zsynchronizowano ${result.data.synced_invoices} faktur`);
        // Refresh page to show updated data
        setTimeout(() => {
          window.location.reload();
        }, 1000);
      } else {
        toast.error(result.error || 'Nie udało się zsynchronizować faktur');
      }
    } catch (error) {
      console.error('Error syncing invoices:', error);
      toast.error('Błąd podczas synchronizacji faktur');
    } finally {
      setIsSyncing(false);
    }
  };

  const createCollectiveInvoice = async () => {
    if (selectedInvoices.size === 0) {
      toast.error('Wybierz faktury do wystawienia faktury zbiorczej');
      return;
    }

    // Get client_id from first invoice
    const firstInvoice = invoices.find((inv) => selectedInvoices.has(inv.id));
    if (!firstInvoice?.client_id) {
      toast.error('Nie można określić klienta');
      return;
    }

    setIsCreatingInvoice(true);

    try {
      // STEP 1 & 2: Create collective invoice and cancel selected invoices
      const response = await fetch('/api/invoices/collective', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          invoice_ids: Array.from(selectedInvoices),
          client_id: firstInvoice.client_id,
        }),
      });

      const result = await response.json();

      if (!result.success) {
        toast.error(result.error || 'Nie udało się utworzyć faktury zbiorczej');
        return;
      }

      toast.success(`Faktura zbiorcza ${result.data.invoice_number} została utworzona`);

      // Open invoice in new tab
      if (result.data.view_url) {
        window.open(result.data.view_url, '_blank');
      }

      // Wait for Fakturownia to process cancellations (API can be slow)
      toast.loading('Oczekiwanie na przetworzenie anulowań...', { id: 'sync' });
      await new Promise(resolve => setTimeout(resolve, 1000));

      // STEP 3 & 4: Sync all invoices for this client (delete + fetch fresh)
      toast.loading('Synchronizacja faktur...', { id: 'sync' });

      const syncResponse = await fetch('/api/sync/client', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: result.data.client_id,
        }),
      });

      const syncResult = await syncResponse.json();

      if (syncResult.success) {
        toast.success(`Zsynchronizowano ${syncResult.data.synced_invoices} faktur`, { id: 'sync' });
      } else {
        toast.error('Błąd synchronizacji', { id: 'sync' });
      }

      // Clear selection
      setSelectedInvoices(new Set());

      // STEP 5: Refresh page
      setTimeout(() => {
        window.location.reload();
      }, 1000);

    } catch (error) {
      console.error('Error creating collective invoice:', error);
      toast.error('Błąd podczas tworzenia faktury zbiorczej');
    } finally {
      setIsCreatingInvoice(false);
    }
  };

  if (invoices.length === 0) {
    return (
      <div className="p-8 text-center text-gray-500">
        <p>Brak faktur dla tego klienta</p>
      </div>
    );
  }

  return (
    <div>
      {/* Collective Invoice Button */}
      <div className={`mb-4 px-6 py-3 rounded-lg flex items-center justify-between ${
        selectedInvoices.size > 0
          ? 'bg-blue-50 border border-blue-200'
          : 'bg-gray-50 border border-gray-200'
      }`}>
        <div className={`text-sm ${
          selectedInvoices.size > 0 ? 'text-blue-800' : 'text-gray-500'
        }`}>
          {selectedInvoices.size > 0 ? (
            <>
              <span className="font-semibold">{selectedInvoices.size}</span> {selectedInvoices.size === 1 ? 'faktura zaznaczona' : 'faktury zaznaczone'}
            </>
          ) : (
            'Zaznacz faktury, aby wystawić fakturę zbiorczą'
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={syncClientInvoices}
            disabled={isSyncing}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${
              isSyncing
                ? 'bg-gray-400 text-white cursor-not-allowed'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
            title="Odśwież listę faktur z Fakturowni"
          >
            {isSyncing ? 'Synchronizacja...' : 'Odśwież'}
          </button>
          <button
            onClick={createCollectiveInvoice}
            disabled={isCreatingInvoice || selectedInvoices.size === 0}
            className={`px-4 py-2 rounded-md font-medium text-white transition-colors ${
              isCreatingInvoice || selectedInvoices.size === 0
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {isCreatingInvoice ? 'Tworzenie...' : 'Wystaw fakturę zbiorczą'}
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
              <input
                type="checkbox"
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 cursor-pointer"
                onChange={toggleAllUnpaid}
                checked={selectedInvoices.size > 0 && selectedInvoices.size === sortedInvoices.filter((inv) => {
                  const isCorrectiveInvoice = inv.number && inv.number.startsWith('FK');
                  const balance = (inv.total ?? 0) - (inv.paid ?? 0);
                  return balance > 0 && inv.kind !== 'canceled' && !isCorrectiveInvoice;
                }).length}
                title="Zaznacz wszystkie nieopłacone"
              />
            </th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Numer faktury
            </th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              <button
                onClick={toggleSort}
                className="flex items-center gap-1 hover:text-gray-700 transition-colors"
                title={`Sortuj ${sortDirection === 'desc' ? 'rosnąco' : 'malejąco'}`}
              >
                Data wystawienia
                <span className="text-xs">
                  {sortDirection === 'desc' ? '↓' : '↑'}
                </span>
              </button>
            </th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Kwota
            </th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Opłacono
            </th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Saldo
            </th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Przypomnienia
            </th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              STOP
            </th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Akcje
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {sortedInvoices.map((invoice) => {
            // Corrective invoices (FK prefix) are never considered "unpaid"
            const isCorrectiveInvoice = invoice.number && invoice.number.startsWith('FK');
            const balance = (invoice.total ?? 0) - (invoice.paid ?? 0);
            const isUnpaid = balance > 0 && invoice.kind !== 'canceled' && !isCorrectiveInvoice;

            return (
              <tr key={invoice.id} className={`hover:bg-gray-50 ${selectedInvoices.has(invoice.id) ? 'bg-blue-50' : ''}`}>
                <td className="px-3 py-2 whitespace-nowrap text-center">
                  {isUnpaid ? (
                    <input
                      type="checkbox"
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 cursor-pointer"
                      checked={selectedInvoices.has(invoice.id)}
                      onChange={() => toggleInvoiceSelection(invoice.id)}
                    />
                  ) : (
                    <span className="text-gray-300">-</span>
                  )}
                </td>
                <td className="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
                <div className="flex items-center gap-1">
                  {invoice.kind === 'canceled' && (
                    <span className="text-red-500" title="Faktura anulowana">⛔</span>
                  )}
                  {invoice.kind === 'correction' && (
                    <span className="text-gray-500" title="Faktura korygująca">🔄</span>
                  )}
                  {invoice.number}
                </div>
              </td>
              <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-600">
                {invoice.issue_date
                  ? new Date(invoice.issue_date).toLocaleDateString('pl-PL', {
                      year: 'numeric',
                      month: '2-digit',
                      day: '2-digit',
                    })
                  : '-'}
              </td>
              <td className={`px-3 py-2 whitespace-nowrap text-sm ${(() => {
                const balance = (invoice.total ?? 0) - (invoice.paid ?? 0);
                if (invoice.kind === 'canceled') return 'text-gray-300';
                return balance > 0 ? 'text-gray-900 font-medium' : 'text-green-600';
              })()}`}>
                €{invoice.total?.toFixed(2)}
              </td>
              <td className={`px-3 py-2 whitespace-nowrap text-sm ${(() => {
                const balance = (invoice.total ?? 0) - (invoice.paid ?? 0);
                if (invoice.kind === 'canceled') return 'text-gray-300';
                return balance > 0 ? 'text-gray-900 font-medium' : 'text-green-600';
              })()}`}>
                €{invoice.kind === 'canceled'
                  ? '0.00'
                  : (invoice.paid ?? 0).toFixed(2)}
              </td>
              <td className={`px-3 py-2 whitespace-nowrap text-sm ${(() => {
                // Corrective invoices (FK prefix) should show €0.00
                const isCorrectiveInvoice = invoice.number && invoice.number.startsWith('FK');
                if (isCorrectiveInvoice) return 'text-gray-400';

                const balance = (invoice.total ?? 0) - (invoice.paid ?? 0);
                if (invoice.kind === 'canceled') return 'text-gray-300';
                return balance > 0 ? 'text-red-600 font-medium' : 'text-green-600';
              })()}`}>
                €{(() => {
                  // Corrective invoices (FK prefix) always show €0.00
                  const isCorrectiveInvoice = invoice.number && invoice.number.startsWith('FK');
                  if (isCorrectiveInvoice) return '0.00';

                  const balance = invoice.kind === 'canceled'
                    ? 0
                    : (invoice.total ?? 0) - (invoice.paid ?? 0);
                  return balance.toFixed(2);
                })()}
              </td>
              <td className="px-3 py-2">
                <div className="flex gap-1 flex-wrap">
                  {/* Handle sent_error status - show red E1 badge */}
                  {invoice.email_status === 'sent_error' && invoice.sent_time && (
                    <span
                      className="px-2 py-1 text-xs font-medium rounded bg-red-500 text-white cursor-default"
                      title={`Wysłano: ${new Date(invoice.sent_time).toLocaleDateString('pl-PL', { year: 'numeric', month: '2-digit', day: '2-digit' })}\nEmail nie istnieje`}
                    >
                      E1
                    </span>
                  )}

                  {/* Normal EMAIL_1 from fiscal_sync (when not sent_error) */}
                  {invoice.fiscal_sync && invoice.fiscal_sync.EMAIL_1 && invoice.email_status !== 'sent_error' && (
                    <span
                      className="px-2 py-1 text-xs font-medium rounded bg-blue-500 text-white cursor-default"
                      title={invoice.fiscal_sync.EMAIL_1_DATE ? `Wysłano: ${new Date(invoice.fiscal_sync.EMAIL_1_DATE).toLocaleDateString('pl-PL', { year: 'numeric', month: '2-digit', day: '2-digit' })}` : 'Wysłano'}
                    >
                      E1
                    </span>
                  )}

                  {invoice.fiscal_sync && (
                    <>
                    {invoice.fiscal_sync.EMAIL_2 && (
                      <span
                        className="px-2 py-1 text-xs font-medium rounded bg-blue-600 text-white cursor-default"
                        title={invoice.fiscal_sync.EMAIL_2_DATE ? `Wysłano: ${new Date(invoice.fiscal_sync.EMAIL_2_DATE).toLocaleDateString('pl-PL', { year: 'numeric', month: '2-digit', day: '2-digit' })}` : 'Wysłano'}
                      >
                        E2
                      </span>
                    )}
                    {invoice.fiscal_sync.EMAIL_3 && (
                      <span
                        className="px-2 py-1 text-xs font-medium rounded bg-blue-700 text-white cursor-default"
                        title={invoice.fiscal_sync.EMAIL_3_DATE ? `Wysłano: ${new Date(invoice.fiscal_sync.EMAIL_3_DATE).toLocaleDateString('pl-PL', { year: 'numeric', month: '2-digit', day: '2-digit' })}` : 'Wysłano'}
                      >
                        E3
                      </span>
                    )}
                    {invoice.fiscal_sync.SMS_1 && (
                      <span
                        className="px-2 py-1 text-xs font-medium rounded bg-purple-500 text-white cursor-default"
                        title={invoice.fiscal_sync.SMS_1_DATE ? `Wysłano: ${new Date(invoice.fiscal_sync.SMS_1_DATE).toLocaleDateString('pl-PL', { year: 'numeric', month: '2-digit', day: '2-digit' })}` : 'Wysłano'}
                      >
                        S1
                      </span>
                    )}
                    {invoice.fiscal_sync.SMS_2 && (
                      <span
                        className="px-2 py-1 text-xs font-medium rounded bg-purple-600 text-white cursor-default"
                        title={invoice.fiscal_sync.SMS_2_DATE ? `Wysłano: ${new Date(invoice.fiscal_sync.SMS_2_DATE).toLocaleDateString('pl-PL', { year: 'numeric', month: '2-digit', day: '2-digit' })}` : 'Wysłano'}
                      >
                        S2
                      </span>
                    )}
                    {invoice.fiscal_sync.SMS_3 && (
                      <span
                        className="px-2 py-1 text-xs font-medium rounded bg-purple-700 text-white cursor-default"
                        title={invoice.fiscal_sync.SMS_3_DATE ? `Wysłano: ${new Date(invoice.fiscal_sync.SMS_3_DATE).toLocaleDateString('pl-PL', { year: 'numeric', month: '2-digit', day: '2-digit' })}` : 'Wysłano'}
                      >
                        S3
                      </span>
                    )}
                    {invoice.fiscal_sync.WHATSAPP_1 && (
                      <span
                        className="px-2 py-1 text-xs font-medium rounded bg-green-500 text-white cursor-default"
                        title={invoice.fiscal_sync.WHATSAPP_1_DATE ? `Wysłano: ${new Date(invoice.fiscal_sync.WHATSAPP_1_DATE).toLocaleDateString('pl-PL', { year: 'numeric', month: '2-digit', day: '2-digit' })}` : 'Wysłano'}
                      >
                        W1
                      </span>
                    )}
                    {invoice.fiscal_sync.WHATSAPP_2 && (
                      <span
                        className="px-2 py-1 text-xs font-medium rounded bg-green-600 text-white cursor-default"
                        title={invoice.fiscal_sync.WHATSAPP_2_DATE ? `Wysłano: ${new Date(invoice.fiscal_sync.WHATSAPP_2_DATE).toLocaleDateString('pl-PL', { year: 'numeric', month: '2-digit', day: '2-digit' })}` : 'Wysłano'}
                      >
                        W2
                      </span>
                    )}
                    {invoice.fiscal_sync.WHATSAPP_3 && (
                      <span
                        className="px-2 py-1 text-xs font-medium rounded bg-green-700 text-white cursor-default"
                        title={invoice.fiscal_sync.WHATSAPP_3_DATE ? `Wysłano: ${new Date(invoice.fiscal_sync.WHATSAPP_3_DATE).toLocaleDateString('pl-PL', { year: 'numeric', month: '2-digit', day: '2-digit' })}` : 'Wysłano'}
                      >
                        W3
                      </span>
                    )}
                    </>
                  )}
                </div>
              </td>
              <td className="px-3 py-2 whitespace-nowrap">
                {invoice.status === 'paid' || invoice.kind === 'canceled' || isCorrectiveInvoice ? (
                  <span className="text-gray-400 text-xs">-</span>
                ) : (
                  <StopToggle
                    invoiceId={invoice.id}
                    initialStop={invoice.fiscal_sync?.STOP || false}
                  />
                )}
              </td>
              <td className="px-3 py-2 whitespace-nowrap text-sm">
                {invoice.status === 'paid' || invoice.kind === 'canceled' || isCorrectiveInvoice ? (
                  <span className="text-gray-400 text-xs">-</span>
                ) : (
                  <ProgressiveReminderButtons
                    invoiceId={invoice.id}
                    fiscalSync={invoice.fiscal_sync}
                    disabled={invoice.fiscal_sync?.STOP || false}
                    clientPhone={clientPhone}
                    windykacjaEnabled={windykacjaEnabled}
                  />
                )}
              </td>
            </tr>
          );
          })}
        </tbody>
      </table>
      </div>
    </div>
  );
}
