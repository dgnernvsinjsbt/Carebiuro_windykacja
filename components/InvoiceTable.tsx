'use client';

import { useState } from 'react';
import { InvoiceWithClient } from '@/types';
import { format } from 'date-fns';
import ReminderButtons from './ReminderButtons';
import StopToggle from './StopToggle';

interface InvoiceTableProps {
  invoices: InvoiceWithClient[];
}

export default function InvoiceTable({ invoices }: InvoiceTableProps) {
  const [filter, setFilter] = useState<'all' | 'stop' | 'active'>('all');

  const filteredInvoices = invoices.filter(invoice => {
    if (filter === 'stop') return invoice.fiscal_sync?.STOP === true;
    if (filter === 'active') return invoice.fiscal_sync?.STOP !== true;
    return true;
  });

  if (invoices.length === 0) {
    return (
      <div className="p-8 text-center text-gray-500">
        <p className="text-lg">Brak nieopłaconych faktur</p>
        <p className="text-sm mt-2">
          Kliknij &quot;Synchronizuj dane&quot; aby pobrać faktury z Fakturowni
        </p>
      </div>
    );
  }

  return (
    <div>
      {/* Filters */}
      <div className="px-6 py-3 border-b border-gray-200 flex gap-2">
        <button
          onClick={() => setFilter('all')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            filter === 'all'
              ? 'bg-blue-100 text-blue-700'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Wszystkie ({invoices.length})
        </button>
        <button
          onClick={() => setFilter('active')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            filter === 'active'
              ? 'bg-green-100 text-green-700'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Aktywne ({invoices.filter(i => !i.fiscal_sync?.STOP).length})
        </button>
        <button
          onClick={() => setFilter('stop')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            filter === 'stop'
              ? 'bg-orange-100 text-orange-700'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          STOP ({invoices.filter(i => i.fiscal_sync?.STOP).length})
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Numer faktury
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Klient
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Kwota
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Opłacono
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Saldo
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Przypomnienia
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                STOP
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Akcje
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredInvoices.map((invoice) => (
              <tr key={invoice.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {invoice.number}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  <div>{invoice.client?.name || 'Nieznany klient'}</div>
                  <div className="text-xs text-gray-500">
                    {invoice.client?.email}
                  </div>
                </td>
                <td className={`px-6 py-4 whitespace-nowrap text-sm ${(() => {
                  const balance = (invoice.total ?? 0) - (invoice.paid ?? 0);
                  if (invoice.kind === 'canceled') return 'text-gray-300';
                  return balance > 0 ? 'text-gray-900 font-medium' : 'text-green-600';
                })()}`}>
                  €{invoice.total?.toFixed(2)}
                </td>
                <td className={`px-6 py-4 whitespace-nowrap text-sm ${(() => {
                  const balance = (invoice.total ?? 0) - (invoice.paid ?? 0);
                  if (invoice.kind === 'canceled') return 'text-gray-300';
                  return balance > 0 ? 'text-gray-900 font-medium' : 'text-green-600';
                })()}`}>
                  €{invoice.kind === 'canceled'
                    ? '0.00'
                    : (invoice.paid ?? 0).toFixed(2)}
                </td>
                <td className={`px-6 py-4 whitespace-nowrap text-sm ${(() => {
                  const balance = (invoice.total ?? 0) - (invoice.paid ?? 0);
                  if (invoice.kind === 'canceled') return 'text-gray-300';
                  return balance > 0 ? 'text-red-600 font-medium' : 'text-green-600';
                })()}`}>
                  €{(() => {
                    const balance = invoice.kind === 'canceled'
                      ? 0
                      : (invoice.total ?? 0) - (invoice.paid ?? 0);
                    return balance.toFixed(2);
                  })()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                    invoice.status === 'paid'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {invoice.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-600">
                  {invoice.fiscal_sync && (
                    <div className="space-y-1">
                      <div className="flex gap-2">
                        {invoice.fiscal_sync.EMAIL_1 && <span className="text-blue-600">✓ E1</span>}
                        {invoice.fiscal_sync.EMAIL_2 && <span className="text-blue-600">✓ E2</span>}
                        {invoice.fiscal_sync.EMAIL_3 && <span className="text-blue-600">✓ E3</span>}
                      </div>
                      <div className="flex gap-2">
                        {invoice.fiscal_sync.SMS_1 && <span className="text-green-600">✓ S1</span>}
                        {invoice.fiscal_sync.SMS_2 && <span className="text-green-600">✓ S2</span>}
                        {invoice.fiscal_sync.SMS_3 && <span className="text-green-600">✓ S3</span>}
                      </div>
                      <div className="flex gap-2">
                        {invoice.fiscal_sync.WHATSAPP_1 && <span className="text-purple-600">✓ W1</span>}
                        {invoice.fiscal_sync.WHATSAPP_2 && <span className="text-purple-600">✓ W2</span>}
                        {invoice.fiscal_sync.WHATSAPP_3 && <span className="text-purple-600">✓ W3</span>}
                      </div>
                    </div>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <StopToggle
                    invoiceId={invoice.id}
                    initialStop={invoice.fiscal_sync?.STOP || false}
                  />
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <ReminderButtons
                    invoiceId={invoice.id}
                    fiscalSync={invoice.fiscal_sync}
                    disabled={invoice.fiscal_sync?.STOP || false}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filteredInvoices.length === 0 && (
        <div className="p-8 text-center text-gray-500">
          <p>Brak faktur dla wybranego filtra</p>
        </div>
      )}
    </div>
  );
}
