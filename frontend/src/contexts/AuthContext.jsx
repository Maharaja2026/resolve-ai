"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { createClient } from "@/lib/supabase";
import { api } from "@/services/api";
import { isStaffRole } from "@/lib/utils";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const supabase = useMemo(() => createClient(), []);
  const [session, setSession] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const profileRef = useRef(null);
  const loadedUserIdRef = useRef(null);

  useEffect(() => {
    profileRef.current = profile;
  }, [profile]);

  const refreshProfile = useCallback(async ({ quiet = false } = {}) => {
    const { data } = await supabase.auth.getSession();
    if (!data.session?.access_token) {
      setProfile(null);
      profileRef.current = null;
      loadedUserIdRef.current = null;
      return null;
    }
    if (!quiet) setProfileLoading(true);
    try {
      const me = await api.getMe();
      setProfile(me);
      profileRef.current = me;
      loadedUserIdRef.current = data.session.user?.id ?? null;
      return me;
    } catch {
      if (!quiet) {
        setProfile(null);
        profileRef.current = null;
      }
      return null;
    } finally {
      if (!quiet) setProfileLoading(false);
    }
  }, [supabase]);

  useEffect(() => {
    let mounted = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      setSession(data.session);
      setUser(data.session?.user ?? null);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, nextSession) => {
      if (!mounted) return;

      // Keep session/token fresh, but do not force a profile reload flash.
      if (event === "TOKEN_REFRESHED") {
        setSession(nextSession);
        setUser(nextSession?.user ?? null);
        return;
      }

      setSession(nextSession);
      setUser(nextSession?.user ?? null);
      setLoading(false);

      if (event === "SIGNED_OUT") {
        setProfile(null);
        profileRef.current = null;
        loadedUserIdRef.current = null;
      }
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, [supabase]);

  useEffect(() => {
    if (loading) return;

    const userId = session?.user?.id ?? null;
    if (!userId) {
      setProfile(null);
      profileRef.current = null;
      loadedUserIdRef.current = null;
      return;
    }

    // Skip reload when navigating / focusing tabs for the same signed-in user.
    if (loadedUserIdRef.current === userId && profileRef.current) {
      return;
    }

    refreshProfile({ quiet: Boolean(profileRef.current) });
  }, [session?.user?.id, loading, refreshProfile]);

  const login = useCallback(
    async (email, password) => {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (error) throw error;
      return data;
    },
    [supabase],
  );

  const register = useCallback(
    async (email, password, metadata = {}) => {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: { data: metadata },
      });
      if (error) throw error;
      return data;
    },
    [supabase],
  );

  const logout = useCallback(async () => {
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
    setProfile(null);
    profileRef.current = null;
    loadedUserIdRef.current = null;
  }, [supabase]);

  const resetPassword = useCallback(
    async (email) => {
      const redirectTo =
        typeof window !== "undefined"
          ? `${window.location.origin}/login`
          : undefined;
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo,
      });
      if (error) throw error;
    },
    [supabase],
  );

  const role = profile?.role ?? "customer";

  const value = useMemo(
    () => ({
      session,
      user,
      loading,
      profile,
      profileLoading,
      role,
      isStaff: isStaffRole(role),
      isAdmin: role === "admin",
      login,
      register,
      logout,
      resetPassword,
      refreshProfile,
      isAuthenticated: Boolean(session?.user),
    }),
    [
      session,
      user,
      loading,
      profile,
      profileLoading,
      role,
      login,
      register,
      logout,
      resetPassword,
      refreshProfile,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
