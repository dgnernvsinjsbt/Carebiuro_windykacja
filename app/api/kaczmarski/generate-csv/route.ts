/**
 * API Endpoint: Generate Kaczmarski CSV
 *
 * POST /api/kaczmarski/generate-csv
 * Body: { clientIds: number[] }
 *
 * Generuje pusty plik CSV dla zaznaczonych klientów
 */

import { NextRequest, NextResponse } from 'next/server';

// Force dynamic rendering - don't evaluate at build time
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  try {
    let clientIds: number[] = [];

    // Sprawdź czy request ma body
    const contentType = request.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      const body = await request.json();
      clientIds = body.clientIds;
    }

    console.log('[Kaczmarski CSV API] Otrzymano request z clientIds:', clientIds);

    if (!clientIds || !Array.isArray(clientIds) || clientIds.length === 0) {
      return NextResponse.json(
        { success: false, error: 'Brak wybranych klientów' },
        { status: 400 }
      );
    }

    console.log(`Generowanie pustego CSV dla ${clientIds.length} klientów...`);

    // Utwórz pusty CSV (tylko nagłówki)
    const csvContent = 'ID,Nazwa,Email,Zadłużenie,Liczba_Faktur\n';

    // Zwróć CSV jako response
    return new NextResponse(csvContent, {
      headers: {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': `attachment; filename="kaczmarski-${new Date().toISOString().split('T')[0]}.csv"`,
      },
    });
  } catch (error: any) {
    console.error('Błąd generowania CSV:', error);
    return NextResponse.json(
      {
        success: false,
        error: 'Błąd generowania CSV',
        details: error.message,
      },
      { status: 500 }
    );
  }
}
