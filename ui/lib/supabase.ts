import { createClient, type SupabaseClient } from '@supabase/supabase-js';

/* Placeholders allow the app to load when env is unset; set NEXT_PUBLIC_SUPABASE_* for OAuth. */
const SUPABASE_URL: string =
  process.env.NEXT_PUBLIC_SUPABASE_URL ?? 'https://placeholder.supabase.co';
const SUPABASE_ANON_KEY: string =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? 'placeholder-key';

export const supabase: SupabaseClient = createClient(
  SUPABASE_URL,
  SUPABASE_ANON_KEY,
);
