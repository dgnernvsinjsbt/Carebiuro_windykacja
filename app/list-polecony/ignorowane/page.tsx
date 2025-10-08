/**
 * List Polecony Ignorowane Page
 *
 * Wyświetla listę klientów którzy zostali zignorowani
 * (mają flagę [LIST_POLECONY_IGNORED]true w note)
 */

import { supabaseAdmin } from '@/lib/supabase';
import Sidebar from '@/components/Sidebar';
import ListPoleconyTable from '@/components/ListPoleconyTable';
import Link from 'next/link';
import { parseInvoiceFlags } from '@/lib/invoice-flags';

export const dynamic = 'force-dynamic';

async function getIgnorowaneClients() {
  const supabase = supabaseAdmin;

  // Pobierz TYLKO klientów z flagą [LIST_POLECONY_IGNORED]true w note
  const { data: ignorowaneClientsData, error: clientsError } = await supabase()
    .from('clients')
    .select('*')
    .like('note', '%[LIST_POLECONY_IGNORED]true%');

  if (clientsError) {
    console.error('[ListPolecony Ignorowane] Error fetching clients:', clientsError);
    return [];
  }

  console.log(`[ListPolecony Ignorowane] Fetched ${ignorowaneClientsData?.length || 0} ignored clients`);

  // Pobierz client_ids
  const clientIds = ignorowaneClientsData?.map(c => c.id) || [];

  if (clientIds.length === 0) {
    return [];
  }

  // Pobierz faktury z flagą [LIST_POLECONY_IGNORED]true dla klientów zignorowanych
  const { data: clientInvoices, error: invoicesError } = await supabase()
    .from('invoices')
    .select('*')
    .in('client_id', clientIds)
    .like('internal_note', '%[LIST_POLECONY_IGNORED]true%');

  if (invoicesError) {
    console.error('[ListPolecony Ignorowane] Error fetching invoices:', invoicesError);
  }

  console.log(`[ListPolecony Ignorowane] Fetched ${clientInvoices?.length || 0} ignored invoices`);

  // Grupuj faktury po client_id
  const clientInvoicesMap = new Map<number, any[]>();
  for (const invoice of clientInvoices || []) {
    if (!invoice.client_id) continue;

    if (!clientInvoicesMap.has(invoice.client_id)) {
      clientInvoicesMap.set(invoice.client_id, []);
    }
    clientInvoicesMap.get(invoice.client_id)!.push(invoice);
  }

  // Oblicz statystyki dla każdego klienta
  const ignorowaneClients = ignorowaneClientsData.map((client) => {
    const invoices = clientInvoicesMap.get(client.id) || [];

    // Oblicz zadłużenie (suma balance = total - paid ze wszystkich faktur zignorowanych)
    const totalDebt = invoices.reduce((sum, inv) => {
      const balance = (inv.total || 0) - (inv.paid || 0);
      return sum + balance;
    }, 0);

    // Znajdź najwcześniejszą datę WYSŁANIA (parsuj z internal_note)
    const earliestSentDate = invoices.reduce((earliest, inv) => {
      const flags = parseInvoiceFlags(inv.internal_note);
      if (!flags.listPoleconySentDate) return earliest;
      const invDate = new Date(flags.listPoleconySentDate);
      return !earliest || invDate < earliest ? invDate : earliest;
    }, null as Date | null);

    // Oblicz ile dni minęło od wysłania
    const daysOverdue = earliestSentDate
      ? Math.floor((Date.now() - earliestSentDate.getTime()) / (1000 * 60 * 60 * 24))
      : 0;

    return {
      ...client,
      invoice_count: invoices.length,
      total_debt: totalDebt,
      earliest_sent_date: earliestSentDate?.toISOString() || null,
      days_overdue: daysOverdue,
    };
  });

  console.log(`[ListPolecony Ignorowane] Klientów zignorowanych: ${ignorowaneClients.length}`);
  return ignorowaneClients;
}

export default async function ListPoleconyIgnorowanePage() {
  const clients = await getIgnorowaneClients();

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <main className="flex-1 p-8">
        <div className="max-w-7xl mx-auto">
          {/* Header z nawigacją */}
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-gray-900">List Polecony</h1>
            <p className="mt-2 text-gray-600">
              Klienci zignorowani
            </p>
          </div>

          {/* Tabs Navigation */}
          <div className="mb-6 border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              <Link
                href="/list-polecony"
                className="border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm"
              >
                Do wysłania
              </Link>
              <Link
                href="/list-polecony/wyslane"
                className="border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm"
              >
                Wysłane
              </Link>
              <Link
                href="/list-polecony/ignorowane"
                className="border-teal-600 text-teal-600 whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm"
              >
                Ignorowane
              </Link>
            </nav>
          </div>

          {/* Info Banner */}
          <div className="mb-6 bg-gray-50 border border-gray-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <svg
                className="w-5 h-5 text-gray-600 mt-0.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <div className="flex-1">
                <h3 className="text-sm font-medium text-gray-900">
                  Zignorowane klientów
                </h3>
                <div className="mt-2 text-sm text-gray-700">
                  Ci klienci zostali oznaczeni jako zignorowanie i nie będą uwzględniani w automatycznych procesach windykacyjnych.
                </div>
              </div>
            </div>
          </div>

          {/* Tabela */}
          <ListPoleconyTable clients={clients} hideGenerateButton={true} showSentDate={true} showRestoreButton={true} />

          {/* Statystyki */}
          {clients.length > 0 && (
            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white rounded-lg shadow p-4">
                <div className="text-sm text-gray-600">Łączna liczba klientów</div>
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
