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
const LEGACY_SESSION_KEY = "go4guru_access_session_v1";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserSummary | null>(null);
  const [mfaRequired, setMfaRequired] = useState<boolean>(false);
  const [initializing, setInitializing] = useState<boolean>(true);

  const setSession = useCallback((resp: AuthTokenResponse) => {
    // Keep short-lived access JWT strictly in React state memory (never in Web Storage).
    setToken(resp.access_token);
    setUser(resp.user);
    setMfaRequired(resp.mfa_required);
    if (typeof window !== "undefined") {
      try {
        window.sessionStorage.removeItem(LEGACY_SESSION_KEY);
      } catch {
        // Ignore restricted storage environments
      }
    }
  }, []);

  const clearSession = useCallback(async () => {
    const activeToken = token;
    setToken(null);
    setUser(null);
    setMfaRequired(false);
    if (typeof window !== "undefined") {
      try {
        window.sessionStorage.removeItem(LEGACY_SESSION_KEY);
      } catch {
        // Ignore restricted storage environments
      }
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
        try {
          window.sessionStorage.removeItem(LEGACY_SESSION_KEY);
        } catch {
          // Ignore restricted storage environments
        }
      }
      try {
        // Restore session exclusively through the HttpOnly rotating refresh cookie.
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
