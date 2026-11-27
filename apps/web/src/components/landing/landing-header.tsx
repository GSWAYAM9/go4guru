"use client";

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/lib/auth-context";

const NAV_LINKS = [
  { href: "#learning-paths", label: "Tutoring" },
  { href: "#exam-prep", label: "Exam Prep" },
  { href: "#parents", label: "For Parents" },
  { href: "#pricing", label: "Pricing" },
  { href: "#faq", label: "FAQ" },
] as const;

export function LandingHeader() {
  const { user } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-[#FAFBFD]/95 backdrop-blur-sm">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3.5 sm:px-6 md:gap-8">
        {/* Zone 1: Clean single-line Brand Mark + Wordmark */}
        <Link
          href="/"
          className="inline-flex shrink-0 items-center gap-2.5 whitespace-nowrap focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1D4ED8]"
        >
          <img
            src="/assets/aistudio/image_2e20d262.png"
            alt="Go4Guru logo"
            referrerPolicy="no-referrer"
            className="h-8 w-[76px] rounded-lg bg-[#090B46] object-cover object-center sm:h-9 sm:w-[84px]"
          />
          <span className="hidden font-display text-xl font-bold tracking-tight text-[#0B104A] sm:inline">
            Go4Guru
          </span>
        </Link>

        {/* Zone 2: 5 concise single-line text nav links */}
        <nav
          aria-label="Landing Navigation"
          className="hidden items-center gap-7 text-sm font-medium text-slate-600 md:flex"
        >
          {NAV_LINKS.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="whitespace-nowrap shrink-0 transition-colors hover:text-[#0B104A] hover:underline hover:underline-offset-8"
            >
              {item.label}
            </a>
          ))}
        </nav>

        {/* Zone 3: Primary CTA (plus quiet Sign in or mobile drawer toggle) */}
        <div className="flex shrink-0 items-center gap-2.5 sm:gap-4">
          {user ? (
            <Link
              href="/dashboard"
              className="inline-flex whitespace-nowrap shrink-0 items-center gap-1.5 rounded-lg bg-[#0B104A] px-3.5 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#17217A] sm:px-4"
            >
              <span>Open Dashboard</span>
              <span aria-hidden="true">→</span>
            </Link>
          ) : (
            <>
              <Link
                href="/login"
                className="hidden whitespace-nowrap shrink-0 text-sm font-medium text-slate-700 transition-colors hover:text-[#0B104A] sm:inline-block"
              >
                Sign in
              </Link>
              <Link
                href="/register"
                className="inline-flex whitespace-nowrap shrink-0 items-center gap-1.5 rounded-lg bg-[#0B104A] px-3.5 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#17217A] sm:px-4"
              >
                <span>Start free</span>
                <span aria-hidden="true">→</span>
              </Link>
            </>
          )}

          <button
            type="button"
            aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((prev) => !prev)}
            className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-white text-[#0B104A] md:hidden"
          >
            <span className="font-mono text-base" aria-hidden="true">
              {menuOpen ? "×" : "≡"}
            </span>
          </button>
        </div>
      </div>

      {/* Mobile navigation drawer */}
      {menuOpen ? (
        <div className="border-t border-slate-200 bg-white px-4 py-4 md:hidden">
          <div className="flex flex-col gap-3 text-sm font-medium text-slate-700">
            {NAV_LINKS.map((item) => (
              <a
                key={item.href}
                href={item.href}
                onClick={() => setMenuOpen(false)}
                className="py-1.5 hover:text-[#0B104A]"
              >
                {item.label}
              </a>
            ))}
            {!user ? (
              <Link
                href="/login"
                onClick={() => setMenuOpen(false)}
                className="border-t border-slate-100 pt-3 text-[#0B104A]"
              >
                Sign in
              </Link>
            ) : null}
          </div>
        </div>
      ) : null}
    </header>
  );
}
