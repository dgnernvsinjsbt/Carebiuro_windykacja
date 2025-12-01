'use client';

import { useState, useEffect, useCallback } from 'react';
import { Client } from '@/types';
import WindykacjaToggle from './WindykacjaToggle';
import { parseWindykacja } from '@/lib/windykacja-parser';

interface ClientHeaderProps {
  client: Client;
  unpaidBalance?: number;
}

export default function ClientHeader({ client, unpaidBalance }: ClientHeaderProps) {
  const [loadingDetails, setLoadingDetails] = useState(true);
  const [clientDetails, setClientDetails] = useState<{
    email?: string;
    phone?: string;
  }>({});

  // Lokalny stan windykacji - aktualizuje się natychmiast po zmianie toggle
  const [windykacjaEnabled, setWindykacjaEnabled] = useState(() => parseWindykacja(client.note));

  // Sync z props gdy klient się zmieni (np. nawigacja)
  useEffect(() => {
    setWindykacjaEnabled(parseWindykacja(client.note));
  }, [client.note]);

  // Callback dla WindykacjaToggle - aktualizuje label natychmiast
  const handleWindykacjaChange = useCallback((_clientId: number, newValue: boolean) => {
    setWindykacjaEnabled(newValue);
  }, []);

  useEffect(() => {
    // Fetch client details from Fakturownia in the background
    async function fetchClientDetails() {
      try {
        const response = await fetch(`/api/client/${client.id}`);
        if (response.ok) {
          const data = await response.json();
          setClientDetails({
            email: data.email,
            phone: data.phone,
          });
        }
      } catch (error) {
        console.error('Failed to fetch client details:', error);
      } finally {
        setLoadingDetails(false);
      }
    }

    fetchClientDetails();
  }, [client.id]);

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-gray-900">
          {client.name}
        </h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-600">
            {windykacjaEnabled ? (
              <span className="text-green-600 font-medium">✓ Windykacja aktywna</span>
            ) : (
              <span className="text-gray-400">Windykacja wyłączona</span>
            )}
          </span>
          <WindykacjaToggle
            clientId={client.id}
            initialWindykacja={windykacjaEnabled}
            onWindykacjaChange={handleWindykacjaChange}
          />
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
        <div>
          <span className="text-gray-500">Email:</span>{' '}
          {loadingDetails ? (
            <span className="inline-flex items-center gap-1 text-gray-400">
              <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Ładowanie...
            </span>
          ) : (
            <span className="text-gray-900">{clientDetails.email || '-'}</span>
          )}
        </div>
        <div>
          <span className="text-gray-500">Telefon:</span>{' '}
          {loadingDetails ? (
            <span className="inline-flex items-center gap-1 text-gray-400">
              <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Ładowanie...
            </span>
          ) : (
            <span className="text-gray-900">{clientDetails.phone || '-'}</span>
          )}
        </div>
        <div>
          <span className="text-gray-500">Saldo nieopłacone:</span>{' '}
          <span
            className={`font-semibold ${
              (unpaidBalance ?? client.total_unpaid ?? 0) > 0
                ? 'text-red-600'
                : 'text-green-600'
            }`}
          >
            €{(unpaidBalance ?? client.total_unpaid ?? 0).toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  );
}
