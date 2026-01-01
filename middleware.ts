import { NextRequest, NextResponse } from 'next/server';
import { verifyToken } from '@/lib/auth';

/**
 * Middleware Next.js - chroni wszystkie strony oprócz whitelisty
 * Weryfikuje JWT token w cookie i przekierowuje niezalogowanych na /login
 */
export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Whitelist - ścieżki dostępne bez logowania
  const publicPaths = [
    '/login',
    '/api/auth/login',
    '/api/auth/logout',
    '/api/windykacja/auto-send-initial',
    '/api/windykacja/auto-send-overdue',
    '/api/windykacja/auto-send-sequence',
    '/api/sync/addresses', // Address sync endpoint
  ];

  // Sprawdź czy ścieżka jest publiczna
  const isPublicPath = publicPaths.some(path => pathname.startsWith(path));

  // Pozwól na pliki statyczne Next.js
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/favicon.ico') ||
    pathname.startsWith('/static')
  ) {
    return NextResponse.next();
  }

  // Pobierz token z cookie
  const token = request.cookies.get('auth-token')?.value;

  // Jeśli na stronie logowania i jest zalogowany -> przekieruj na główną
  if (pathname === '/login' && token) {
    try {
      await verifyToken(token);
      return NextResponse.redirect(new URL('/', request.url));
    } catch {
      // Token nieważny, pozwól zostać na /login
      return NextResponse.next();
    }
  }

  // Jeśli na ścieżce publicznej -> pozwól
  if (isPublicPath) {
    return NextResponse.next();
  }

  // Sprawdź czy użytkownik jest zalogowany
  if (!token) {
    // Brak tokenu -> przekieruj na login
    const loginUrl = new URL('/login', request.url);
    return NextResponse.redirect(loginUrl);
  }

  try {
    // Weryfikuj token
    await verifyToken(token);
    return NextResponse.next();
  } catch (error) {
    // Token nieważny -> przekieruj na login
    console.error('Token verification failed:', error);
    const loginUrl = new URL('/login', request.url);
    const response = NextResponse.redirect(loginUrl);

    // Usuń nieważny token
    response.cookies.delete('auth-token');

    return response;
  }
}

/**
 * Konfiguracja matchera - określa które ścieżki mają być chronione
 * Wykluczamy pliki statyczne i API routes które nie wymagają autoryzacji
 */
export const config = {
  matcher: [
    /*
     * Dopasuj wszystkie ścieżki oprócz:
     * - _next/static (pliki statyczne)
     * - _next/image (optymalizacja obrazów)
     * - favicon.ico (favicon)
     * - public folder (obrazy, itp.)
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.png$|.*\\.jpg$|.*\\.jpeg$|.*\\.gif$|.*\\.svg$).*)',
  ],
};
