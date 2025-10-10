import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';

/**
 * One-time migration to add outstanding column to invoices table
 *
 * POST /api/migrate-outstanding
 */
export async function POST() {
  try {
    console.log('[Migration] Adding outstanding column to invoices table...');

    const supabase = supabaseAdmin();

    // Step 1: Add column (Supabase might auto-add, but we'll update values)
    console.log('[Migration] Step 1: Updating outstanding values for all invoices...');

    // Fetch all invoices
    const { data: invoices, error: fetchError } = await supabase
      .from('invoices')
      .select('id, total, paid');

    if (fetchError) {
      throw new Error(`Failed to fetch invoices: ${fetchError.message}`);
    }

    console.log(`[Migration] Found ${invoices?.length || 0} invoices to update`);

    // Update each invoice with calculated outstanding
    let updatedCount = 0;
    const batchSize = 100;

    if (invoices && invoices.length > 0) {
      for (let i = 0; i < invoices.length; i += batchSize) {
        const batch = invoices.slice(i, i + batchSize);

        const updates = batch.map((inv) => ({
          id: inv.id,
          outstanding: (inv.total || 0) - (inv.paid || 0),
        }));

        const { error: updateError } = await supabase
          .from('invoices')
          .upsert(updates);

        if (updateError) {
          console.error(`[Migration] Error updating batch ${i / batchSize + 1}:`, updateError);
        } else {
          updatedCount += updates.length;
          console.log(`[Migration] Updated batch ${i / batchSize + 1}: ${updates.length} invoices`);
        }
      }
    }

    console.log(`[Migration] ✅ Successfully updated ${updatedCount} invoices`);

    return NextResponse.json({
      success: true,
      message: 'outstanding column migration completed',
      invoices_updated: updatedCount,
    });
  } catch (error: any) {
    console.error('[Migration] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
