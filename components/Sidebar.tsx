'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';
import toast from 'react-hot-toast';

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const handleLogout = async () => {
    if (isLoggingOut) return;

    setIsLoggingOut(true);

    try {
      const response = await fetch('/api/auth/logout', {
        method: 'POST',
      });

      if (response.ok) {
        toast.success('Wylogowano pomyślnie');
        router.push('/login');
        router.refresh();
      } else {
        toast.error('Błąd podczas wylogowania');
      }
    } catch (error) {
      console.error('Logout error:', error);
      toast.error('Błąd połączenia z serwerem');
    } finally {
      setIsLoggingOut(false);
    }
  };

  return (
    <div className="w-64 bg-white border-r border-gray-200 min-h-screen flex flex-col relative">
      {/* Logo */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-teal-600 rounded-lg flex items-center justify-center text-white font-bold text-xl">
            C
          </div>
          <div>
            <div className="font-bold text-gray-900">CAREBIURO</div>
            <div className="text-xs text-gray-500">Windykacja</div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="p-4 space-y-1">
        <Link
          href="/"
          className={`
            flex items-center gap-3 px-4 py-3 rounded-lg transition-colors
            ${
              pathname === '/'
                ? 'bg-teal-50 text-teal-700 font-medium'
                : 'text-gray-700 hover:bg-gray-50'
            }
          `}
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
            />
          </svg>
          Klienci
        </Link>

        <Link
          href="/historia"
          className={`
            flex items-center gap-3 px-4 py-3 rounded-lg transition-colors
            ${
              pathname === '/historia'
                ? 'bg-teal-50 text-teal-700 font-medium'
                : 'text-gray-700 hover:bg-gray-50'
            }
          `}
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          Historia
        </Link>

        <Link
          href="/list-polecony"
          className={`
            flex items-center gap-3 px-4 py-3 rounded-lg transition-colors
            ${
              pathname?.startsWith('/list-polecony')
                ? 'bg-teal-50 text-teal-700 font-medium'
                : 'text-gray-700 hover:bg-gray-50'
            }
          `}
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          List Polecony
        </Link>

        <Link
          href="/kaczmarski"
          className={`
            flex items-center gap-3 px-4 py-3 rounded-lg transition-colors
            ${
              pathname === '/kaczmarski'
                ? 'bg-red-50 text-red-700 font-medium'
                : 'text-gray-700 hover:bg-gray-50'
            }
          `}
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          Kaczmarski
        </Link>

        {/* Divider */}
        <div className="my-2 border-t border-gray-200"></div>

        <Link
          href="/szablony"
          className={`
            flex items-center gap-3 px-4 py-3 rounded-lg transition-colors
            ${
              pathname?.startsWith('/szablony')
                ? 'bg-teal-50 text-teal-700 font-medium'
                : 'text-gray-700 hover:bg-gray-50'
            }
          `}
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
            />
          </svg>
          Szablony
        </Link>
      </nav>

      {/* Logout Button - Fixed at bottom */}
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 bg-white">
        <button
          onClick={handleLogout}
          disabled={isLoggingOut}
          className="
            w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors
            text-red-700 hover:bg-red-50 font-medium
            disabled:opacity-50 disabled:cursor-not-allowed
          "
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
            />
          </svg>
          {isLoggingOut ? 'Wylogowywanie...' : 'Wyloguj'}
        </button>
      </div>
    </div>
  );
}
