#!/usr/bin/env node

/**
 * Run migration 003: Fix timezone handling
 *
 * This script converts the sent_at column from TIMESTAMP to TIMESTAMPTZ
 * to properly handle timezone information.
 */

const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');
const path = require('path');

// Load environment variables
require('dotenv').config({ path: '.env.local' });

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error('❌ Missing Supabase credentials in .env.local');
  console.error('   Need: NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY');
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

async function runMigration() {
  console.log('🔄 Running migration 003: Fix timezone handling...\n');

  try {
    // Step 1: Check current column type
    console.log('1️⃣ Checking current column type...');
    const { data: beforeCheck, error: beforeError } = await supabase
      .rpc('exec_sql', {
        query: `
          SELECT column_name, data_type, column_default
          FROM information_schema.columns
          WHERE table_name = 'message_history' AND column_name = 'sent_at'
        `
      });

    if (beforeError) {
      // If RPC doesn't exist, we'll need to use alternative method
      console.log('   Note: Direct SQL execution via RPC not available');
      console.log('   Please run the migration manually in Supabase SQL Editor');
      console.log('\n📋 SQL to execute:');
      const sqlFile = fs.readFileSync(
        path.join(__dirname, '../migrations/003_fix_timezone.sql'),
        'utf-8'
      );
      console.log(sqlFile);
      console.log('\n📝 Instructions:');
      console.log('   1. Go to Supabase Dashboard > SQL Editor');
      console.log('   2. Copy and paste the SQL above');
      console.log('   3. Click "Run"');
      process.exit(0);
    }

    console.log('   Current type:', beforeCheck);

    // Step 2: Perform migration
    console.log('\n2️⃣ Converting TIMESTAMP to TIMESTAMPTZ...');

    const { error: alterError } = await supabase
      .rpc('exec_sql', {
        query: `
          ALTER TABLE message_history
            ALTER COLUMN sent_at TYPE TIMESTAMPTZ
            USING sent_at AT TIME ZONE 'UTC';

          ALTER TABLE message_history
            ALTER COLUMN sent_at SET DEFAULT now();
        `
      });

    if (alterError) throw alterError;

    console.log('   ✅ Column type converted successfully');

    // Step 3: Verify change
    console.log('\n3️⃣ Verifying the change...');
    const { data: afterCheck, error: afterError } = await supabase
      .rpc('exec_sql', {
        query: `
          SELECT column_name, data_type, column_default
          FROM information_schema.columns
          WHERE table_name = 'message_history' AND column_name = 'sent_at'
        `
      });

    if (afterError) throw afterError;

    console.log('   New type:', afterCheck);

    // Step 4: Test with sample data
    console.log('\n4️⃣ Testing timezone handling...');
    const { data: testData, error: testError } = await supabase
      .from('message_history')
      .select('id, sent_at')
      .limit(1)
      .single();

    if (testError && testError.code !== 'PGRST116') { // PGRST116 = no rows
      throw testError;
    }

    if (testData) {
      console.log('   Sample record:', testData);
      console.log('   Parsed date:', new Date(testData.sent_at));
      console.log('   Local PL time:', new Date(testData.sent_at).toLocaleString('pl-PL', {
        timeZone: 'Europe/Warsaw'
      }));
    } else {
      console.log('   No records to test (table empty)');
    }

    console.log('\n✅ Migration completed successfully!');
    console.log('\n📝 Changes:');
    console.log('   • sent_at column: TIMESTAMP → TIMESTAMPTZ');
    console.log('   • Existing data converted from UTC');
    console.log('   • New records will use UTC with timezone info');
    console.log('\n🎯 Result: Times will now display correctly in Poland (UTC+1/+2)');

  } catch (error) {
    console.error('\n❌ Migration failed:', error.message);
    console.error('\n🔧 Manual migration required:');
    console.error('   Run this in Supabase SQL Editor:');
    const sqlFile = fs.readFileSync(
      path.join(__dirname, '../migrations/003_fix_timezone.sql'),
      'utf-8'
    );
    console.error('\n' + sqlFile);
    process.exit(1);
  }
}

runMigration();
