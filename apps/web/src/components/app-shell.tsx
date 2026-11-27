"use client";

import { StatusBadge } from "@go4guru/ui";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useAuth } from "@/lib/auth-context";
import { useLanguage } from "@/lib/language-context";

const PRIVILEGED_ROLES = new Set([
  "content_admin",
  "academic_reviewer",
  "platform_admin",
]);

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, mfaRequired, clearSession } = useAuth();
  const { preferences, capabilities, isRtl, t } = useLanguage();

  const activeUiLang = capabilities.find(
    (c) => c.language_code === preferences.ui_language
  );

  const roles = user?.roles ?? [];
  const isPrivileged = roles.some((r) => PRIVILEGED_ROLES.has(r));
  const isTeacher = roles.some((r) =>
    ["teacher", "school_admin", "platform_admin"].includes(r)
  );
  const isMentor = roles.some((r) =>
    ["mentor", "school_admin", "platform_admin"].includes(r)
  );
  const isParent = roles.some((r) =>
    ["parent", "platform_admin"].includes(r)
  );
  const isOrgAdmin = roles.some((r) =>
    ["school_admin", "platform_admin"].includes(r)
  );
  const isParentOnly = roles.length === 1 && roles[0] === "parent";
  const isStudent = roles.includes("student");

  const navItems = [
    { href: "/", label: t("nav.home", "Home") },
    { href: "/curriculum", label: t("nav.curriculum", "Curriculum") },
    { href: "/languages", label: t("nav.languages", "Languages") },
    ...(user && !isParentOnly && (isStudent || isPrivileged)
      ? [
          { href: "/dashboard", label: t("nav.dashboard", "Dashboard") },
          { href: "/practice", label: t("nav.practice", "Practice") },
          { href: "/quizzes", label: t("nav.quizzes", "Quizzes") },
          { href: "/assessments", label: t("nav.assessments", "Assessments") },
          { href: "/exams", label: t("nav.exams", "Exam Prep") },
          { href: "/tutor", label: t("nav.tutor", "AI Tutor") },
          { href: "/classroom", label: t("nav.classroom", "Live Classroom") },
          { href: "/homework", label: t("nav.homework", "Homework AI") },
          { href: "/adaptive", label: t("nav.adaptive", "Adaptive Mastery") },
          { href: "/revision", label: t("nav.revision", "Revision & Plan") },
          { href: "/analytics", label: t("nav.analytics", "Analytics") },
          { href: "/notes", label: t("nav.notes", "Notes & Saved") },
        ]
      : []),
    ...(isTeacher
      ? [{ href: "/teacher", label: t("nav.teacher", "Teacher Hub") }]
      : []),
    ...(isMentor
      ? [{ href: "/mentor", label: t("nav.mentor", "Mentor Hub") }]
      : []),
    ...(isParent
      ? [{ href: "/parent", label: t("nav.parent", "Parent Portal") }]
      : []),
    ...(isOrgAdmin
      ? [{ href: "/institution", label: t("nav.institution", "Institution") }]
      : []),
    ...(isPrivileged
      ? [{ href: "/admin", label: t("nav.admin", "Admin Studio") }]
      : []),
  ];

  async function handleLogout() {
    await clearSession();
    router.push("/login");
  }

  if (pathname === "/") {
    return (
      <div className="flex min-h-screen flex-col" dir={isRtl ? "rtl" : "ltr"}>
        {children}
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col" dir={isRtl ? "rtl" : "ltr"}>
      <nav
        aria-label="Primary Navigation"
        className="border-b border-slate-200 bg-white"
      >
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <div className="flex flex-wrap items-center gap-6">
            <Link
              href="/"
              className="inline-flex whitespace-nowrap shrink-0 items-center gap-2 text-lg font-bold tracking-tight text-[#0B104A] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1D4ED8]"
            >
              <img
                src="/assets/aistudio/image_2e20d262.png"
                alt="Go4Guru"
                referrerPolicy="no-referrer"
                className="h-7 w-16 rounded bg-[#090B46] object-cover object-center"
              />
              <span className="font-display">Go4Guru</span>
            </Link>
            <ul className="flex flex-wrap items-center gap-1.5 text-sm">
              {navItems.map((item) => {
                const active = pathname === item.href;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={`whitespace-nowrap shrink-0 rounded-md px-2.5 py-1.5 font-medium transition ${
                        active
                          ? "bg-[#EEF2FF] text-[#0B104A]"
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
            <Link
              href="/languages"
              title="Configure 6-modality language preferences"
              className="whitespace-nowrap shrink-0 text-xs font-medium text-slate-600 underline-offset-4 hover:text-[#1D4ED8] hover:underline"
            >
              {activeUiLang
                ? `${activeUiLang.native_name} (${activeUiLang.language_code.toUpperCase()})`
                : preferences.ui_language.toUpperCase()}
            </Link>
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
                  className="whitespace-nowrap shrink-0 rounded-md border border-slate-300 bg-white px-3 py-1.5 font-medium text-slate-800 hover:bg-slate-50"
                >
                  {t("auth.sign_out", "Sign Out")}
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="whitespace-nowrap shrink-0 rounded-md border border-slate-300 px-3 py-1.5 font-medium text-slate-800 hover:bg-slate-50"
                >
                  {t("auth.sign_in", "Sign In")}
                </Link>
                <Link
                  href="/register"
                  className="whitespace-nowrap shrink-0 rounded-md bg-[#0B104A] px-3 py-1.5 font-medium text-white hover:bg-[#17217A]"
                >
                  {t("auth.register", "Register")}
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      <div className="flex-1">{children}</div>

      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-500">
        {t(
          "footer.disclaimer",
          "Go4Guru by GO4GURU Inc. (USA & India · www.go4guru.com) — Independent educational platform; not endorsed by or affiliated with NCERT, CBSE, or NTA."
        )}
      </footer>
    </div>
  );
}
