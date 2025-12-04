import { NextResponse } from 'next/server';

/**
 * POST /api/auth/logout
 * Endpoint do wylogowania - usuwa cookie z JWT
 */
export async function POST() {
  try {
    const response = NextResponse.json({
      success: true,
      message: 'Wylogowano pomyślnie',
    });

    // Usunięcie cookie poprzez ustawienie pustej wartości i wygaśnięcia w przeszłości
    response.cookies.set('auth-token', '', {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 0,
      path: '/',
    });

    return response;
  } catch (error) {
    console.error('Logout error:', error);
    return NextResponse.json(
      { success: false, error: 'Błąd serwera podczas wylogowania' },
      { status: 500 }
    );
  }
}
