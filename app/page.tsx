import { clientsDb, supabaseAdmin } from '@/lib/supabase';
import Sidebar from '@/components/Sidebar';
import ClientsTable from '@/components/ClientsTable';

// Cache for 60 seconds - much faster!
// Will be revalidated on-demand when data changes (via revalidatePath)
export const revalidate = 60;

/**
 * Fetch all clients in batches (parallel-optimized)
 */
async function fetchAllClients() {
  const pageSize = 1000;
  let allClients: Array<any> = [];
  let page = 0;
  let hasMore = true;

  while (hasMore) {
    const { data, error } = await supabaseAdmin()
      .from('clients')
      .select('*')
      .range(page * pageSize, (page + 1) * pageSize - 1);

    if (error) {
      console.error('[fetchAllClients] Error:', error);
      break;
    }

    if (data && data.length > 0) {
      allClients = allClients.concat(data);
      page++;
      hasMore = data.length === pageSize;
    } else {
      hasMore = false;
    }
  }

  console.log('[fetchAllClients] Total fetched:', allClients.length);
  return allClients;
}

/**
 * Fetch all unpaid invoices in batches (parallel-optimized)
 */
async function fetchAllUnpaidInvoices() {
  const pageSize = 1000;
  let allInvoices: Array<{
    id: number;
    client_id: number | null;
    total: number | null;
    paid: number | null;
    status: string | null;
    kind: string | null
  }> = [];
  let page = 0;
  let hasMore = true;

  while (hasMore) {
    const { data, error } = await supabaseAdmin()
      .from('invoices')
      .select('id, client_id, total, paid, status, kind')
      .neq('status', 'paid')
      .neq('kind', 'canceled')
      .neq('kind', 'correction')
      .range(page * pageSize, (page + 1) * pageSize - 1);

    if (error) {
      console.error('[fetchAllUnpaidInvoices] Error:', error);
      break;
    }

    if (data && data.length > 0) {
      allInvoices = allInvoices.concat(data);
      page++;
      hasMore = data.length === pageSize;
    } else {
      hasMore = false;
    }
  }

  console.log('[fetchAllUnpaidInvoices] Total fetched:', allInvoices.length);
  return allInvoices;
}

export default async function ClientsPage() {
  // ✅ PARALLEL FETCH - znacznie szybsze!
  const [allClients, allInvoices] = await Promise.all([
    fetchAllClients(),
    fetchAllUnpaidInvoices()
  ]);

  console.log('[HomePage] Data loaded:', {
    clients: allClients.length,
    invoices: allInvoices.length
  });

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
