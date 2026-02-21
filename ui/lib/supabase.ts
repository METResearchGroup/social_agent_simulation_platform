import { createClient, type SupabaseClient } from '@supabase/supabase-js';

/* Placeholders allow the app to load when env is unset; set NEXT_PUBLIC_SUPABASE_* for OAuth. */
const SUPABASE_URL: string =
  process.env.NEXT_PUBLIC_SUPABASE_URL ?? 'https://placeholder.supabase.co';
const SUPABASE_ANON_KEY: string =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? 'placeholder-key';

if (
  SUPABASE_URL === 'https://placeholder.supabase.co' ||
  SUPABASE_ANON_KEY === 'placeholder-key'
) {
  console.warn(
    'NEXT_PUBLIC_SUPABASE_URL and/or NEXT_PUBLIC_SUPABASE_ANON_KEY are unset. OAuth will fail. Configure them in .env.local.',
  );
}

export const supabase: SupabaseClient = createClient(
  SUPABASE_URL,
  SUPABASE_ANON_KEY,
);
