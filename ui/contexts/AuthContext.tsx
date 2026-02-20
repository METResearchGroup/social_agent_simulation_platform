'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import type { Session, User } from '@supabase/supabase-js';
import { supabase } from '@/lib/supabase';
import { setAuthTokenGetter, setOnUnauthorized } from '@/lib/api/simulation';

interface AuthContextValue {
  user: User | null;
  session: Session | null;
  isLoading: boolean;
  signInWithGoogle: () => Promise<void>;
  signInWithGitHub: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const updateAuthState = useCallback((sess: Session | null) => {
    setSession(sess);
    setUser(sess?.user ?? null);
    setAuthTokenGetter(
      sess?.access_token
        ? () => Promise.resolve(sess.access_token)
        : null,
    );
  }, []);

  useEffect(() => {
    void supabase.auth.getSession().then(({ data: { session: sess } }) => {
      updateAuthState(sess);
      setIsLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, sess) => {
      updateAuthState(sess);
    });

    setOnUnauthorized(() => {
      void supabase.auth.signOut();
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
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: getRedirectTo() },
    });
  }, [getRedirectTo]);

  const signInWithGitHub = useCallback(async () => {
    await supabase.auth.signInWithOAuth({
      provider: 'github',
      options: { redirectTo: getRedirectTo() },
    });
  }, [getRedirectTo]);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
  }, []);

  const value: AuthContextValue = {
    user,
    session,
    isLoading,
    signInWithGoogle,
    signInWithGitHub,
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
