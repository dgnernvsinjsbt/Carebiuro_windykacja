/**
 * List Polecony Page
 *
 * Wyświetla listę klientów kwalifikujących się do listu poleconego
 * z możliwością generowania dokumentów (PDF + Excel + ZIP)
 */

import { supabaseAdmin } from '@/lib/supabase';
import Sidebar from '@/components/Sidebar';
import ListPoleconyTable from '@/components/ListPoleconyTable';
import { qualifiesForListPolecony, calculateTotalDebt, getInvoicesWithThirdReminder } from '@/lib/list-polecony-logic';
import { parseListPolecony, parseListPoleconyIgnored } from '@/lib/list-polecony-parser';
import Link from 'next/link';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

async function getListPoleconyClients() {
  const supabase = supabaseAdmin;

  // OPTIMIZED: Pobierz TYLKO faktury z trzecim upomnieniem (has_third_reminder = true)
  const { data: invoicesWithThirdReminder, error: invoicesError } = await supabase()
    .from('invoices')
    .select('*')
    .eq('has_third_reminder', true);

  if (invoicesError) {
    console.error('[ListPolecony] Error fetching invoices:', invoicesError);
    return [];
  }

  console.log(`[ListPolecony] Fetched ${invoicesWithThirdReminder?.length || 0} invoices with third reminder`);

  // Grupuj faktury po client_id
  const clientInvoicesMap = new Map<number, any[]>();
  const clientIds = new Set<number>();

  for (const invoice of invoicesWithThirdReminder || []) {
    if (!invoice.client_id) continue;

    clientIds.add(invoice.client_id);

    if (!clientInvoicesMap.has(invoice.client_id)) {
      clientInvoicesMap.set(invoice.client_id, []);
    }
    clientInvoicesMap.get(invoice.client_id)!.push(invoice);
  }

  console.log(`[ListPolecony] Found ${clientIds.size} unique clients with third reminder invoices`);

  // Pobierz TYLKO klientów którzy mają faktury z trzecim upomnieniem
  const { data: clients, error: clientsError } = await supabase()
    .from('clients')
    .select('*')
    .in('id', Array.from(clientIds));

  if (clientsError) {
    console.error('[ListPolecony] Error fetching clients:', clientsError);
    return [];
  }

  console.log(`[ListPolecony] Fetched ${clients?.length || 0} clients`);

  // Filtruj klientów którzy kwalifikują się DO WYSŁANIA (nie wysłano jeszcze i nie zignorowano)
  const qualifiedClients = (clients || [])
    .map((client) => {
      // Sprawdź czy list polecony już został wysłany - filtruj NAJPIERW
      const listPoleconyWyslany = parseListPolecony(client.note);
      if (listPoleconyWyslany) return null; // Już wysłany - pomijamy

      // Sprawdź czy klient został zignorowany
      const listPoleconyIgnored = parseListPoleconyIgnored(client.note);
      if (listPoleconyIgnored) return null; // Zignorowany - pomijamy

      const clientInvoices = clientInvoicesMap.get(client.id) || [];
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
    .filter(Boolean);

  console.log(`[ListPolecony] ${qualifiedClients.length} clients qualify for list polecony`);

  return qualifiedClients;
}

export default async function ListPoleconyPage() {
  const clients = await getListPoleconyClients();

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <main className="flex-1 p-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-gray-900">List Polecony</h1>
            <p className="mt-2 text-gray-600">
              Klienci z 3+ fakturami po trzecim upomnieniu lub z sumą zadłużenia ≥ 190 EUR po trzecim upomnieniu
            </p>
          </div>

          {/* Tabs Navigation */}
          <div className="mb-6 border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              <Link
                href="/list-polecony"
                className="border-teal-600 text-teal-600 whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm"
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
                className="border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm"
              >
                Ignorowane
              </Link>
            </nav>
          </div>

        {/* Info Banner */}
        <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <svg
              className="w-5 h-5 text-blue-600 mt-0.5"
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
              <h3 className="text-sm font-medium text-blue-900">
                Jak to działa?
              </h3>
              <div className="mt-2 text-sm text-blue-700">
                <ol className="list-decimal list-inside space-y-1">
                  <li>Zaznacz klientów, dla których chcesz wygenerować dokumenty</li>
                  <li>Kliknij "Generuj dokumenty"</li>
                  <li>
                    Pobierz archiwum ZIP zawierające:
                    <ul className="list-disc list-inside ml-6 mt-1">
                      <li>Osobne PDF-y dla każdego klienta (1.pdf, 2.pdf, ...)</li>
                      <li>Plik Excel z danymi klientów (lista_klientow.xlsx)</li>
                    </ul>
                  </li>
                </ol>
              </div>
            </div>
          </div>
        </div>

        {/* Tabela */}
        <ListPoleconyTable clients={clients} />

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
