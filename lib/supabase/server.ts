import { supabaseAdmin } from '../supabase';
import type { SupabaseClient } from '@supabase/supabase-js';

/**
 * Server-side Supabase client for React Server Components
 * Uses admin client to bypass RLS for template management
 */
export async function createClient(): Promise<SupabaseClient> {
  // Return admin client (already initialized in supabase.ts)
  return supabaseAdmin();
}
