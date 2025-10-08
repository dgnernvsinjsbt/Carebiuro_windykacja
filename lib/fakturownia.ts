import { FakturowniaInvoice, FakturowniaClient } from '@/types';

// Lazy initialization - only validate when actually used
let _apiToken: string | null = null;
let _account: string | null = null;
let _baseUrl: string | null = null;

function getApiToken(): string {
  if (!_apiToken) {
    _apiToken = process.env.FAKTUROWNIA_API_TOKEN || '';
    if (!_apiToken) {
      throw new Error('Missing FAKTUROWNIA_API_TOKEN environment variable');
    }
  }
  return _apiToken;
}

function getAccount(): string {
  if (!_account) {
    _account = process.env.FAKTUROWNIA_ACCOUNT || '';
    if (!_account) {
      throw new Error('Missing FAKTUROWNIA_ACCOUNT environment variable');
    }
  }
  return _account;
}

function getBaseUrl(): string {
  if (!_baseUrl) {
    _baseUrl = `https://${getAccount()}.fakturownia.pl`;
  }
  return _baseUrl;
}

const API_TOKEN = getApiToken;
const ACCOUNT = getAccount;
const BASE_URL = getBaseUrl;

/**
 * Rate limiter for Fakturownia API
 * Limit: 1000 requests/hour AND 1 request/second
 * We enforce 2000ms (2s) between requests for extra safety during full sync
 */
class RateLimiter {
  private lastRequest: number = 0;
  private readonly minInterval: number = 2000; // ms (2 seconds for safety)
  private requestCount: number = 0;
  private windowStart: number = Date.now();
  private readonly maxRequestsPerHour: number = 1000;

  async wait() {
    const now = Date.now();

    // Reset hourly counter if window passed
    if (now - this.windowStart >= 3600000) {
      console.log(`[RateLimiter] ✓ Hourly window reset. Prev count: ${this.requestCount}`);
      this.requestCount = 0;
      this.windowStart = now;
    }

    // Warning at 900 requests (approaching limit)
    if (this.requestCount === 900) {
      const elapsed = (now - this.windowStart) / 1000;
      const remaining = 1000 - this.requestCount;
      console.warn(`[RateLimiter] ⚠️  Approaching hourly limit: ${this.requestCount}/1000 requests used in ${elapsed.toFixed(0)}s. ${remaining} remaining.`);
    }

    // Check hourly limit - PAUSE for remaining time
    if (this.requestCount >= this.maxRequestsPerHour) {
      const waitUntilNextWindow = 3600000 - (now - this.windowStart);
      const waitMinutes = (waitUntilNextWindow / 60000).toFixed(1);
      console.warn(`[RateLimiter] 🛑 HOURLY LIMIT REACHED (1000 requests/hour)`);
      console.warn(`[RateLimiter] ⏳ Pausing for ${waitMinutes} minutes until next window...`);
      await new Promise(resolve => setTimeout(resolve, waitUntilNextWindow));
      this.requestCount = 0;
      this.windowStart = Date.now();
      console.log(`[RateLimiter] ✓ Resuming sync after hourly pause`);
    }

    // Enforce 2 seconds between requests
    const elapsed = now - this.lastRequest;
    const waitTime = Math.max(0, this.minInterval - elapsed);

    if (waitTime > 0) {
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }

    this.lastRequest = Date.now();
    this.requestCount++;

    // Log progress every 100 requests
    if (this.requestCount % 100 === 0) {
      const elapsedMinutes = ((Date.now() - this.windowStart) / 60000).toFixed(1);
      console.log(`[RateLimiter] Progress: ${this.requestCount}/1000 requests in ${elapsedMinutes} min`);
    }
  }

  /**
   * Get current request count in this hourly window
   */
  getRequestCount(): number {
    return this.requestCount;
  }

  /**
   * Get remaining requests in this hourly window
   */
  getRemainingRequests(): number {
    return this.maxRequestsPerHour - this.requestCount;
  }
}

const rateLimiter = new RateLimiter();

/**
 * Make authenticated request to Fakturownia API
 */
async function fakturowniaRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  // Rate limiting
  await rateLimiter.wait();

  const url = `${BASE_URL()}${endpoint}${endpoint.includes('?') ? '&' : '?'}api_token=${API_TOKEN()}`;

  console.log(`[Fakturownia] ${options.method || 'GET'} ${endpoint}`);

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    console.error(`[Fakturownia] Error: ${response.status} ${errorText}`);
    throw new Error(`Fakturownia API error: ${response.status} ${errorText}`);
  }

  return response.json();
}

/**
 * Fakturownia API client
 */
export const fakturowniaApi = {
  /**
   * Direct API request method (exposed for custom endpoints)
   */
  fakturowniaRequest,

  /**
   * Get all invoices (paginated)
   */
  async getAllInvoices(page: number = 1, perPage: number = 100): Promise<FakturowniaInvoice[]> {
    return fakturowniaRequest<FakturowniaInvoice[]>(
      `/invoices.json?page=${page}&per_page=${perPage}`
    );
  },

  /**
   * Get recently updated invoices (for incremental sync)
   */
  async getRecentInvoices(perPage: number = 100): Promise<FakturowniaInvoice[]> {
    return fakturowniaRequest<FakturowniaInvoice[]>(
      `/invoices.json?sort=updated_at&order=desc&per_page=${perPage}`
    );
  },

  /**
   * Get unpaid invoices
   */
  async getUnpaidInvoices(page: number = 1, perPage: number = 100): Promise<FakturowniaInvoice[]> {
    return fakturowniaRequest<FakturowniaInvoice[]>(
      `/invoices.json?status=not_paid&page=${page}&per_page=${perPage}`
    );
  },

  /**
   * Get invoices by client ID
   */
  async getInvoicesByClientId(clientId: number, perPage: number = 100): Promise<FakturowniaInvoice[]> {
    return fakturowniaRequest<FakturowniaInvoice[]>(
      `/invoices.json?client_id=${clientId}&per_page=${perPage}`
    );
  },

  /**
   * Get invoice by ID
   */
  async getInvoice(id: number): Promise<FakturowniaInvoice> {
    return fakturowniaRequest<FakturowniaInvoice>(`/invoices/${id}.json`);
  },

  /**
   * Update invoice (including comment)
   */
  async updateInvoice(id: number, data: Partial<FakturowniaInvoice>): Promise<FakturowniaInvoice> {
    return fakturowniaRequest<FakturowniaInvoice>(`/invoices/${id}.json`, {
      method: 'PUT',
      body: JSON.stringify({ invoice: data }),
    });
  },

  /**
   * Update invoice internal note (private, not visible on print)
   */
  async updateInvoiceComment(id: number, internal_note: string): Promise<FakturowniaInvoice> {
    return this.updateInvoice(id, { internal_note });
  },

  /**
   * Get all clients (paginated)
   */
  async getAllClients(page: number = 1, perPage: number = 100): Promise<FakturowniaClient[]> {
    return fakturowniaRequest<FakturowniaClient[]>(
      `/clients.json?page=${page}&per_page=${perPage}`
    );
  },

  /**
   * Get client by ID
   */
  async getClient(id: number): Promise<FakturowniaClient> {
    return fakturowniaRequest<FakturowniaClient>(`/clients/${id}.json`);
  },

  /**
   * Update client (including note field for flags)
   */
  async updateClient(id: number, data: Partial<FakturowniaClient>): Promise<FakturowniaClient> {
    return fakturowniaRequest<FakturowniaClient>(`/clients/${id}.json`, {
      method: 'PUT',
      body: JSON.stringify({ client: data }),
    });
  },

  /**
   * Fetch ALL invoices with pagination (full sync)
   * Fetches all invoices regardless of status - for holistic client debt view
   *
   * Parameters:
   * - status= (empty): ALL invoices (issued, paid, draft, canceled)
   * - period=all: all time (not just recent)
   * - per_page=100: 100 invoices per page
   */
  async fetchAllInvoices(): Promise<FakturowniaInvoice[]> {
    const allInvoices: FakturowniaInvoice[] = [];
    let page = 1;
    let hasMore = true;

    console.log('[Fakturownia] Starting FULL sync (ALL invoices, all statuses)...');

    while (hasMore) {
      // Fetch ALL invoices (no status filter)
      const invoices = await fakturowniaRequest<FakturowniaInvoice[]>(
        `/invoices.json?period=all&page=${page}&per_page=100`
      );

      if (invoices.length === 0) {
        hasMore = false;
        console.log(`[Fakturownia] No more invoices on page ${page}. Stopping.`);
      } else {
        allInvoices.push(...invoices);
        console.log(`[Fakturownia] ✓ Page ${page}: ${invoices.length} invoices (total: ${allInvoices.length})`);
        page++;
      }
    }

    console.log(`[Fakturownia] FULL sync complete: ${allInvoices.length} total invoices`);
    return allInvoices;
  },

  /**
   * Fetch all clients with pagination (full sync)
   */
  async fetchAllClients(): Promise<FakturowniaClient[]> {
    const allClients: FakturowniaClient[] = [];
    let page = 1;
    let hasMore = true;

    console.log('[Fakturownia] Starting full client sync...');

    while (hasMore) {
      const clients = await this.getAllClients(page, 100);

      if (clients.length === 0) {
        hasMore = false;
      } else {
        allClients.push(...clients);
        console.log(`[Fakturownia] Fetched page ${page}, total: ${allClients.length}`);
        page++;
      }
    }

    console.log(`[Fakturownia] Full sync complete: ${allClients.length} clients`);
    return allClients;
  },
};
