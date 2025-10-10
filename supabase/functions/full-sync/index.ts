import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

interface FakturowniaInvoice {
  id: number
  client_id: number
  number: string
  price_gross: string
  price_net: string
  price_tax: string
  paid: string
  status: string
  internal_note: string | null
  email_status: string | null
  sent_time: string | null
  updated_at: string
  issue_date: string | null
  sell_date: string | null
  payment_to: string | null
  paid_date: string | null
  created_at: string | null
  currency: string | null
  payment_type: string | null
  buyer_name: string | null
  buyer_email: string | null
  buyer_phone: string | null
  buyer_tax_no: string | null
  buyer_street: string | null
  buyer_city: string | null
  buyer_post_code: string | null
  buyer_country: string | null
  kind: string | null
  description: string | null
  place: string | null
  view_url: string | null
  payment_url: string | null
  'overdue?': boolean | null
}

interface FakturowniaClient {
  id: number
  note: string | null
}

interface Invoice {
  id: number
  client_id: number
  number: string
  total: number
  status: string
  internal_note: string | null
  email_status: string | null
  sent_time: string | null
  updated_at: string
  issue_date: string | null
  sell_date: string | null
  payment_to: string | null
  paid_date: string | null
  created_at: string | null
  price_net: number | null
  price_tax: number | null
  paid: number | null
  currency: string | null
  payment_type: string | null
  buyer_name: string | null
  buyer_email: string | null
  buyer_phone: string | null
  buyer_tax_no: string | null
  buyer_street: string | null
  buyer_city: string | null
  buyer_post_code: string | null
  buyer_country: string | null
  kind: string | null
  description: string | null
  place: string | null
  view_url: string | null
  payment_url: string | null
  overdue: boolean | null
  has_third_reminder: boolean
  list_polecony_sent_date: string | null
  list_polecony_ignored_date: string | null
}

interface Client {
  id: number
  name: string
  first_name: string | null
  last_name: string | null
  tax_no: string | null
  post_code: string | null
  city: string | null
  street: string | null
  street_no: string | null
  country: string | null
  email: string | null
  phone: string | null
  mobile_phone: string | null
  www: string | null
  fax: string | null
  note: string | null
  bank: string | null
  bank_account: string | null
  shortcut: string | null
  kind: string | null
  token: string | null
  discount: number | null
  payment_to_kind: string | null
  category_id: number | null
  use_delivery_address: boolean | null
  delivery_address: string | null
  person: string | null
  use_mass_payment: boolean | null
  mass_payment_code: string | null
  external_id: string | null
  company: boolean | null
  title: string | null
  register_number: string | null
  tax_no_check: boolean | null
  disable_auto_reminders: boolean | null
  created_at: string | null
  updated_at: string
  total_unpaid: number
  list_polecony: string | null
}

// Helper: Check if invoice has third reminder in internal_note
function hasThirdReminder(invoice: { internal_note: string | null }): boolean {
  if (!invoice.internal_note) return false

  const match = invoice.internal_note.match(/\[FISCAL_SYNC\](.*?)\[\/FISCAL_SYNC\]/s)
  if (!match) return false

  try {
    const syncData = JSON.parse(match[1])
    return syncData.third_reminder_sent === true
  } catch {
    return false
  }
}

// Helper: Send SMS notification
async function sendSMS(message: string, smsFrom: string, smsToken: string) {
  try {
    const formData = new URLSearchParams()
    formData.append('from', smsFrom)
    formData.append('to', '+48536214664')
    formData.append('msg', message)

    await fetch('https://api2.smsplanet.pl/sms', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': `Bearer ${smsToken}`,
      },
      body: formData.toString(),
    })
  } catch (error) {
    console.error('[Sync] SMS alert failed:', error)
  }
}

// Helper: Fakturownia API request
async function fakturowniaRequest<T>(endpoint: string, fakturowniaApiToken: string): Promise<T> {
  // Add api_token as query parameter (not header!)
  const separator = endpoint.includes('?') ? '&' : '?'
  const url = `https://cbb-office.fakturownia.pl${endpoint}${separator}api_token=${fakturowniaApiToken}`

  const response = await fetch(url, {
    headers: {
      'Accept': 'application/json',
    },
  })

  if (!response.ok) {
    throw new Error(`Fakturownia API error: ${response.status}`)
  }

  return response.json()
}

// Helper: Fetch all clients from Fakturownia
async function fetchAllClients(fakturowniaApiToken: string): Promise<FakturowniaClient[]> {
  const allClients: FakturowniaClient[] = []
  let page = 1
  let hasMore = true

  while (hasMore) {
    const clients = await fakturowniaRequest<FakturowniaClient[]>(
      `/clients.json?page=${page}&per_page=100`,
      fakturowniaApiToken
    )

    if (clients.length === 0) {
      hasMore = false
    } else {
      allClients.push(...clients)
      page++
      // Rate limit: 1 req/sec
      await new Promise(resolve => setTimeout(resolve, 1000))
    }
  }

  return allClients
}

serve(async (req) => {
  try {
    // Security: Accept only GitHub Actions or Vercel Cron
    const isGitHubAction = req.headers.get('x-github-action') === 'true'
    const isVercelCron = req.headers.get('x-vercel-cron') === '1'

    if (!isGitHubAction && !isVercelCron) {
      console.error('[Sync] Unauthorized: Not from GitHub Actions or Vercel Cron')
      return new Response(
        JSON.stringify({ success: false, error: 'Unauthorized' }),
        { status: 401, headers: { 'Content-Type': 'application/json' } }
      )
    }

    console.log('[Sync] Starting full synchronization...')
    const startTime = Date.now()

    // Environment variables
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    const fakturowniaApiToken = Deno.env.get('FAKTUROWNIA_API_TOKEN')!
    const smsFrom = Deno.env.get('SMSPLANET_FROM') || 'Cbb-Office'
    const smsToken = Deno.env.get('SMSPLANET_API_TOKEN')!

    // Initialize Supabase client
    const supabase = createClient(supabaseUrl, supabaseServiceKey)

    // STEP 1: Clear all existing data
    console.log('[Sync] STEP 1: Clearing all existing data from Supabase...')
    await supabase.from('invoices').delete().neq('id', 0)
    await supabase.from('clients').delete().neq('id', 0)
    console.log('[Sync] ✓ All data cleared')

    // STEP 2: Stream invoices + clients from Fakturownia
    console.log('[Sync] STEP 2: Streaming invoices from Fakturownia (ALL statuses)...')
    console.log('[Sync] Parameters: status=all, period=all, per_page=100, delay=1s')
    console.log('[Sync] Strategy: Fetch page → Create NEW clients → Save ALL invoices → Repeat')

    const seenClientIds = new Set<number>()
    let totalInvoices = 0
    let totalClients = 0
    let page = 1
    let hasMore = true

    while (hasMore) {
      // 1. Fetch one page (100 invoices)
      const pageInvoices = await fakturowniaRequest<FakturowniaInvoice[]>(
        `/invoices.json?period=all&page=${page}&per_page=100`,
        fakturowniaApiToken
      )

      if (pageInvoices.length === 0) {
        hasMore = false
        console.log(`[Sync] ✓ Page ${page}: No more invoices`)
        break
      }

      // 2. Extract unique client_ids from this page
      const uniqueClientIdsOnPage = new Set<number>()
      const clientDataMap = new Map<number, FakturowniaInvoice>()

      for (const invoice of pageInvoices) {
        if (invoice.client_id) {
          uniqueClientIdsOnPage.add(invoice.client_id)
          if (!clientDataMap.has(invoice.client_id)) {
            clientDataMap.set(invoice.client_id, invoice)
          }
        }
      }

      // 3. Create ONLY NEW clients
      const newClientIds = Array.from(uniqueClientIdsOnPage).filter(id => !seenClientIds.has(id))

      console.log(`[Sync] Page ${page}: ${uniqueClientIdsOnPage.size} unique clients, ${newClientIds.length} new`)

      if (newClientIds.length > 0) {
        const newClients: Client[] = newClientIds.map(clientId => {
          const invoiceData = clientDataMap.get(clientId)!
          return {
            id: clientId,
            name: invoiceData.buyer_name || `Client ${clientId}`,
            first_name: null,
            last_name: null,
            tax_no: invoiceData.buyer_tax_no || null,
            post_code: invoiceData.buyer_post_code || null,
            city: invoiceData.buyer_city || null,
            street: invoiceData.buyer_street || null,
            street_no: null,
            country: invoiceData.buyer_country || null,
            email: invoiceData.buyer_email || null,
            phone: invoiceData.buyer_phone || null,
            mobile_phone: null,
            www: null,
            fax: null,
            note: null,
            bank: null,
            bank_account: null,
            shortcut: null,
            kind: null,
            token: null,
            discount: null,
            payment_to_kind: null,
            category_id: null,
            use_delivery_address: null,
            delivery_address: null,
            person: null,
            use_mass_payment: null,
            mass_payment_code: null,
            external_id: null,
            company: null,
            title: null,
            register_number: null,
            tax_no_check: null,
            disable_auto_reminders: null,
            created_at: null,
            updated_at: new Date().toISOString(),
            total_unpaid: 0,
            list_polecony: null,
          }
        })

        console.log(`[Sync] Creating clients: ${newClientIds.slice(0, 5).join(', ')}${newClientIds.length > 5 ? '...' : ''}`)

        const { error: clientError } = await supabase.from('clients').upsert(newClients)
        if (clientError) throw clientError

        newClientIds.forEach(id => seenClientIds.add(id))
        totalClients += newClientIds.length
        console.log(`[Sync] ✓ Page ${page}: Created ${newClientIds.length} new clients (total: ${totalClients})`)
      }

      // Debug: check for invoices with missing clients
      const invoicesWithMissingClients = pageInvoices.filter(inv =>
        inv.client_id && !seenClientIds.has(inv.client_id)
      )
      if (invoicesWithMissingClients.length > 0) {
        console.error(`[Sync] ERROR: Page ${page} has ${invoicesWithMissingClients.length} invoices with missing clients!`)
        console.error(`[Sync] Missing client_ids: ${invoicesWithMissingClients.map(i => i.client_id).slice(0, 10).join(', ')}`)
      }

      // 4. Transform and save ALL invoices
      const invoices: Invoice[] = pageInvoices.map((fi: FakturowniaInvoice) => {
        const tempInvoice = { internal_note: fi.internal_note || null }
        const hasThird = hasThirdReminder(tempInvoice)

        return {
          id: fi.id,
          client_id: fi.client_id,
          number: fi.number,
          total: parseFloat(fi.price_gross) || 0,
          status: fi.status,
          internal_note: fi.internal_note || null,
          email_status: fi.email_status || null,
          sent_time: fi.sent_time || null,
          updated_at: fi.updated_at,
          issue_date: fi.issue_date || null,
          sell_date: fi.sell_date || null,
          payment_to: fi.payment_to || null,
          paid_date: fi.paid_date || null,
          created_at: fi.created_at || null,
          price_net: parseFloat(fi.price_net) || null,
          price_tax: parseFloat(fi.price_tax) || null,
          paid: parseFloat(fi.paid) || null,
          currency: fi.currency || null,
          payment_type: fi.payment_type || null,
          buyer_name: fi.buyer_name || null,
          buyer_email: fi.buyer_email || null,
          buyer_phone: fi.buyer_phone || null,
          buyer_tax_no: fi.buyer_tax_no || null,
          buyer_street: fi.buyer_street || null,
          buyer_city: fi.buyer_city || null,
          buyer_post_code: fi.buyer_post_code || null,
          buyer_country: fi.buyer_country || null,
          kind: fi.kind || null,
          description: fi.description || null,
          place: fi.place || null,
          view_url: fi.view_url || null,
          payment_url: fi.payment_url || null,
          overdue: fi['overdue?'] || null,
          has_third_reminder: hasThird,
          list_polecony_sent_date: null,
          list_polecony_ignored_date: null,
        }
      })

      const { error: invoiceError } = await supabase.from('invoices').upsert(invoices)
      if (invoiceError) throw invoiceError

      totalInvoices += invoices.length
      console.log(`[Sync] ✓ Page ${page}: Saved ${invoices.length} invoices (total: ${totalInvoices})`)

      page++
      // Rate limit: 1 req/sec
      await new Promise(resolve => setTimeout(resolve, 1000))
    }

    console.log(`[Sync] ✓ Streaming complete: ${totalInvoices} invoices, ${totalClients} clients`)

    // STEP 3: Fetch client notes from Fakturownia
    console.log('[Sync] STEP 3: Fetching client notes from Fakturownia...')
    const fakturowniaClients = await fetchAllClients(fakturowniaApiToken)

    const clientNotesMap = new Map<number, string>()
    for (const fc of fakturowniaClients) {
      if (fc.note) {
        clientNotesMap.set(fc.id, fc.note)
      }
    }
    console.log(`[Sync] ✓ Fetched notes for ${clientNotesMap.size} clients from Fakturownia`)

    // STEP 4: Calculate total_unpaid for all clients
    console.log('[Sync] STEP 4: Calculating total_unpaid for all clients from Supabase invoices...')

    const { data: allInvoices, error: fetchError } = await supabase
      .from('invoices')
      .select('client_id, total, number')

    if (fetchError) {
      console.error('[Sync] Warning: Could not fetch invoices for totals:', fetchError)
      console.log('[Sync] Skipping total_unpaid update')
    } else {
      // Aggregate totals per client (excluding FK - corrective invoices)
      const clientTotalsMap = new Map<number, number>()

      for (const inv of allInvoices || []) {
        if (inv.client_id) {
          // Skip corrective invoices (FK prefix) - they shouldn't affect total_unpaid
          const isCorrectiveInvoice = inv.number && inv.number.startsWith('FK')
          if (!isCorrectiveInvoice) {
            const current = clientTotalsMap.get(inv.client_id) || 0
            clientTotalsMap.set(inv.client_id, current + (inv.total || 0))
          }
        }
      }

      console.log(`[Sync] ✓ Calculated totals for ${clientTotalsMap.size} clients, updating...`)

      // Fetch existing clients to preserve their data
      const { data: existingClients } = await supabase
        .from('clients')
        .select('*')

      const clientsToUpdate: Client[] = (existingClients || []).map((client: any) => ({
        ...client,
        note: clientNotesMap.get(client.id) || client.note || null,
        total_unpaid: clientTotalsMap.get(client.id) || 0,
        updated_at: new Date().toISOString(),
      }))

      const { error: updateError } = await supabase.from('clients').upsert(clientsToUpdate)
      if (updateError) throw updateError

      console.log('[Sync] ✓ Client totals and notes updated')
    }

    const duration = ((Date.now() - startTime) / 1000).toFixed(2)
    console.log(`[Sync] Synchronization complete in ${duration}s`)

    // Send success SMS
    await sendSMS(
      `FULL SYNC COMPLETE! ${totalInvoices} invoices, ${totalClients} clients in ${duration}s`,
      smsFrom,
      smsToken
    )

    return new Response(
      JSON.stringify({
        success: true,
        data: {
          synced_clients: totalClients,
          synced_invoices: totalInvoices,
          duration_seconds: parseFloat(duration),
        },
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    )
  } catch (error: any) {
    console.error('[Sync] Error:', error)

    // Send SMS alert on failure
    try {
      const smsFrom = Deno.env.get('SMSPLANET_FROM') || 'Cbb-Office'
      const smsToken = Deno.env.get('SMSPLANET_API_TOKEN')!
      await sendSMS(
        `FULL SYNC FAILED: ${error.message.slice(0, 120)}`,
        smsFrom,
        smsToken
      )
    } catch (smsError) {
      console.error('[Sync] SMS alert failed:', smsError)
    }

    return new Response(
      JSON.stringify({
        success: false,
        error: error.message || 'Synchronization failed',
      }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }
})
