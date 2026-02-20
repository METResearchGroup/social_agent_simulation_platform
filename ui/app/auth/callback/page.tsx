'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

export default function AuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const code = searchParams.get('code');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!code) return;

    const exchange = async (): Promise<void> => {
      const { error: exchangeError } =
        await supabase.auth.exchangeCodeForSession(code);
      if (exchangeError) {
        setError(exchangeError.message);
        return;
      }
      router.replace('/');
    };

    void exchange();
  }, [code, router]);

  if (!code) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-8 text-beige-800">
        <p className="text-sm font-medium">Sign-in failed</p>
        <p className="text-sm">Missing authorization code</p>
        <Link
          href="/"
          className="text-sm font-medium text-accent hover:text-accent-hover"
        >
          Return to sign in
        </Link>
      </div>
    );
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

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-2 text-beige-600">
      <LoadingSpinner />
      <span className="text-sm">Completing sign-in…</span>
    </div>
  );
}
