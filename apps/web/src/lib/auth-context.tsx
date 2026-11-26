"use client";

import type { AuthTokenResponse, UserSummary } from "@go4guru/contracts";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { logoutAccount, refreshAuthSession } from "@/lib/api-client";

interface AuthContextValue {
  token: string | null;
  user: UserSummary | null;
  mfaRequired: boolean;
  initializing: boolean;
  setSession: (resp: AuthTokenResponse) => void;
  clearSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);
const SESSION_KEY = "go4guru_access_session_v1";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserSummary | null>(null);
  const [mfaRequired, setMfaRequired] = useState<boolean>(false);
  const [initializing, setInitializing] = useState<boolean>(true);

  const setSession = useCallback((resp: AuthTokenResponse) => {
    setToken(resp.access_token);
    setUser(resp.user);
    setMfaRequired(resp.mfa_required);
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(
        SESSION_KEY,
        JSON.stringify({
          access_token: resp.access_token,
          user: resp.user,
          mfa_required: resp.mfa_required,
        })
      );
    }
  }, []);

  const clearSession = useCallback(async () => {
    const activeToken = token;
    setToken(null);
    setUser(null);
    setMfaRequired(false);
    if (typeof window !== "undefined") {
      window.sessionStorage.removeItem(SESSION_KEY);
    }
    if (activeToken) {
      try {
        await logoutAccount(activeToken);
      } catch {
        // Best-effort server logout
      }
    }
  }, [token]);

  useEffect(() => {
    let active = true;
    async function restore() {
      if (typeof window !== "undefined") {
        const cached = window.sessionStorage.getItem(SESSION_KEY);
        if (cached) {
          try {
            const parsed = JSON.parse(cached) as {
              access_token: string;
              user: UserSummary;
              mfa_required: boolean;
            };
            if (active) {
              setToken(parsed.access_token);
              setUser(parsed.user);
              setMfaRequired(parsed.mfa_required);
              setInitializing(false);
              return;
            }
          } catch {
            window.sessionStorage.removeItem(SESSION_KEY);
          }
        }
      }
      try {
        const refreshed = await refreshAuthSession();
        if (active) {
          setSession(refreshed);
        }
      } catch {
        // No active refresh session cookie
      } finally {
        if (active) {
          setInitializing(false);
        }
      }
    }
    void restore();
    return () => {
      active = false;
    };
  }, [setSession]);

  return (
    <AuthContext.Provider
      value={{ token, user, mfaRequired, initializing, setSession, clearSession }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return ctx;
}
