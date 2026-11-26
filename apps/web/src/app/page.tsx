import Link from "next/link";
import { FoundationStatus } from "@/components/foundation-status";

export default function HomePage() {
  return (
    <main id="main-content" className="mx-auto max-w-5xl space-y-10 px-4 py-10 sm:px-6">
      <header className="space-y-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-indigo-700">
          GuruSetu AI — Phase 1 Core Learning Platform
        </p>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">
          Curriculum-Grounded Learning, Question Bank &amp; Guided Practice
        </h1>
        <p className="max-w-3xl text-sm text-slate-600">
          Built on FastAPI, PostgreSQL 18, and Next.js with role-based access
          control, 11-level versioned curriculum, content rights governance,
          schema-adaptive Excel/CSV staging, and guided student practice.
        </p>
        <div className="flex flex-wrap gap-3 pt-1">
          <Link
            href="/curriculum"
            className="rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-800"
          >
            Browse Curriculum
          </Link>
          <Link
            href="/register"
            className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50"
          >
            Create Student Account
          </Link>
          <Link
            href="/login"
            className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50"
          >
            Sign In
          </Link>
        </div>
      </header>

      <FoundationStatus />
    </main>
  );
}
