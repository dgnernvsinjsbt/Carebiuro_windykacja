import { NextRequest, NextResponse } from 'next/server';
import { fakturowniaApi } from '@/lib/fakturownia';
import { clientsDb, invoicesDb } from '@/lib/supabase';
import { Invoice } from '@/types';

// Force dynamic rendering - don't evaluate at build time
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { invoice_ids, client_id } = body;

    if (!invoice_ids || !Array.isArray(invoice_ids) || !client_id) {
      return NextResponse.json(
        { success: false, error: 'invoice_ids (array) and client_id required' },
        { status: 400 }
      );
    }

    console.log(`[ManualImport] Importing ${invoice_ids.length} invoices for client ${client_id}`);

    // Fetch and insert client
    const clientData = await fakturowniaApi.getClient(client_id);
    await clientsDb.upsert({
      id: clientData.id,
      name: clientData.name || `Client ${clientData.id}`,
      first_name: null,
      last_name: null,
      email: clientData.email || null,
      phone: clientData.phone || null,
      total_unpaid: 0,
      note: clientData.note || null,
      list_polecony: null,
      updated_at: new Date().toISOString(),
    });

    console.log(`[ManualImport] Client ${client_id} inserted/updated`);

    // Fetch and insert invoices
    const invoices: Invoice[] = [];
    for (const invoiceId of invoice_ids) {
      const inv = await fakturowniaApi.getInvoice(invoiceId);
      
      const invoice: Invoice = {
        id: inv.id,
        client_id: inv.client_id,
        number: inv.number,
        total: parseFloat(inv.price_gross) || 0,
        status: inv.status,
        comment: inv.internal_note || null,
        email_status: inv.email_status || null,
        sent_time: inv.sent_time || null,
        updated_at: inv.updated_at,
        issue_date: inv.issue_date || null,
        sell_date: inv.sell_date || null,
        payment_to: inv.payment_to || null,
        paid_date: inv.paid_date || null,
        created_at: inv.created_at || null,
        price_net: parseFloat(inv.price_net) || null,
        price_tax: parseFloat(inv.price_tax) || null,
        paid: parseFloat(inv.paid) || null,
        currency: inv.currency || null,
        payment_type: inv.payment_type || null,
        buyer_name: inv.buyer_name || null,
        buyer_email: inv.buyer_email || null,
        buyer_phone: inv.buyer_phone || null,
        buyer_tax_no: inv.buyer_tax_no || null,
        buyer_street: inv.buyer_street || null,
        buyer_city: inv.buyer_city || null,
        buyer_post_code: inv.buyer_post_code || null,
        buyer_country: inv.buyer_country || null,
        kind: inv.kind || null,
        description: inv.description || null,
        place: inv.place || null,
        view_url: inv.view_url || null,
        payment_url: inv.payment_url || null,
        overdue: inv['overdue?'] || null,

        // Optimization flags
        has_third_reminder: null,
        list_polecony_sent_date: null,
        list_polecony_ignored_date: null,
      };

      invoices.push(invoice);
      console.log(`[ManualImport] Invoice ${invoiceId} (${inv.number}): €${inv.price_gross} paid=${inv.paid}`);
    }

    await invoicesDb.bulkUpsert(invoices);

    console.log(`[ManualImport] Successfully imported ${invoices.length} invoices`);

    return NextResponse.json({
      success: true,
      data: {
        client_id,
        imported_invoices: invoices.length,
        invoices: invoices.map(i => ({ id: i.id, number: i.number, total: i.total, paid: i.paid })),
      },
    });
  } catch (error: any) {
    console.error('[ManualImport] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
