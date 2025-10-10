import { NextRequest, NextResponse } from 'next/server';
import { fakturowniaApi } from '@/lib/fakturownia';
import { invoicesDb } from '@/lib/supabase';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

/**
 * POST /api/sync/test
 * Test synchronization: Syncs ONLY client 211779362
 * Used for testing GitHub Actions integration
 */
export async function POST(request: NextRequest) {
  try {
    // Auth: Accept GitHub Actions or Vercel Cron
    const isVercelCron = request.headers.get('x-vercel-cron') === '1';
    const isGitHubAction = request.headers.get('x-github-action') === 'true';

    if (!isVercelCron && !isGitHubAction) {
      console.error('[TestSync] Unauthorized: Not from Vercel Cron or GitHub Actions');
      return NextResponse.json(
        { success: false, error: 'Unauthorized' },
        { status: 401 }
      );
    }

    console.log('[TestSync] Starting test sync for client 211779362...');
    const startTime = Date.now();

    const TEST_CLIENT_ID = 211779362;

    // Fetch invoices for test client only
    const clientInvoices = await fakturowniaApi.getInvoicesByClientId(TEST_CLIENT_ID);
    console.log(`[TestSync] Fetched ${clientInvoices.length} invoices for client ${TEST_CLIENT_ID}`);

    if (clientInvoices.length === 0) {
      console.warn('[TestSync] No invoices found for test client');

      // Send SMS even if no invoices
      try {
        const smsFormData = new URLSearchParams();
        smsFormData.append('from', process.env.SMSPLANET_FROM || 'Carebiuro');
        smsFormData.append('to', '+48536214664');
        smsFormData.append('msg', 'TEST SYNC: No invoices found for client 211779362');

        await fetch('https://api2.smsplanet.pl/sms', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': `Bearer ${process.env.SMSPLANET_API_TOKEN}`,
          },
          body: smsFormData.toString(),
        });
      } catch (smsError) {
        console.error('[TestSync] SMS alert failed:', smsError);
      }

      return NextResponse.json({
        success: true,
        message: 'No invoices found for test client',
        data: {
          client_id: TEST_CLIENT_ID,
          synced_invoices: 0,
          duration_seconds: ((Date.now() - startTime) / 1000).toFixed(2)
        }
      });
    }

    // Transform invoices (same logic as full sync)
    const invoices = clientInvoices.map((fi: any) => ({
        id: fi.id,
        client_id: fi.client_id,
        number: fi.number,
        total: parseFloat(fi.price_gross) || 0,
        status: fi.status,
        internal_note: fi.internal_note || null,
        email_status: fi.email_status || null,
        sent_time: fi.sent_time || null,
        updated_at: fi.updated_at,

        // Core invoice dates
        issue_date: fi.issue_date || null,
        sell_date: fi.sell_date || null,
        payment_to: fi.payment_to || null,
        paid_date: fi.paid_date || null,
        created_at: fi.created_at || null,

        // Financial data
        price_net: parseFloat(fi.price_net) || null,
        price_tax: parseFloat(fi.price_tax) || null,
        paid: parseFloat(fi.paid) || null,
        outstanding: (parseFloat(fi.price_gross) || 0) - (parseFloat(fi.paid) || 0),
        currency: fi.currency || null,
        payment_type: fi.payment_type || null,

        // Buyer information
        buyer_name: fi.buyer_name || null,
        buyer_email: fi.buyer_email || null,
        buyer_phone: fi.buyer_phone || null,
        buyer_tax_no: fi.buyer_tax_no || null,
        buyer_street: fi.buyer_street || null,
        buyer_city: fi.buyer_city || null,
        buyer_post_code: fi.buyer_post_code || null,
        buyer_country: fi.buyer_country || null,

        // Document metadata
        kind: fi.kind || null,
        description: fi.description || null,
        place: fi.place || null,
        view_url: fi.view_url || null,
        payment_url: fi.payment_url || null,

        // Status fields
        overdue: fi['overdue?'] || null,
      }
    ));

    // Upsert to Supabase
    await invoicesDb.bulkUpsert(invoices);

    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
    console.log(`[TestSync] Complete in ${duration}s`);

    // Send SUCCESS SMS
    try {
      const smsFormData = new URLSearchParams();
      smsFormData.append('from', process.env.SMSPLANET_FROM || 'Carebiuro');
      smsFormData.append('to', '+48536214664');
      smsFormData.append('msg', `TEST SYNC OK: ${invoices.length} invoices in ${duration}s`);

      await fetch('https://api2.smsplanet.pl/sms', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': `Bearer ${process.env.SMSPLANET_API_TOKEN}`,
        },
        body: smsFormData.toString(),
      });
    } catch (smsError) {
      console.error('[TestSync] SMS alert failed:', smsError);
    }

    return NextResponse.json({
      success: true,
      data: {
        client_id: TEST_CLIENT_ID,
        synced_invoices: invoices.length,
        duration_seconds: parseFloat(duration),
      },
    });

  } catch (error: any) {
    console.error('[TestSync] Error:', error);

    // Send FAILURE SMS
    try {
      const smsFormData = new URLSearchParams();
      smsFormData.append('from', process.env.SMSPLANET_FROM || 'Carebiuro');
      smsFormData.append('to', '+48536214664');
      smsFormData.append('msg', `TEST SYNC FAIL: ${error.message.slice(0, 120)}`);

      await fetch('https://api2.smsplanet.pl/sms', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': `Bearer ${process.env.SMSPLANET_API_TOKEN}`,
        },
        body: smsFormData.toString(),
      });
    } catch (smsError) {
      console.error('[TestSync] SMS alert failed:', smsError);
    }

    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
