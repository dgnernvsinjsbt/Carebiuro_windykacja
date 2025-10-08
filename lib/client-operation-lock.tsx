'use client';

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import toast from 'react-hot-toast';

interface ClientOperationLockContextType {
  isLocked: boolean;
  lockOperation: (operationName: string) => boolean;
  unlockOperation: () => void;
  currentOperation: string | null;
}

const ClientOperationLockContext = createContext<ClientOperationLockContextType | undefined>(undefined);

export function ClientOperationLockProvider({ children }: { children: ReactNode }) {
  const [isLocked, setIsLocked] = useState(false);
  const [currentOperation, setCurrentOperation] = useState<string | null>(null);

  const lockOperation = useCallback((operationName: string): boolean => {
    if (isLocked) {
      toast.error(`Operacja w toku: ${currentOperation}. Proszę czekać...`, {
        duration: 3000,
      });
      return false;
    }

    setIsLocked(true);
    setCurrentOperation(operationName);
    console.log(`[Lock] 🔒 Locked for operation: ${operationName}`);
    return true;
  }, [isLocked, currentOperation]);

  const unlockOperation = useCallback(() => {
    console.log(`[Lock] 🔓 Unlocked from operation: ${currentOperation}`);
    setIsLocked(false);
    setCurrentOperation(null);
  }, [currentOperation]);

  return (
    <ClientOperationLockContext.Provider
      value={{
        isLocked,
        lockOperation,
        unlockOperation,
        currentOperation,
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
