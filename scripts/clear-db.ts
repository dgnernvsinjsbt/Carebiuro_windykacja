#!/usr/bin/env node
/**
 * Clear all data from Supabase (invoices and clients)
 * Use for testing or resetting the database
 */

import { clientsDb, invoicesDb } from '../lib/supabase';

async function clearDatabase() {
  try {
    console.log('🗑️  Clearing Supabase database...');

    console.log('Deleting all invoices...');
    await invoicesDb.deleteAll();
    console.log('✅ All invoices deleted');

    console.log('Deleting all clients...');
    await clientsDb.deleteAll();
    console.log('✅ All clients deleted');

    console.log('🎉 Database cleared successfully!');
  } catch (error) {
    console.error('❌ Error clearing database:', error);
    process.exit(1);
  }
}

clearDatabase();
