'use client';

import { useState } from 'react';
import toast from 'react-hot-toast';
import { useClientOperationLock } from '@/lib/client-operation-lock';

interface WindykacjaToggleProps {
  clientId: number;
  initialWindykacja: boolean;
}

export default function WindykacjaToggle({ clientId, initialWindykacja }: WindykacjaToggleProps) {
  const [isWindykacja, setIsWindykacja] = useState(initialWindykacja);
  const [isUpdating, setIsUpdating] = useState(false);
  const { lockOperation, unlockOperation, isLocked } = useClientOperationLock();

  const toggleWindykacja = async () => {
    const newValue = !isWindykacja;

    // Try to acquire lock
    if (!lockOperation(newValue ? 'Włączanie WINDYKACJI' : 'Wyłączanie WINDYKACJI')) {
      return; // Another operation is in progress
    }

    setIsUpdating(true);

    // Optimistic update
    setIsWindykacja(newValue);

    const toastId = toast.loading(
      newValue ? 'Włączanie WINDYKACJI...' : 'Wyłączanie WINDYKACJI...'
    );

    try {
      const response = await fetch(`/api/client/${clientId}/windykacja`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ windykacja_enabled: newValue }),
      });

      const data = await response.json();

      if (data.success) {
        toast.success(
          newValue
            ? 'WINDYKACJA włączona - automatyczne przypomnienia aktywne dla wszystkich faktur klienta'
            : 'WINDYKACJA wyłączona - automatyczne przypomnienia zatrzymane dla wszystkich faktur klienta',
          { id: toastId }
        );

        // Synchronizuj dane klienta (pobierz note z Fakturowni)
        toast.loading('Synchronizacja danych klienta...', { id: 'sync' });

        const syncResponse = await fetch('/api/sync/client', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ client_id: clientId }),
        });

        const syncResult = await syncResponse.json();

        if (syncResult.success) {
          toast.success('Dane zsynchronizowane', { id: 'sync' });

          // If windykacja was ENABLED, auto-send S1 SMS to all eligible invoices
          // Auto-send fetches FRESH data directly from Fakturownia, so no need to wait
          if (newValue) {
            toast.loading('Wysyłanie automatycznych przypomnień S1...', { id: 'auto-send' });

            const autoSendResponse = await fetch('/api/windykacja/auto-send', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ client_id: clientId }),
            });

            const autoSendResult = await autoSendResponse.json();

            if (autoSendResult.success) {
              if (autoSendResult.sent > 0) {
                toast.success(
                  `✓ Wysłano ${autoSendResult.sent} SMS (S1) do ${autoSendResult.total} uprawnionych faktur`,
                  { id: 'auto-send', duration: 5000 }
                );
              } else {
                toast.success('Brak faktur wymagających wysłania SMS', { id: 'auto-send' });
              }
            } else {
              toast.error(`Błąd: ${autoSendResult.error}`, { id: 'auto-send' });
            }

            // Wait a bit before reload to show the success message
            await new Promise(resolve => setTimeout(resolve, 2000));
          }
        } else {
          toast.error('Błąd synchronizacji', { id: 'sync' });
        }

        // Refresh page to update data
        window.location.reload();
      } else {
        // Revert on error
        setIsWindykacja(!newValue);
        toast.error(`Błąd: ${data.error}`, { id: toastId });
      }
    } catch (error: any) {
      // Revert on error
      setIsWindykacja(!newValue);
      toast.error(`Błąd połączenia: ${error.message}`, { id: toastId });
    } finally {
      setIsUpdating(false);
      unlockOperation();
    }
  };

  return (
    <button
      onClick={toggleWindykacja}
      disabled={isUpdating || isLocked}
      className={`
        relative inline-flex h-6 w-11 items-center rounded-full transition-colors
        ${isUpdating || isLocked ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        ${isWindykacja ? 'bg-green-500' : 'bg-gray-300'}
      `}
      title={isLocked ? 'Operacja w toku, proszę czekać...' : (isWindykacja ? 'Kliknij aby wyłączyć WINDYKACJĘ (auto-przypomnienia)' : 'Kliknij aby włączyć WINDYKACJĘ (auto-przypomnienia)')}
    >
      <span
        className={`
          inline-block h-4 w-4 transform rounded-full bg-white transition-transform
          ${isWindykacja ? 'translate-x-6' : 'translate-x-1'}
        `}
      />
    </button>
  );
}
