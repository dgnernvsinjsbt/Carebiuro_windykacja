/**
 * List Polecony Kaczmarski Page
 *
 * Wyświetla klientów do przekazania firmie windykacyjnej Kaczmarski:
 * - Mają wysłany list polecony (list_polecony_sent_date)
 * - Minęło ≥31 dni od wysłania
 * - Mają otwarte faktury (status != 'paid')
 */

import { supabaseAdmin } from '@/lib/supabase';
import Sidebar from '@/components/Sidebar';
import KaczmarskiTable from '@/components/KaczmarskiTable';

export const dynamic = 'force-dynamic';

async function getKaczmarskiClients() {
  const supabase = supabaseAdmin;

  // Oblicz datę 31 dni wstecz
  const thirtyOneDaysAgo = new Date();
  thirtyOneDaysAgo.setDate(thirtyOneDaysAgo.getDate() - 31);

  console.log(`[Kaczmarski] Szukam faktur wysłanych przed: ${thirtyOneDaysAgo.toISOString()}`);

  // KROK 1: Pobierz faktury spełniające warunki:
  // - list_polecony = true (list polecony został wysłany)
  // - list_polecony_sent_date <= 31 dni temu
  // - status != 'paid' (otwarte)
  const { data: qualifyingInvoices, error: invoicesError } = await supabase
    .from('invoices')
    .select('*')
    .eq('list_polecony', true)
    .lte('list_polecony_sent_date', thirtyOneDaysAgo.toISOString())
    .neq('status', 'paid');

  if (invoicesError) {
    console.error('[Kaczmarski] Error fetching invoices:', invoicesError);
    return [];
  }

  console.log(`[Kaczmarski] Znaleziono ${qualifyingInvoices?.length || 0} faktur spełniających warunki`);

  if (!qualifyingInvoices || qualifyingInvoices.length === 0) {
    return [];
  }

  // KROK 2: Pobierz unikalnych klientów dla tych faktur
  const clientIds = [...new Set(qualifyingInvoices.map(inv => inv.client_id).filter(Boolean))] as number[];

  const { data: clients, error: clientsError } = await supabase
    .from('clients')
    .select('*')
    .in('id', clientIds);

  if (clientsError) {
    console.error('[Kaczmarski] Error fetching clients:', clientsError);
    return [];
  }

  console.log(`[Kaczmarski] Znaleziono ${clients?.length || 0} klientów`);

  // KROK 3: Grupuj faktury po client_id
  const clientInvoicesMap = new Map<number, any[]>();
  for (const invoice of qualifyingInvoices) {
    if (!invoice.client_id) continue;

    if (!clientInvoicesMap.has(invoice.client_id)) {
      clientInvoicesMap.set(invoice.client_id, []);
    }
    clientInvoicesMap.get(invoice.client_id)!.push(invoice);
  }

  // KROK 4: Oblicz statystyki dla każdego klienta
  const kaczmarskiClients = clients.map((client) => {
    const invoices = clientInvoicesMap.get(client.id) || [];

    // Oblicz zadłużenie (suma outstanding = total - paid dla każdej faktury)
    const totalDebt = invoices.reduce((sum, invoice) => {
      const outstanding = (invoice.total || 0) - (invoice.paid || 0);
      return sum + outstanding;
    }, 0);

    // Znajdź najwcześniejszą datę wysłania (dla informacji)
    const earliestSentDate = invoices.reduce((earliest, inv) => {
      if (!inv.list_polecony_sent_date) return earliest;
      const invDate = new Date(inv.list_polecony_sent_date);
      return !earliest || invDate < earliest ? invDate : earliest;
    }, null as Date | null);

    // Oblicz ile dni minęło od najwcześniejszego wysłania
    const daysOverdue = earliestSentDate
      ? Math.floor((Date.now() - earliestSentDate.getTime()) / (1000 * 60 * 60 * 24))
      : 0;

    return {
      ...client,
      invoice_count: invoices.length,
      total_debt: totalDebt,
      qualifies_for_list_polecony: true,
      earliest_sent_date: earliestSentDate?.toISOString() || null,
      days_overdue: daysOverdue,
    };
  });

  console.log(`[Kaczmarski] Klientów kwalifikujących się do Kaczmarski: ${kaczmarskiClients.length}`);
  return kaczmarskiClients;
}

export default async function KaczmarskiPage() {
  const clients = await getKaczmarskiClients();

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <main className="flex-1 p-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-gray-900">Kaczmarski</h1>
            <p className="mt-2 text-gray-600">
              Klienci do przekazania firmie windykacyjnej Kaczmarski
            </p>
          </div>

          {/* Info Banner */}
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <svg
                className="w-5 h-5 text-red-600 mt-0.5"
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
              <div className="flex-1">
                <h3 className="text-sm font-medium text-red-900">
                  Windykacja Kaczmarski
                </h3>
                <div className="mt-2 text-sm text-red-700">
                  Klienci z tej listy otrzymali list polecony <strong>ponad 31 dni temu</strong> i nadal mają{' '}
                  <strong>nieopłacone faktury</strong>. Są gotowi do przekazania firmie windykacyjnej.
                </div>
              </div>
            </div>
          </div>

          {/* Tabela */}
          <KaczmarskiTable clients={clients} />

          {/* Statystyki */}
          {clients.length > 0 && (
            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white rounded-lg shadow p-4">
                <div className="text-sm text-gray-600">Klientów do windykacji</div>
                <div className="text-2xl font-bold text-gray-900 mt-1">
                  {clients.length}
                </div>
              </div>
              <div className="bg-white rounded-lg shadow p-4">
                <div className="text-sm text-gray-600">Łączna liczba faktur</div>
                <div className="text-2xl font-bold text-gray-900 mt-1">
                  {clients.reduce((sum, c) => sum + (c.invoice_count || 0), 0)}
                </div>
              </div>
              <div className="bg-white rounded-lg shadow p-4">
                <div className="text-sm text-gray-600">Łączne zadłużenie</div>
                <div className="text-2xl font-bold text-red-600 mt-1">
                  €{clients.reduce((sum, c) => sum + (c.total_debt || 0), 0).toFixed(2)}
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
