import { NextRequest, NextResponse } from 'next/server';
import { validateCredentials, signToken } from '@/lib/auth';

/**
 * POST /api/auth/login
 * Endpoint do logowania - weryfikuje credentials i ustawia cookie z JWT
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { login, password } = body;

    // Walidacja danych wejściowych
    if (!login || !password) {
      return NextResponse.json(
        { success: false, error: 'Login i hasło są wymagane' },
        { status: 400 }
      );
    }

    // Weryfikacja credentials
    if (!validateCredentials(login, password)) {
      return NextResponse.json(
        { success: false, error: 'Nieprawidłowy login lub hasło' },
        { status: 401 }
      );
    }

    // Generowanie JWT token
    const token = await signToken(login);

    // Utworzenie response z ustawionym cookie
    const response = NextResponse.json({
      success: true,
      message: 'Zalogowano pomyślnie',
    });

    // Ustawienie HTTP-only cookie z tokenem (7 dni ważności)
    response.cookies.set('auth-token', token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 60 * 60 * 24 * 7, // 7 dni w sekundach
      path: '/',
    });

    return response;
  } catch (error) {
    console.error('Login error:', error);
    return NextResponse.json(
      { success: false, error: 'Błąd serwera podczas logowania' },
      { status: 500 }
    );
  }
}
