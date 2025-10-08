'use client';

import { useRouter } from 'next/navigation';
import { Client } from '@/types';

interface KaczmarskiClient extends Client {
  invoice_count?: number;
  total_debt?: number;
  earliest_sent_date?: string | null;
  days_overdue?: number;
}

interface KaczmarskiTableProps {
  clients: KaczmarskiClient[];
}

export default function KaczmarskiTable({ clients }: KaczmarskiTableProps) {
  const router = useRouter();

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('pl-PL', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
  };

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Klienci do listu poleconego
          </h2>
          <span className="text-sm text-gray-600">
            ({clients.length} klientów)
          </span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Klient
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                Ilość faktur
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Zadłużenie
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                List polecony
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                Email
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {clients.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                  Brak klientów do przekazania firmie windykacyjnej
                </td>
              </tr>
            ) : (
              clients.map((client) => (
                <tr
                  key={client.id}
                  onClick={() => router.push(`/client/${client.id}`)}
                  className="hover:bg-gray-50 transition-colors cursor-pointer"
                >
                  <td className="px-4 py-3">
                    <div>
                      <div className="font-medium text-gray-900">{client.name}</div>
                      <div className="text-sm text-gray-500">ID: {client.id}</div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {client.invoice_count || 0}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="font-semibold text-red-600">
                      €{(client.total_debt || 0).toFixed(2)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {formatDate(client.earliest_sent_date)}
                      </div>
                      {client.days_overdue && client.days_overdue > 0 && (
                        <div className="text-xs text-red-600">
                          ({client.days_overdue} dni temu)
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-sm text-gray-600">
                      {client.email || '-'}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
