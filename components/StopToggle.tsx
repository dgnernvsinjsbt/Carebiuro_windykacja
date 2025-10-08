'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import { useClientOperationLock } from '@/lib/client-operation-lock';

interface StopToggleProps {
  invoiceId: number;
  initialStop: boolean;
}

export default function StopToggle({ invoiceId, initialStop }: StopToggleProps) {
  const [isStop, setIsStop] = useState(initialStop);
  const [isUpdating, setIsUpdating] = useState(false);
  const { lockOperation, unlockOperation, isLocked } = useClientOperationLock();
  const router = useRouter();

  const toggleStop = async () => {
    const newValue = !isStop;

    // Try to acquire lock
    if (!lockOperation(`${newValue ? 'Włączanie' : 'Wyłączanie'} STOP dla faktury #${invoiceId}`)) {
      return; // Another operation is in progress
    }

    setIsUpdating(true);

    // Optimistic update
    setIsStop(newValue);

    const toastId = toast.loading(
      newValue ? 'Włączanie STOP...' : 'Wyłączanie STOP...'
    );

    try {
      const response = await fetch(`/api/invoice/${invoiceId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stop: newValue }),
      });

      const data = await response.json();

      if (data.success) {
        toast.success(
          newValue
            ? 'STOP włączony - przypomnienia zatrzymane'
            : 'STOP wyłączony - przypomnienia wznowione',
          { id: toastId }
        );
        // Odśwież dane z serwera (np. saldo klienta)
        router.refresh();
        setTimeout(() => unlockOperation(), 500);
      } else {
        // Revert on error
        setIsStop(!newValue);
        toast.error(`Błąd: ${data.error}`, { id: toastId });
        unlockOperation();
      }
    } catch (error: any) {
      // Revert on error
      setIsStop(!newValue);
      toast.error(`Błąd połączenia: ${error.message}`, { id: toastId });
      unlockOperation();
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <button
      onClick={toggleStop}
      disabled={isUpdating || isLocked}
      className={`
        relative inline-flex h-6 w-11 items-center rounded-full transition-colors
        ${isUpdating || isLocked ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        ${isStop ? 'bg-orange-500' : 'bg-gray-300'}
      `}
      title={isLocked ? 'Operacja w toku, proszę czekać...' : (isStop ? 'Kliknij aby wyłączyć STOP' : 'Kliknij aby włączyć STOP')}
    >
      <span
        className={`
          inline-block h-4 w-4 transform rounded-full bg-white transition-transform
          ${isStop ? 'translate-x-6' : 'translate-x-1'}
        `}
      />
    </button>
  );
}
