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
      sess
        ? async () => {
            const { data } = await supabase.auth.getSession();
            return data.session?.access_token ?? null;
          }
        : null,
    );
  }, []);

  useEffect(() => {
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
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: getRedirectTo() },
    });
    if (error) {
      throw new Error(error.message);
    }
  }, [getRedirectTo]);

  const signInWithGitHub = useCallback(async () => {
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
