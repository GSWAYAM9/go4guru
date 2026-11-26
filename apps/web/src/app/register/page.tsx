"use client";

import { ErrorBanner } from "@go4guru/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ApiClientError, registerAccount } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

export default function RegisterPage() {
  const router = useRouter();
  const { setSession } = useAuth();

  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [dobYear, setDobYear] = useState("2010");
  const [role, setRole] = useState<"student" | "parent">("student");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<{
    code: string;
    message: string;
    requestId?: string;
  } | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const resp = await registerAccount({
        email,
        password,
        display_name: displayName,
        date_of_birth_year: dobYear ? Number(dobYear) : null,
        role,
      });
      setSession(resp);
      router.push(role === "student" ? "/onboarding" : "/curriculum");
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
          message: "Unable to reach registration server.",
        });
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main id="main-content" className="mx-auto max-w-md px-4 py-12">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
        <h1 className="text-2xl font-bold text-slate-900">Create Account</h1>
        <p className="mt-1 text-sm text-slate-600">
          Join Classes 6–12 guided practice. Passwords require 8+ characters
          with letters and digits.
        </p>

        {error ? (
          <div className="mt-4">
            <ErrorBanner
              title={`Registration Failed (${error.code})`}
              message={error.message}
              requestId={error.requestId}
            />
          </div>
        ) : null}

        <form onSubmit={(e) => void handleSubmit(e)} className="mt-6 space-y-4">
          <div>
            <label
              htmlFor="reg-name"
              className="block text-sm font-medium text-slate-800"
            >
              Full Name
            </label>
            <input
              id="reg-name"
              type="text"
              required
              minLength={2}
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label
              htmlFor="reg-email"
              className="block text-sm font-medium text-slate-800"
            >
              Email Address
            </label>
            <input
              id="reg-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label
              htmlFor="reg-password"
              className="block text-sm font-medium text-slate-800"
            >
              Password
            </label>
            <input
              id="reg-password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label
                htmlFor="reg-dob"
                className="block text-sm font-medium text-slate-800"
              >
                Birth Year
              </label>
              <input
                id="reg-dob"
                type="number"
                min={1940}
                max={2025}
                value={dobYear}
                onChange={(e) => setDobYear(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label
                htmlFor="reg-role"
                className="block text-sm font-medium text-slate-800"
              >
                Account Role
              </label>
              <select
                id="reg-role"
                value={role}
                onChange={(e) =>
                  setRole(e.target.value as "student" | "parent")
                }
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="student">Student</option>
                <option value="parent">Parent / Guardian</option>
              </select>
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-md bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 disabled:opacity-60"
          >
            {submitting ? "Creating Account..." : "Create Account"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-slate-600">
          Already registered?{" "}
          <Link href="/login" className="font-medium text-indigo-700 underline">
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}
