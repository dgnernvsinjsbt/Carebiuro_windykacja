/**
 * API Endpoint: Get List Polecony Clients
 *
 * GET /api/list-polecony/clients
 *
 * Zwraca listę klientów kwalifikujących się do listu poleconego
 */

import { NextRequest, NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';
import { qualifiesForListPolecony, calculateTotalDebt, getInvoicesWithThirdReminder } from '@/lib/list-polecony-logic';

// Force dynamic rendering - don't evaluate at build time
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function GET(request: NextRequest) {
  try {
    // supabase client already initialized in lib

    // Pobierz wszystkich klientów
    const { data: clients, error: clientsError } = await supabase()
      .from('clients')
      .select('*')
      .order('name', { ascending: true });

    if (clientsError || !clients) {
      console.error('Błąd pobierania klientów:', clientsError);
      return NextResponse.json(
        { success: false, error: 'Błąd pobierania klientów' },
        { status: 500 }
      );
    }

    // Pobierz wszystkie faktury
    const { data: allInvoices, error: invoicesError } = await supabase()
      .from('invoices')
      .select('*');

    if (invoicesError || !allInvoices) {
      console.error('Błąd pobierania faktur:', invoicesError);
      return NextResponse.json(
        { success: false, error: 'Błąd pobierania faktur' },
        { status: 500 }
      );
    }

    // Filtruj klientów kwalifikujących się do listu poleconego
    const qualifiedClients = clients
      .map((client) => {
        const clientInvoices = allInvoices.filter((inv) => inv.client_id === client.id);

        const qualifies = qualifiesForListPolecony(client, clientInvoices);

        if (!qualifies) return null;

        // Oblicz statystyki
        const invoicesWithReminders = getInvoicesWithThirdReminder(clientInvoices);
        const totalDebt = calculateTotalDebt(clientInvoices);

        return {
          ...client,
          invoice_count: invoicesWithReminders.length,
          total_debt: totalDebt,
          qualifies_for_list_polecony: true,
        };
      })
      .filter(Boolean); // Usuń null

    console.log(`Znaleziono ${qualifiedClients.length} klientów kwalifikujących się do listu poleconego`);

    // Note: List Polecony status is tracked via invoice.internal_note, not client.list_polecony
    // Client qualification is calculated on-demand based on invoice flags

    return NextResponse.json({
      success: true,
      clients: qualifiedClients,
      count: qualifiedClients.length,
    });
  } catch (error: any) {
    console.error('Błąd pobierania klientów:', error);
    return NextResponse.json(
      {
        success: false,
        error: 'Błąd serwera',
        details: error.message,
      },
      { status: 500 }
    );
  }
}
