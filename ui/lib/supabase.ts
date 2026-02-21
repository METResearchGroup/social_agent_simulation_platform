import { createClient, type SupabaseClient } from '@supabase/supabase-js';

/* Placeholders allow the app to load when env is unset; set NEXT_PUBLIC_SUPABASE_* for OAuth. */
const PLACEHOLDER_SUPABASE_URL: string = 'https://placeholder.supabase.co';
const PLACEHOLDER_SUPABASE_ANON_KEY: string = 'placeholder-key';

const SUPABASE_URL: string =
  process.env.NEXT_PUBLIC_SUPABASE_URL ?? PLACEHOLDER_SUPABASE_URL;
const SUPABASE_ANON_KEY: string =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? PLACEHOLDER_SUPABASE_ANON_KEY;

if (
  SUPABASE_URL === PLACEHOLDER_SUPABASE_URL ||
  SUPABASE_ANON_KEY === PLACEHOLDER_SUPABASE_ANON_KEY
) {
  console.warn(
    'NEXT_PUBLIC_SUPABASE_URL and/or NEXT_PUBLIC_SUPABASE_ANON_KEY are unset. OAuth will fail. Configure them in .env.local.',
  );
}

export const isSupabaseConfigured: boolean =
  SUPABASE_URL !== PLACEHOLDER_SUPABASE_URL &&
  SUPABASE_ANON_KEY !== PLACEHOLDER_SUPABASE_ANON_KEY;

export const supabase: SupabaseClient = createClient(
  SUPABASE_URL,
  SUPABASE_ANON_KEY,
);
