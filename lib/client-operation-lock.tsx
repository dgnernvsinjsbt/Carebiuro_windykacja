'use client';

import { createContext, useContext, useState, useCallback, ReactNode, useEffect } from 'react';
import toast from 'react-hot-toast';

interface LockedClient {
  operation: string;
  timestamp: number;
}

interface ClientOperationLockContextType {
  // Globalny lock (dla kompatybilności ze StopToggle)
  isLocked: boolean;
  lockOperation: (operationName: string) => boolean;
  unlockOperation: () => void;
  currentOperation: string | null;
  // Per-client lock (dla WindykacjaToggle)
  lockClientOperation: (clientId: number, operationName: string) => boolean;
  unlockClientOperation: (clientId: number) => void;
  isClientLocked: (clientId: number) => boolean;
}

const ClientOperationLockContext = createContext<ClientOperationLockContextType | undefined>(undefined);

const LOCK_TIMEOUT_MS = 60000; // Auto-cleanup po 60s

export function ClientOperationLockProvider({ children }: { children: ReactNode }) {
  // Globalny lock (dla StopToggle - kompatybilność wsteczna)
  const [isLocked, setIsLocked] = useState(false);
  const [currentOperation, setCurrentOperation] = useState<string | null>(null);

  // Per-client lock (dla WindykacjaToggle)
  const [lockedClients, setLockedClients] = useState<Map<number, LockedClient>>(new Map());

  // Auto-cleanup starych locków (zabezpieczenie)
  useEffect(() => {
    const interval = setInterval(() => {
      setLockedClients(prev => {
        const now = Date.now();
        const next = new Map(prev);
        let cleaned = false;

        // Użyj forEach zamiast for...of dla kompatybilności
        prev.forEach((lock, clientId) => {
          if (now - lock.timestamp > LOCK_TIMEOUT_MS) {
            console.log(`[Lock] ⏰ Auto-cleanup stale lock for client ${clientId}`);
            next.delete(clientId);
            cleaned = true;
          }
        });

        return cleaned ? next : prev;
      });
    }, 10000); // Check co 10s

    return () => clearInterval(interval);
  }, []);

  // === GLOBALNY LOCK (kompatybilność ze StopToggle) ===
  const lockOperation = useCallback((operationName: string): boolean => {
    if (isLocked) {
      toast.error(`Operacja w toku: ${currentOperation}. Proszę czekać...`, {
        duration: 3000,
      });
      return false;
    }

    setIsLocked(true);
    setCurrentOperation(operationName);
    console.log(`[Lock] 🔒 Global locked for: ${operationName}`);
    return true;
  }, [isLocked, currentOperation]);

  const unlockOperation = useCallback(() => {
    console.log(`[Lock] 🔓 Global unlocked from: ${currentOperation}`);
    setIsLocked(false);
    setCurrentOperation(null);
  }, [currentOperation]);

  // === PER-CLIENT LOCK (dla WindykacjaToggle) ===
  const lockClientOperation = useCallback((clientId: number, operationName: string): boolean => {
    if (lockedClients.has(clientId)) {
      const existing = lockedClients.get(clientId);
      toast.error(`Operacja w toku dla tego klienta: ${existing?.operation}. Proszę czekać...`, {
        duration: 3000,
      });
      return false;
    }

    setLockedClients(prev => new Map(prev).set(clientId, {
      operation: operationName,
      timestamp: Date.now()
    }));
    console.log(`[Lock] 🔒 Client ${clientId} locked for: ${operationName}`);
    return true;
  }, [lockedClients]);

  const unlockClientOperation = useCallback((clientId: number) => {
    setLockedClients(prev => {
      const next = new Map(prev);
      const existing = next.get(clientId);
      console.log(`[Lock] 🔓 Client ${clientId} unlocked from: ${existing?.operation}`);
      next.delete(clientId);
      return next;
    });
  }, []);

  const isClientLocked = useCallback((clientId: number): boolean => {
    return lockedClients.has(clientId);
  }, [lockedClients]);

  return (
    <ClientOperationLockContext.Provider
      value={{
        // Globalny lock
        isLocked,
        lockOperation,
        unlockOperation,
        currentOperation,
        // Per-client lock
        lockClientOperation,
        unlockClientOperation,
        isClientLocked,
      }}
    >
      {children}
    </ClientOperationLockContext.Provider>
  );
}

export function useClientOperationLock() {
  const context = useContext(ClientOperationLockContext);
  if (!context) {
    throw new Error('useClientOperationLock must be used within ClientOperationLockProvider');
  }
  return context;
}
