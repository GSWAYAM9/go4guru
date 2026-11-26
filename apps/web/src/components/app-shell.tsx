"use client";

import { StatusBadge } from "@go4guru/ui";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useAuth } from "@/lib/auth-context";

const PRIVILEGED_ROLES = new Set([
  "content_admin",
  "academic_reviewer",
  "platform_admin",
]);

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, mfaRequired, clearSession } = useAuth();

  const isPrivileged = user
    ? user.roles.some((r) => PRIVILEGED_ROLES.has(r))
    : false;

  const isParentOnly = user
    ? user.roles.length === 1 && user.roles[0] === "parent"
    : false;

  const navItems = [
    { href: "/", label: "Home" },
    { href: "/curriculum", label: "Curriculum" },
    ...(user
      ? [
          { href: "/dashboard", label: "Dashboard" },
          { href: "/practice", label: "Practice" },
          { href: "/quizzes", label: "Quizzes" },
          { href: "/assessments", label: "Assessments" },
          ...(!isParentOnly
            ? [
                { href: "/tutor", label: "AI Tutor" },
                { href: "/classroom", label: "Live Classroom" },
                { href: "/adaptive", label: "Adaptive Mastery" },
                { href: "/revision", label: "Revision & Plan" },
              ]
            : []),
          { href: "/analytics", label: "Analytics" },
          { href: "/notes", label: "Notes & Saved" },
        ]
      : []),
    ...(isPrivileged ? [{ href: "/admin", label: "Admin Studio" }] : []),
  ];

  async function handleLogout() {
    await clearSession();
    router.push("/login");
  }

  return (
    <div className="flex min-h-screen flex-col">
      <nav
        aria-label="Primary Navigation"
        className="border-b border-slate-200 bg-white"
      >
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <div className="flex flex-wrap items-center gap-6">
            <Link
              href="/"
              className="text-lg font-bold tracking-tight text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
            >
              GuruSetu AI
            </Link>
            <ul className="flex flex-wrap items-center gap-2 text-sm">
              {navItems.map((item) => {
                const active = pathname === item.href;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={`rounded-md px-3 py-1.5 font-medium transition ${
                        active
                          ? "bg-indigo-50 text-indigo-900"
                          : "text-slate-700 hover:bg-slate-100"
                      }`}
                    >
                      {item.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-sm">
            {user ? (
              <>
                <span className="text-slate-700">
                  {user.display_name}{" "}
                  <StatusBadge tone={mfaRequired ? "degraded" : "neutral"}>
                    {user.roles[0] ?? "user"}
                    {mfaRequired ? " (MFA Pending)" : ""}
                  </StatusBadge>
                </span>
                <button
                  type="button"
                  onClick={() => void handleLogout()}
                  className="rounded-md border border-slate-300 bg-white px-3 py-1.5 font-medium text-slate-800 hover:bg-slate-50"
                >
                  Sign Out
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="rounded-md border border-slate-300 px-3 py-1.5 font-medium text-slate-800 hover:bg-slate-50"
                >
                  Sign In
                </Link>
                <Link
                  href="/register"
                  className="rounded-md bg-indigo-700 px-3 py-1.5 font-medium text-white hover:bg-indigo-800"
                >
                  Register
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      <div className="flex-1">{children}</div>

      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-500">
        GuruSetu AI (Phase 1 Core Learning Platform) — Independent educational
        ecosystem; not endorsed by or affiliated with NCERT, CBSE, or NTA.
      </footer>
    </div>
  );
}
