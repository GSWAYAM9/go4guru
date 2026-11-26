"use client";

import { ErrorBanner, StatusBadge } from "@go4guru/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import {
  ApiClientError,
  loginAccount,
  setupMfa,
  verifyMfa,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const router = useRouter();
  const { setSession, token, mfaRequired, user } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [mfaSecret, setMfaSecret] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<{
    code: string;
    message: string;
    requestId?: string;
  } | null>(null);

  async function handleLogin(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const resp = await loginAccount({
        email,
        password,
        totp_code: totpCode.trim() ? totpCode.trim() : null,
      });
      setSession(resp);
      if (!resp.mfa_required) {
        const isAdmin = resp.user.roles.some((r) =>
          ["content_admin", "academic_reviewer", "platform_admin"].includes(r)
        );
        router.push(isAdmin ? "/admin" : "/dashboard");
      }
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError({
          code: err.code,
          message: err.message,
          requestId: err.requestId,
        });
      } else {
        setError({
          code: "NETWORK_ERROR",
          message: "Unable to reach authentication server.",
        });
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSetupMfa() {
    if (!token) return;
    setError(null);
    try {
      const res = await setupMfa(token);
      setMfaSecret(res.secret);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError({ code: err.code, message: err.message, requestId: err.requestId });
      }
    }
  }

  async function handleVerifyMfa(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await verifyMfa(token, totpCode.trim());
      setSession(res);
      router.push("/admin");
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError({ code: err.code, message: err.message, requestId: err.requestId });
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main id="main-content" className="mx-auto max-w-md px-4 py-12">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
        <h1 className="text-2xl font-bold text-slate-900">Sign In</h1>
        <p className="mt-1 text-sm text-slate-600">
          Access your personalized curriculum, practice sessions, and notes.
        </p>

        {error ? (
          <div className="mt-4">
            <ErrorBanner
              title={`Sign-In Error (${error.code})`}
              message={error.message}
              requestId={error.requestId}
            />
          </div>
        ) : null}

        {mfaRequired && user ? (
          <form onSubmit={(e) => void handleVerifyMfa(e)} className="mt-6 space-y-4">
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">
              <div className="flex items-center justify-between">
                <span className="font-semibold">TOTP MFA Required</span>
                <StatusBadge tone="degraded">Privileged Role</StatusBadge>
              </div>
              <p className="mt-1">
                Verify your 6-digit authenticator code to unlock privileged routes.
              </p>
              {!user.mfa_enabled && !mfaSecret ? (
                <button
                  type="button"
                  onClick={() => void handleSetupMfa()}
                  className="mt-2 rounded bg-amber-800 px-3 py-1 text-xs font-medium text-white hover:bg-amber-900"
                >
                  Generate TOTP Secret
                </button>
              ) : null}
              {mfaSecret ? (
                <p className="mt-2 font-mono text-xs break-all">
                  Authenticator Secret: <strong>{mfaSecret}</strong>
                </p>
              ) : null}
            </div>

            <div>
              <label
                htmlFor="mfa-code"
                className="block text-sm font-medium text-slate-800"
              >
                6-Digit TOTP Code
              </label>
              <input
                id="mfa-code"
                type="text"
                required
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                placeholder="123456"
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-md bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 disabled:opacity-60"
            >
              {submitting ? "Verifying MFA..." : "Verify MFA & Continue"}
            </button>
          </form>
        ) : (
          <form onSubmit={(e) => void handleLogin(e)} className="mt-6 space-y-4">
            <div>
              <label
                htmlFor="login-email"
                className="block text-sm font-medium text-slate-800"
              >
                Email
              </label>
              <input
                id="login-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label
                htmlFor="login-password"
                className="block text-sm font-medium text-slate-800"
              >
                Password
              </label>
              <input
                id="login-password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label
                htmlFor="login-totp"
                className="block text-sm font-medium text-slate-800"
              >
                TOTP Code (Optional unless MFA enabled)
              </label>
              <input
                id="login-totp"
                type="text"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                placeholder="6-digit code"
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-md bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 disabled:opacity-60"
            >
              {submitting ? "Signing In..." : "Sign In"}
            </button>
          </form>
        )}

        <p className="mt-4 text-center text-sm text-slate-600">
          New learner?{" "}
          <Link href="/register" className="font-medium text-indigo-700 underline">
            Create an account
          </Link>
        </p>
      </div>
    </main>
  );
}
