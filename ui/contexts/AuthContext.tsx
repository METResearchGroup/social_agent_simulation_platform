'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import type { Session, User } from '@supabase/supabase-js';
import { isSupabaseConfigured, supabase } from '@/lib/supabase';
import { setAuthTokenGetter, setOnUnauthorized } from '@/lib/api/simulation';
import { DISABLE_AUTH } from '@/lib/env';

/** Mock user when DISABLE_AUTH is set. */
const MOCK_DEV_USER: User = {
  id: 'dev-user-id',
  app_metadata: {},
  user_metadata: {},
  aud: 'authenticated',
  created_at: new Date().toISOString(),
} as User;

interface AuthContextValue {
  user: User | null;
  session: Session | null;
  isLoading: boolean;
  isAuthConfigured: boolean;
  signInWithGoogle: () => Promise<void>;
  signInWithGitHub: () => Promise<void>;
  completeOAuthCallback: (input: {
    code: string | null;
    oauthError: string | null;
    oauthErrorDescription: string | null;
    hash: string;
  }) => Promise<{ ok: true } | { ok: false; message: string }>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const isAuthConfigured: boolean = DISABLE_AUTH || isSupabaseConfigured;
  const [user, setUser] = useState<User | null>(DISABLE_AUTH ? MOCK_DEV_USER : null);
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(
    () => !DISABLE_AUTH && isSupabaseConfigured,
  );

  const updateAuthState = useCallback((sess: Session | null) => {
    setSession(sess);
    setUser(sess?.user ?? null);
    setAuthTokenGetter(
      sess
        ? async () => {
            const { data } = await supabase.auth.getSession();
            return data.session?.access_token ?? null;
          }
        : null,
    );
  }, []);

  useEffect(() => {
    if (DISABLE_AUTH) {
      setAuthTokenGetter(null);
      setOnUnauthorized(null);
      return;
    }

    if (!isSupabaseConfigured) {
      setAuthTokenGetter(null);
      setOnUnauthorized(null);
      return;
    }

    void supabase.auth.getSession().then(({ data, error }) => {
      if (error) {
        updateAuthState(null);
        setIsLoading(false);
        return;
      }

      updateAuthState(data.session);
      setIsLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, sess) => {
      updateAuthState(sess);
    });

    setOnUnauthorized(() => {
      supabase.auth.signOut().catch(() => {
        updateAuthState(null);
      });
    });

    return () => {
      subscription.unsubscribe();
      setAuthTokenGetter(null);
      setOnUnauthorized(null);
    };
  }, [updateAuthState]);

  const getRedirectTo = useCallback((): string => {
    if (typeof window === 'undefined') return '';
    return `${window.location.origin}/auth/callback`;
  }, []);

  const signInWithGoogle = useCallback(async () => {
    if (!isSupabaseConfigured) {
      throw new Error(
        'Supabase OAuth is not configured. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in the deployment environment and redeploy.',
      );
    }
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: getRedirectTo() },
    });
    if (error) {
      throw new Error(error.message);
    }
  }, [getRedirectTo]);

  const signInWithGitHub = useCallback(async () => {
    if (!isSupabaseConfigured) {
      throw new Error(
        'Supabase OAuth is not configured. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in the deployment environment and redeploy.',
      );
    }
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'github',
      options: { redirectTo: getRedirectTo() },
    });
    if (error) {
      throw new Error(error.message);
    }
  }, [getRedirectTo]);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
  }, []);

  const completeOAuthCallback = useCallback(
    async (input: {
      code: string | null;
      oauthError: string | null;
      oauthErrorDescription: string | null;
      hash: string;
    }): Promise<{ ok: true } | { ok: false; message: string }> => {
      if (input.oauthErrorDescription || input.oauthError) {
        return {
          ok: false,
          message: input.oauthErrorDescription ?? `OAuth error: ${input.oauthError}`,
        };
      }

      const rawHash = input.hash.startsWith('#') ? input.hash.slice(1) : input.hash;
      if (rawHash) {
        const params = new URLSearchParams(rawHash);
        const hashErrorDescription = params.get('error_description');
        const hashErrorCode = params.get('error');
        if (hashErrorDescription) return { ok: false, message: hashErrorDescription };
        if (hashErrorCode) return { ok: false, message: `OAuth error: ${hashErrorCode}` };
      }

      if (DISABLE_AUTH) {
        return { ok: true };
      }

      if (!isSupabaseConfigured) {
        return {
          ok: false,
          message:
            'Supabase OAuth is not configured for this deployment. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY and redeploy.',
        };
      }

      if (input.code) {
        const { error: exchangeError } = await supabase.auth.exchangeCodeForSession(input.code);
        if (exchangeError) {
          return { ok: false, message: exchangeError.message };
        }
        const { data, error: sessionError } = await supabase.auth.getSession();
        if (sessionError) {
          return { ok: false, message: sessionError.message };
        }
        updateAuthState(data.session);
        return { ok: true };
      }

      const { data, error: sessionError } = await supabase.auth.getSession();
      if (sessionError) {
        return { ok: false, message: sessionError.message };
      }
      if (data.session) {
        updateAuthState(data.session);
        return { ok: true };
      }

      return { ok: false, message: 'Missing authorization code' };
    },
    [updateAuthState],
  );

  const value: AuthContextValue = {
    user,
    session,
    isLoading,
    isAuthConfigured,
    signInWithGoogle,
    signInWithGitHub,
    completeOAuthCallback,
    signOut,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (ctx == null) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}
