import type { Metadata } from 'next';
import { Toaster } from 'react-hot-toast';
import { ClientOperationLockProvider } from '@/lib/client-operation-lock';
import './globals.css';

export const metadata: Metadata = {
  title: 'Carebiuro Windykacja - System Przypomnień',
  description: 'System zarządzania windykacją i przypomnieniami o nieopłaconych fakturach',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pl">
      <body>
        <ClientOperationLockProvider>
          {children}
        </ClientOperationLockProvider>
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#363636',
              color: '#fff',
            },
            success: {
              duration: 3000,
              iconTheme: {
                primary: '#10b981',
                secondary: '#fff',
              },
            },
            error: {
              duration: 5000,
              iconTheme: {
                primary: '#ef4444',
                secondary: '#fff',
              },
            },
          }}
        />
      </body>
    </html>
  );
}
