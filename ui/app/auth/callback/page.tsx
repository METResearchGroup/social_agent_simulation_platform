'use client';

import Link from 'next/link';
import { Suspense, useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

const loadingView = (
  <div className="flex min-h-screen flex-col items-center justify-center gap-2 text-beige-600">
    <LoadingSpinner />
    <span className="text-sm">Completing sign-in…</span>
  </div>
);

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { completeOAuthCallback } = useAuth();
  const code = searchParams.get('code');
  const oauthError = searchParams.get('error');
  const oauthErrorDescription = searchParams.get('error_description');
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef<number>(0);

  useEffect(() => {
    requestIdRef.current += 1;
    const requestId = requestIdRef.current;

    const run = async (): Promise<void> => {
      const result = await completeOAuthCallback({
        code,
        oauthError,
        oauthErrorDescription,
        hash: typeof window === 'undefined' ? '' : window.location.hash,
      });

      if (requestId !== requestIdRef.current) return;

      if (result.ok) {
        router.replace('/');
        return;
      }

      setError(result.message);
    };

    void run();
  }, [code, completeOAuthCallback, oauthError, oauthErrorDescription, router]);

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
