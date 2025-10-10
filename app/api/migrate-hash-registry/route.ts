import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';

/**
 * One-time migration to create invoice_hash_registry table
 *
 * POST /api/migrate-hash-registry
 */
export async function POST() {
  try {
    console.log('[Migration] Creating invoice_hash_registry table...');

    // Create table using raw SQL
    const { error: createError } = await supabaseAdmin().rpc('execute_sql', {
      sql: `
        -- Invoice Hash Registry: Persistent storage for invoice hash verification
        CREATE TABLE IF NOT EXISTS invoice_hash_registry (
          invoice_id INTEGER PRIMARY KEY,
          expected_hash TEXT NOT NULL,
          first_action_date TIMESTAMP NOT NULL,
          last_verified_date TIMESTAMP,
          created_at TIMESTAMP DEFAULT NOW(),
          updated_at TIMESTAMP DEFAULT NOW()
        );

        -- Index for looking up invoices by hash
        CREATE INDEX IF NOT EXISTS idx_hash_lookup ON invoice_hash_registry(expected_hash);

        -- Index for cleanup queries
        CREATE INDEX IF NOT EXISTS idx_first_action_date ON invoice_hash_registry(first_action_date);
      `,
    });

    if (createError) {
      console.error('[Migration] Failed to create table:', createError);

      // Try alternative approach without RPC
      const { error: altError } = await supabaseAdmin()
        .from('invoice_hash_registry')
        .select('invoice_id')
        .limit(1);

      if (altError && altError.code === '42P01') {
        // Table doesn't exist - create it manually
        return NextResponse.json({
          success: false,
          error: 'Table does not exist and RPC failed. Please create manually in Supabase SQL Editor.',
          sql: `
CREATE TABLE IF NOT EXISTS invoice_hash_registry (
  invoice_id INTEGER PRIMARY KEY,
  expected_hash TEXT NOT NULL,
  first_action_date TIMESTAMP NOT NULL,
  last_verified_date TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hash_lookup ON invoice_hash_registry(expected_hash);
CREATE INDEX IF NOT EXISTS idx_first_action_date ON invoice_hash_registry(first_action_date);
          `,
        });
      }

      // Table might already exist
      console.log('[Migration] Table might already exist, checking...');
    }

    // Verify table exists
    const { data, error: verifyError } = await supabaseAdmin()
      .from('invoice_hash_registry')
      .select('invoice_id')
      .limit(1);

    if (verifyError) {
      console.error('[Migration] Verification failed:', verifyError);
      return NextResponse.json(
        {
          success: false,
          error: `Verification failed: ${verifyError.message}`,
          hint: 'Please create the table manually in Supabase SQL Editor using the SQL in the migrations folder.',
        },
        { status: 500 }
      );
    }

    console.log('[Migration] ✅ Table invoice_hash_registry exists and is accessible');

    return NextResponse.json({
      success: true,
      message: 'invoice_hash_registry table created successfully',
      row_count: data?.length || 0,
    });
  } catch (error: any) {
    console.error('[Migration] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
