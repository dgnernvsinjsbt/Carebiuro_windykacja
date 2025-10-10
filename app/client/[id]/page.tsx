import { clientsDb, invoicesDb } from '@/lib/supabase';
import { parseFiscalSync, initializeFromEmailStatus } from '@/lib/fiscal-sync-parser';
import { parseWindykacja } from '@/lib/windykacja-parser';
import Sidebar from '@/components/Sidebar';
import ClientHeader from '@/components/ClientHeader';
import ClientInvoicesTable from '@/components/ClientInvoicesTable';
import OperationStatusBanner from '@/components/OperationStatusBanner';
import { ClientOperationLockProvider } from '@/lib/client-operation-lock';
import { notFound } from 'next/navigation';
import { InvoiceWithClient } from '@/types';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export default async function ClientDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const clientId = parseInt(params.id);

  if (isNaN(clientId)) {
    notFound();
  }

  // Fetch client
  const client = await clientsDb.getById(clientId);

  if (!client) {
    notFound();
  }

  // Use phone from Supabase (synced nightly from Fakturownia)
  const clientPhone = client.phone;

  // Fetch client's invoices from Supabase (ONLY for this client - fast!)
  const invoices = await invoicesDb.getByClientId(clientId);

  // No need to fetch from Fakturownia - all data is in Supabase from nightly sync!
  const fakturowniaMap = new Map();

  // Parse Fiscal Sync data for each invoice
  // If invoice was sent from Fakturownia (email_status='sent'), auto-mark EMAIL_1
  // Note: invoices from getByClientId() returns InvoiceFromDB[] which includes outstanding
  const invoicesWithFiscalSync: InvoiceWithClient[] = invoices.map((invoice) => {
    const fakturowniaData = fakturowniaMap.get(invoice.id);

    const initializedComment = initializeFromEmailStatus(
      invoice.internal_note,
      fakturowniaData?.email_status || invoice.email_status,
      fakturowniaData?.sent_time || invoice.sent_time
    );

    return {
      ...invoice, // invoice is InvoiceFromDB, includes outstanding field
      client: client,
      email_status: fakturowniaData?.email_status || invoice.email_status,
      sent_time: fakturowniaData?.sent_time || invoice.sent_time,
      fiscal_sync: parseFiscalSync(initializedComment),
    };
  });

  // Calculate unpaid balance as sum of (total - paid) for non-canceled invoices
  // IMPORTANT: Exclude corrective invoices (FK prefix) - they don't count toward balance
  const unpaidBalance = invoicesWithFiscalSync.reduce((sum, invoice) => {
    if (invoice.kind === 'canceled') return sum;

    // Skip corrective invoices (FK prefix) - they shouldn't affect total_unpaid
    const isCorrectiveInvoice = invoice.number && invoice.number.startsWith('FK');
    if (isCorrectiveInvoice) return sum;

    const balance = (invoice.total ?? 0) - (invoice.paid ?? 0);
    return sum + balance;
  }, 0);

  // Parse windykacja status from client note
  const windykacjaEnabled = parseWindykacja(client.note);

  return (
    <ClientOperationLockProvider>
      {/* Operation Status Banner */}
      <OperationStatusBanner />

      <div className="flex min-h-screen bg-gray-50">
        {/* Sidebar */}
        <Sidebar />

        {/* Main Content */}
        <main className="flex-1 p-8">
          <div className="max-w-7xl mx-auto">
            {/* Client Header */}
            <div className="mb-8">
              <div className="flex items-center gap-4 mb-4">
                <a
                  href="/"
                  className="text-gray-600 hover:text-gray-900 transition-colors"
                >
                  ← Powrót do listy klientów
                </a>
              </div>

              <ClientHeader client={client} unpaidBalance={unpaidBalance} />
            </div>

            {/* Invoices Table */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-xl font-semibold text-gray-900">
                  Faktury ({invoicesWithFiscalSync.length})
                </h2>
              </div>
              <ClientInvoicesTable
                invoices={invoicesWithFiscalSync}
                clientPhone={clientPhone || undefined}
                windykacjaEnabled={windykacjaEnabled}
              />
            </div>
          </div>
        </main>
      </div>
    </ClientOperationLockProvider>
  );
}
