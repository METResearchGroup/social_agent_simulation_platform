'use client';

import Link from 'next/link';
import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { isSupabaseConfigured, supabase } from '@/lib/supabase';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

const DEFAULT_MISSING_CODE_MESSAGE: string = 'Missing authorization code';

const loadingView = (
  <div className="flex min-h-screen flex-col items-center justify-center gap-2 text-beige-600">
    <LoadingSpinner />
    <span className="text-sm">Completing sign-in…</span>
  </div>
);

function _errorMessageFromHash(hash: string): string | null {
  // Supabase may redirect back with error info in the URL hash fragment.
  // Example: #error=access_denied&error_description=...
  const raw = hash.startsWith('#') ? hash.slice(1) : hash;
  if (!raw) return null;
  const params = new URLSearchParams(raw);
  const errorDescription = params.get('error_description');
  const errorCode = params.get('error');
  if (errorDescription) return errorDescription;
  if (errorCode) return `OAuth error: ${errorCode}`;
  return null;
}

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const code = searchParams.get('code');
  const oauthError = searchParams.get('error');
  const oauthErrorDescription = searchParams.get('error_description');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async (): Promise<void> => {
      if (!isSupabaseConfigured) {
        setError(
          'Supabase OAuth is not configured for this deployment. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY and redeploy.',
        );
        return;
      }

      // Some providers (or user cancel) return errors as query params.
      if (oauthErrorDescription || oauthError) {
        setError(oauthErrorDescription ?? `OAuth error: ${oauthError}`);
        return;
      }

      // PKCE flow: Supabase returns ?code=... which must be exchanged for a session.
      if (code) {
        const { error: exchangeError } =
          await supabase.auth.exchangeCodeForSession(code);
        if (exchangeError) {
          setError(exchangeError.message);
          return;
        }
        router.replace('/');
        return;
      }

      // Implicit/hash flow: allow supabase-js to detect session from URL hash.
      // If tokens are present, getSession() should populate local storage.
      const { data, error: sessionError } = await supabase.auth.getSession();
      if (sessionError) {
        setError(sessionError.message);
        return;
      }
      if (data.session) {
        router.replace('/');
        return;
      }

      const hashError = _errorMessageFromHash(window.location.hash);
      setError(hashError ?? DEFAULT_MISSING_CODE_MESSAGE);
    };

    void run();
  }, [code, oauthError, oauthErrorDescription, router]);

  if (!code && error == null) {
    return loadingView;
  }

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-8 text-beige-800">
        <p className="text-sm font-medium">Sign-in failed</p>
        <p className="text-sm">{error}</p>
        <Link
          href="/"
          className="text-sm font-medium text-accent hover:text-accent-hover"
        >
          Return to sign in
        </Link>
      </div>
    );
  }

  return loadingView;
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={loadingView}>
      <AuthCallbackContent />
    </Suspense>
  );
}
