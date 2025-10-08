'use client';

import { useClientOperationLock } from '@/lib/client-operation-lock';

export default function OperationStatusBanner() {
  const { isLocked, currentOperation } = useClientOperationLock();

  if (!isLocked || !currentOperation) {
    return null;
  }

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-blue-600 text-white px-4 py-3 shadow-lg">
      <div className="max-w-7xl mx-auto flex items-center justify-center gap-3">
        <svg
          className="animate-spin h-5 w-5"
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
        <span className="font-medium">{currentOperation}...</span>
        <span className="text-blue-200 text-sm">Proszę czekać</span>
      </div>
    </div>
  );
}
