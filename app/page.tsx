import { clientsDb, supabase } from '@/lib/supabase';
import Sidebar from '@/components/Sidebar';
import ClientsTable from '@/components/ClientsTable';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export default async function ClientsPage() {
  // Fetch ALL clients in batches (Supabase has 1000 row limit)
  let allClients: Array<any> = [];
  let clientPage = 0;
  const pageSize = 1000;
  let hasMoreClients = true;

  while (hasMoreClients) {
    const { data, error } = await supabase
      .from('clients')
      .select('*')
      .range(clientPage * pageSize, (clientPage + 1) * pageSize - 1);

    if (error) {
      console.error('[HomePage] Error fetching clients:', error);
      break;
    }

    if (data && data.length > 0) {
      allClients = allClients.concat(data);
      clientPage++;

      if (data.length < pageSize) {
        hasMoreClients = false;
      }
    } else {
      hasMoreClients = false;
    }
  }

  console.log('[HomePage] Clients fetched:', allClients.length);

  // Fetch ALL unpaid invoices (status != 'paid' AND kind != 'canceled' AND kind != 'correction')
  // Supabase has default 1000 row limit - we need to fetch in batches
  let allInvoices: Array<{ id: number; client_id: number | null; total: number | null; paid: number | null; status: string | null; kind: string | null }> = [];
  let invoicePage = 0;
  let hasMoreInvoices = true;

  while (hasMoreInvoices) {
    const { data, error } = await supabase
      .from('invoices')
      .select('id, client_id, total, paid, status, kind')
      .neq('status', 'paid')             // status != 'paid'
      .neq('kind', 'canceled')           // kind != 'canceled'
      .neq('kind', 'correction')         // kind != 'correction'
      .range(invoicePage * pageSize, (invoicePage + 1) * pageSize - 1);

    if (error) {
      console.error('[HomePage] Error fetching invoices:', error);
      break;
    }

    if (data && data.length > 0) {
      allInvoices = allInvoices.concat(data);
      invoicePage++;

      // If we got less than pageSize, we've reached the end
      if (data.length < pageSize) {
        hasMoreInvoices = false;
      }
    } else {
      hasMoreInvoices = false;
    }
  }

  console.log('[HomePage] Unpaid invoices fetched:', allInvoices.length);

  // Calculate unpaid balance per client (sum of total - paid for all unpaid invoices)
  const clientBalanceMap = new Map<number, { count: number; balance: number }>();

  if (allInvoices) {
    allInvoices.forEach((invoice) => {
      if (invoice.client_id) {
        const balance = (invoice.total ?? 0) - (invoice.paid ?? 0);

        if (!clientBalanceMap.has(invoice.client_id)) {
          clientBalanceMap.set(invoice.client_id, { count: 0, balance: 0 });
        }

        const clientData = clientBalanceMap.get(invoice.client_id)!;
        clientData.count++;
        clientData.balance += balance;
      }
    });
  }

  console.log('[HomePage] Client balance map size:', clientBalanceMap.size);

  // Add unpaid invoice count and calculated balance to clients
  const clientsWithCount = allClients.map((client) => {
    const clientData = clientBalanceMap.get(client.id);
    return {
      ...client,
      invoice_count: clientData?.count || 0,
      total_unpaid: clientData?.balance || 0,
    };
  });

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <main className="flex-1 p-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900">
              Klienci
            </h1>
            <p className="mt-2 text-gray-600">
              Lista wszystkich klientów z Fakturowni
            </p>
          </div>

          {/* Clients Table */}
          <ClientsTable clients={clientsWithCount} />
        </div>
      </main>
    </div>
  );
}
