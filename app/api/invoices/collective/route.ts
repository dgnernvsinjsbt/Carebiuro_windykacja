import { NextRequest, NextResponse } from 'next/server';
import { fakturowniaApi } from '@/lib/fakturownia';
import { supabase, invoicesDb } from '@/lib/supabase';
import { Invoice, FakturowniaInvoice } from '@/types';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { invoice_ids, client_id } = body;

    if (!invoice_ids || !Array.isArray(invoice_ids) || invoice_ids.length === 0) {
      return NextResponse.json(
        { success: false, error: 'invoice_ids array is required and must not be empty' },
        { status: 400 }
      );
    }

    if (!client_id) {
      return NextResponse.json(
        { success: false, error: 'client_id is required' },
        { status: 400 }
      );
    }

    console.log(`[CollectiveInvoice] Creating collective invoice for ${invoice_ids.length} invoices`);

    // Fetch invoice details from Supabase
    const { data: invoices, error } = await supabase
      .from('invoices')
      .select('id, number, total, paid')
      .in('id', invoice_ids);

    if (error || !invoices) {
      console.error('[CollectiveInvoice] Error fetching invoices:', error);
      return NextResponse.json(
        { success: false, error: 'Failed to fetch invoice details' },
        { status: 500 }
      );
    }

    // Create positions for each invoice
    const positions = invoices.map((inv) => {
      const balance = (inv.total ?? 0) - (inv.paid ?? 0);
      return {
        name: `Faktura ${inv.number}`,
        quantity: 1,
        total_price_gross: balance.toFixed(2),
        tax: 0, // Odwrotne obciążenie
      };
    });

    const today = new Date().toISOString().split('T')[0];

    // Create invoice via Fakturownia API
    const payload = {
      api_token: process.env.FAKTUROWNIA_API_TOKEN,
      invoice: {
        kind: 'proforma',
        client_id: client_id,
        place: 'Chocianów',
        sell_date: today,
        issue_date: today,
        payment_to_kind: 7, // 7 days
        description: 'Odwrotne obciążenie',
        buyer_person: '', // Ukrywa pole "Imię i nazwisko odbiorcy"
        positions: positions,
      },
    };

    console.log('[CollectiveInvoice] Creating invoice with positions:', positions.length);
    console.log('[CollectiveInvoice] Payload:', JSON.stringify(payload, null, 2));

    const createdInvoice = await fakturowniaApi.fakturowniaRequest(
      '/invoices.json',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );

    console.log('[CollectiveInvoice] Response from Fakturownia:', JSON.stringify(createdInvoice, null, 2));
    console.log(`[CollectiveInvoice] Created invoice: ${createdInvoice.number} (ID: ${createdInvoice.id})`);

    // Cancel selected invoices that were included in the collective invoice
    console.log(`[CollectiveInvoice] Canceling ${invoice_ids.length} original invoices...`);
    const canceledInvoices: number[] = [];

    for (const invoiceId of invoice_ids) {
      try {
        await fakturowniaApi.fakturowniaRequest(
          '/invoices/cancel.json',
          {
            method: 'POST',
            body: JSON.stringify({
              api_token: process.env.FAKTUROWNIA_API_TOKEN,
              cancel_invoice_id: invoiceId,
              cancel_reason: `Zastąpiona fakturą zbiorczą ${createdInvoice.number}`,
            }),
          }
        );
        canceledInvoices.push(invoiceId);
        console.log(`[CollectiveInvoice] ✓ Canceled invoice ID ${invoiceId}`);
      } catch (err: any) {
        console.error(`[CollectiveInvoice] Failed to cancel invoice ${invoiceId}:`, err.message);
      }
    }

    console.log(`[CollectiveInvoice] ✓ Canceled ${canceledInvoices.length}/${invoice_ids.length} invoices`);

    return NextResponse.json({
      success: true,
      data: {
        invoice_id: createdInvoice.id,
        invoice_number: createdInvoice.number,
        total: createdInvoice.price_gross,
        view_url: createdInvoice.view_url,
        canceled_invoices: canceledInvoices.length,
        client_id: client_id,
      },
    });
  } catch (error: any) {
    console.error('[CollectiveInvoice] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to create collective invoice' },
      { status: 500 }
    );
  }
}
