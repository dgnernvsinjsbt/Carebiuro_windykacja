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
  const { lockClientOperation, unlockClientOperation, isClientLocked } = useClientOperationLock();

  const toggleWindykacja = async () => {
    const newValue = !isWindykacja;

    // Per-client lock - nie blokuje innych klientów
    if (!lockClientOperation(clientId, newValue ? 'Włączanie' : 'Wyłączanie')) {
      return;
    }

    setIsUpdating(true);

    try {
      const response = await fetch(`/api/client/${clientId}/windykacja`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ windykacja_enabled: newValue }),
      });

      const data = await response.json();

      if (data.success) {
        // SUKCES - zmiana UI po potwierdzeniu serwera
        setIsWindykacja(newValue);
        toast.success(newValue ? '✓ Włączona' : '✓ Wyłączona', { duration: 1500 });
      } else {
        toast.error(`Błąd: ${data.error}`, { duration: 4000 });
      }
    } catch (error: any) {
      toast.error('Błąd połączenia', { duration: 4000 });
    } finally {
      setIsUpdating(false);
      unlockClientOperation(clientId);
    }
  };

  const isLocked = isClientLocked(clientId);

  return (
    <button
      onClick={toggleWindykacja}
      disabled={isUpdating || isLocked}
      className={`
        relative inline-flex h-6 w-11 items-center rounded-full transition-colors
        ${isUpdating || isLocked ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        ${isWindykacja ? 'bg-green-500' : 'bg-gray-300'}
      `}
      title={isLocked ? 'Zapisywanie...' : (isWindykacja ? 'Wyłącz windykację' : 'Włącz windykację')}
    >
      <span
        className={`
          inline-block h-4 w-4 transform rounded-full bg-white transition-transform
          ${isWindykacja ? 'translate-x-6' : 'translate-x-1'}
        `}
      />
      {isUpdating && (
        <span className="absolute inset-0 flex items-center justify-center">
          <span className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
        </span>
      )}
    </button>
  );
}
