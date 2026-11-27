"use client";

import Link from "next/link";
import { useState } from "react";
import { SHOWCASE_TABS, type ShowcaseTab } from "@/lib/landing-data";

export function HeroClassroomPreview() {
  const [step, setStep] = useState<0 | 1 | 2>(0);

  const steps = [
    {
      label: "Step 1 · Formula",
      equation: "6CO₂ + 6H₂O + light → C₆H₁₂O₆ + 6O₂",
      boardNote: "Chloroplasts convert solar energy into chemical glucose.",
      prompt:
        "Look at the right-hand side of the equation. Which gas is released into the air?",
    },
    {
      label: "Step 2 · Check-in",
      equation: "Input: CO₂ + H₂O  ⟶  Output: Glucose + O₂",
      boardNote: "Stomata take in CO₂ and release O₂ during daylight.",
      prompt:
        "Good catch! Would you like a quick diagram of the leaf cross-section next?",
    },
    {
      label: "Step 3 · Marked Practice",
      equation: "Mastery Check · 2 of 2 verified",
      boardNote: "Saved key formula to your Spaced Revision deck.",
      prompt:
        "Ready to test this concept with a timed CBSE / NEET checkpoint question?",
    },
  ] as const;

  const active = steps[step];

  return (
    <div className="relative mx-auto w-full min-w-0 max-w-[600px]">
      <div className="overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-[0_24px_60px_-24px_rgba(11,16,74,0.22)]">
        {/* Window chrome */}
        <div className="flex items-center justify-between gap-2 border-b border-slate-200 bg-[#F8FAFC] px-4 py-2.5">
          <div className="flex min-w-0 items-center gap-2">
            <img
              src="/assets/aistudio/image_2e20d262.png"
              alt="Go4Guru"
              referrerPolicy="no-referrer"
              className="h-6 w-12 shrink-0 rounded bg-[#090B46] object-cover object-center"
            />
            <span className="truncate text-xs font-semibold text-[#0B104A]">
              Photosynthesis — Light &amp; Dark Reactions
            </span>
          </div>
          <span className="shrink-0 whitespace-nowrap font-mono text-[11px] font-medium text-slate-500">
            Class 10 · Science
          </span>
        </div>

        {/* Interactive Board + Tutor Side Panel */}
        <div className="grid grid-cols-1 sm:grid-cols-[1.25fr_1fr]">
          {/* Dotted whiteboard canvas */}
          <div
            className="flex min-w-0 flex-col justify-between border-b border-slate-200 p-4 sm:border-b-0 sm:border-r sm:p-5"
            style={{
              backgroundImage:
                "radial-gradient(#CBD5E1 1px, transparent 1px)",
              backgroundSize: "16px 16px",
              backgroundColor: "#FCFDFE",
            }}
          >
            <div className="space-y-4">
              <div className="flex items-center justify-between text-[11px] font-medium text-slate-500">
                <span>Interactive Board</span>
                <span className="font-mono text-[#1D4ED8]">{active.label}</span>
              </div>

              <div className="rounded-xl border border-[#0B104A]/12 bg-white/95 p-4">
                <p className="font-mono text-xs font-semibold text-[#0B104A] sm:text-sm">
                  {active.equation}
                </p>
                <p className="mt-2 text-xs leading-relaxed text-slate-600">
                  {active.boardNote}
                </p>
              </div>

              {/* Clean schematic SVG diagram */}
              <svg
                viewBox="0 0 280 96"
                role="img"
                aria-label="Chloroplast energy flow diagram"
                className="h-24 w-full"
              >
                <rect
                  x="8"
                  y="24"
                  width="74"
                  height="46"
                  rx="10"
                  fill="#EFF6FF"
                  stroke="#93C5FD"
                  strokeWidth="1.5"
                />
                <text
                  x="45"
                  y="44"
                  textAnchor="middle"
                  fill="#0B104A"
                  fontSize="10"
                  fontWeight="600"
                >
                  Sunlight +
                </text>
                <text
                  x="45"
                  y="58"
                  textAnchor="middle"
                  fill="#1D4ED8"
                  fontSize="10"
                >
                  CO₂ &amp; H₂O
                </text>
                <path
                  d="M86 47 L112 47"
                  stroke="#0B104A"
                  strokeWidth="1.75"
                  strokeLinecap="round"
                />
                <polygon points="112,43 120,47 112,51" fill="#0B104A" />
                <ellipse
                  cx="154"
                  cy="47"
                  rx="30"
                  ry="24"
                  fill="#ECFCCB"
                  stroke="#65A30D"
                  strokeWidth="1.5"
                />
                <text
                  x="154"
                  y="50"
                  textAnchor="middle"
                  fill="#1A2E05"
                  fontSize="10"
                  fontWeight="600"
                >
                  Leaf Cell
                </text>
                <path
                  d="M188 47 L212 47"
                  stroke="#0B104A"
                  strokeWidth="1.75"
                  strokeLinecap="round"
                />
                <polygon points="212,43 220,47 212,51" fill="#0B104A" />
                <rect
                  x="222"
                  y="24"
                  width="52"
                  height="46"
                  rx="10"
                  fill="#FEF9C3"
                  stroke="#CA8A04"
                  strokeWidth="1.5"
                />
                <text
                  x="248"
                  y="44"
                  textAnchor="middle"
                  fill="#0B104A"
                  fontSize="10"
                  fontWeight="600"
                >
                  Glucose
                </text>
                <text
                  x="248"
                  y="58"
                  textAnchor="middle"
                  fill="#854D0E"
                  fontSize="10"
                >
                  + O₂
                </text>
              </svg>
            </div>

            {/* Interactive step switcher */}
            <div
              className="mt-4 flex items-center gap-1 rounded-lg bg-slate-100 p-1"
              role="tablist"
              aria-label="Preview lesson stages"
            >
              {(["Board", "Check-in", "Marked"] as const).map((name, idx) => {
                const selected = step === idx;
                return (
                  <button
                    key={name}
                    type="button"
                    role="tab"
                    aria-selected={selected}
                    onClick={() => setStep(idx as 0 | 1 | 2)}
                    className={`flex-1 whitespace-nowrap rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors ${
                      selected
                        ? "bg-white text-[#0B104A] shadow-xs"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    {name}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Lesson Tutor Column */}
          <div className="flex flex-col justify-between bg-white p-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <span className="text-xs font-semibold text-[#0B104A]">
                  Go4Guru Lesson Guide
                </span>
                <span className="text-[11px] text-slate-500">Hint Mode</span>
              </div>

              <div className="rounded-lg bg-[#F4F6FB] p-3 text-xs leading-relaxed text-slate-700">
                {active.prompt}
              </div>

              <div className="rounded-lg border border-slate-200 p-2.5 text-[11px] text-slate-600">
                <span className="font-semibold text-[#0B104A]">
                  Student reply:
                </span>{" "}
                Oxygen gas (O₂) is released.
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-500">
                <span>Understanding verified</span>
                <span className="font-mono font-semibold text-emerald-700">
                  100%
                </span>
              </div>
            </div>

            <div className="mt-4 border-t border-slate-100 pt-3">
              <Link
                href="/classroom"
                className="flex w-full items-center justify-between rounded-lg bg-[#0B104A] px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-[#17217A]"
              >
                <span>Try a live board lesson</span>
                <span aria-hidden="true">→</span>
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Quiet caption below preview */}
      <p className="mt-3 text-right text-xs text-slate-500">
        Interactive Go4Guru Classroom · Bilingual captions &amp; verified math
      </p>
    </div>
  );
}

function ShowcaseVisual({ tabId }: { tabId: ShowcaseTab["id"] }) {
  if (tabId === "whiteboard") {
    return (
      <div
        className="flex h-full min-h-[300px] flex-col justify-between p-6"
        style={{
          backgroundImage: "radial-gradient(#CBD5E1 1px, transparent 1px)",
          backgroundSize: "18px 18px",
          backgroundColor: "#FCFDFE",
        }}
      >
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <span className="text-xs font-semibold text-[#0B104A]">
            Quadratic Equations · Completing the Square
          </span>
          <span className="font-mono text-xs text-slate-500">
            SymPy Verified
          </span>
        </div>
        <div className="my-5 grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-xs font-medium text-slate-500">Worked Step</p>
            <p className="mt-2 font-mono text-sm font-semibold text-[#0B104A]">
              x² + 6x − 7 = 0
            </p>
            <p className="mt-1 font-mono text-sm text-[#1D4ED8]">
              (x + 3)² = 16
            </p>
            <p className="mt-1 font-mono text-sm font-semibold text-emerald-700">
              x = 1 or x = −7
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-xs font-medium text-slate-500">Tutor Prompt</p>
            <p className="mt-2 text-xs leading-relaxed text-slate-700">
              Why did we add 9 to both sides before factoring the left side?
            </p>
            <p className="mt-3 text-[11px] font-medium text-[#1D4ED8]">
              Voice captions + 14 language preferences available
            </p>
          </div>
        </div>
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>Stage 3 of 5 · Worked Example</span>
          <span className="font-mono">Replay saved</span>
        </div>
      </div>
    );
  }

  if (tabId === "curriculum") {
    return (
      <div className="flex h-full min-h-[300px] flex-col justify-between bg-white p-6">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <span className="text-xs font-semibold text-[#0B104A]">
            CBSE &amp; US Common Core · Grade 10 Mathematics
          </span>
          <span className="text-xs text-slate-500">11-Level Tree</span>
        </div>
        <div className="my-4 grid gap-4 sm:grid-cols-[0.9fr_1.3fr]">
          <ul className="space-y-2 border-r border-slate-100 pr-3 text-xs">
            <li className="rounded-md bg-[#EEF2FF] px-2.5 py-2 font-semibold text-[#0B104A]">
              01. Real Numbers
            </li>
            <li className="px-2.5 py-1.5 text-slate-600">02. Polynomials</li>
            <li className="px-2.5 py-1.5 text-slate-600">
              03. Linear Equations
            </li>
            <li className="px-2.5 py-1.5 text-slate-600">
              04. Quadratic Equations
            </li>
            <li className="px-2.5 py-1.5 text-slate-600">
              05. Coordinate Geometry
            </li>
          </ul>
          <div className="space-y-3">
            <p className="text-sm font-semibold text-[#0B104A]">
              Fundamental Theorem of Arithmetic
            </p>
            <p className="text-xs leading-relaxed text-slate-600">
              Every composite integer greater than 1 can be factored uniquely
              into prime numbers, apart from the order of the factors.
            </p>
            <div className="rounded-lg bg-[#F8FAFC] p-3 text-xs text-slate-700">
              <span className="font-semibold text-[#0B104A]">
                Linked Study Actions:
              </span>{" "}
              Ask AI Tutor · Open Practice Set · Add Personal Note
            </div>
          </div>
        </div>
        <div className="text-xs text-slate-500">
          Prerequisites, learning objectives, and saved notes stay attached to
          each concept.
        </div>
      </div>
    );
  }

  if (tabId === "practice") {
    return (
      <div className="flex h-full min-h-[300px] flex-col justify-between bg-white p-6">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <span className="text-xs font-semibold text-[#0B104A]">
            Introduction to Rational Numbers
          </span>
          <span className="font-mono text-xs text-slate-500">
            Question 2 of 6
          </span>
        </div>
        <div className="my-4 space-y-3">
          <p className="text-sm font-medium text-slate-900">
            Which of the following numbers is rational?
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            {[
              { key: "A", val: "√2", selected: false },
              { key: "B", val: "3 / 4", selected: true },
              { key: "C", val: "π", selected: false },
              { key: "D", val: "√5", selected: false },
            ].map((opt) => (
              <div
                key={opt.key}
                className={`flex items-center gap-2.5 rounded-lg border px-3 py-2 text-xs ${
                  opt.selected
                    ? "border-[#0B104A] bg-[#EEF2FF] font-semibold text-[#0B104A]"
                    : "border-slate-200 text-slate-700"
                }`}
              >
                <span className="font-mono text-[11px]">{opt.key}.</span>
                <span>{opt.val}</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-emerald-700">
            Verified: 3/4 is expressed as p/q with integers p = 3, q = 4 ≠ 0.
          </p>
        </div>
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>Graduated hints ready before solution reveal</span>
          <span className="font-mono">Server-checked</span>
        </div>
      </div>
    );
  }

  if (tabId === "revision") {
    return (
      <div className="flex h-full min-h-[300px] flex-col justify-between bg-white p-6">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <span className="text-xs font-semibold text-[#0B104A]">
            Spaced Revision Queue · SM-2 Scheduler
          </span>
          <span className="font-mono text-xs text-[#1D4ED8]">6 cards due</span>
        </div>
        <div className="my-4 space-y-3">
          <div className="rounded-xl border border-slate-200 bg-[#F8FAFC] p-4">
            <p className="text-xs text-slate-500">
              Physics · Laws of Motion · Missed 3 days ago
            </p>
            <p className="mt-1.5 text-sm font-semibold text-[#0B104A]">
              Why does friction act opposite to the tendency of relative motion?
            </p>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            <div className="rounded-lg border border-slate-200 p-2.5">
              <p className="font-mono font-semibold text-[#0B104A]">1 day</p>
              <p className="text-slate-500">Needs review</p>
            </div>
            <div className="rounded-lg border border-[#0B104A] bg-[#EEF2FF] p-2.5">
              <p className="font-mono font-semibold text-[#0B104A]">4 days</p>
              <p className="text-[#0B104A]">Recalled well</p>
            </div>
            <div className="rounded-lg border border-slate-200 p-2.5">
              <p className="font-mono font-semibold text-[#0B104A]">12 days</p>
              <p className="text-slate-500">Mastered</p>
            </div>
          </div>
        </div>
        <div className="text-xs text-slate-500">
          Weak concepts from homework and mocks sync automatically into your
          daily deck.
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-[300px] flex-col justify-between bg-white p-6">
      <div className="flex items-center justify-between border-b border-slate-200 pb-3">
        <span className="text-xs font-semibold text-[#0B104A]">
          Good evening, Aarav · Class 10
        </span>
        <span className="font-mono text-xs text-slate-500">
          Study Streak: 9 days
        </span>
      </div>
      <div className="my-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-[#F8FAFC] p-4">
          <p className="text-xs text-slate-500">Up Next Today</p>
          <p className="mt-1 text-base font-semibold text-[#0B104A]">
            Review 6 due cards
          </p>
          <p className="mt-1 text-xs text-slate-600">
            12 min · Algebra &amp; Optics refresher
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs text-slate-500">Recent Assessment</p>
          <p className="mt-1 font-mono text-base font-semibold text-[#0B104A] tabular-nums">
            86% accuracy
          </p>
          <p className="mt-1 text-xs text-slate-600">
            CBSE Chapter Test · Quadratic Equations
          </p>
        </div>
      </div>
      <div className="text-xs text-slate-500">
        Direct access to Live Classroom, Homework AI, Exam Prep, and Parent
        Summaries.
      </div>
    </div>
  );
}

export function WorkspaceShowcase() {
  const [activeId, setActiveId] = useState<ShowcaseTab["id"]>("whiteboard");
  const activeTab =
    SHOWCASE_TABS.find((t) => t.id === activeId) ?? SHOWCASE_TABS[0];

  return (
    <div className="space-y-8">
      {/* Interactive segmented tab bar */}
      <div
        role="tablist"
        aria-label="Inside Go4Guru workspace tools"
        className="flex flex-wrap items-center gap-2"
      >
        {SHOWCASE_TABS.map((tab) => {
          const isActive = tab.id === activeTab.id;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => setActiveId(tab.id)}
              className={`whitespace-nowrap rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-[#0B104A] text-white"
                  : "border border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:text-[#0B104A]"
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Split Preview Frame + Editorial Explanation */}
      <div className="grid items-center gap-8 lg:grid-cols-[1.35fr_0.95fr] lg:gap-12">
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_20px_48px_-28px_rgba(11,16,74,0.2)]">
          <div className="flex items-center gap-1.5 border-b border-slate-200 bg-[#F8FAFC] px-4 py-2.5">
            <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
            <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
            <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
            <span className="ml-2 text-xs text-slate-500">
              app.go4guru.com{activeTab.href}
            </span>
          </div>
          <ShowcaseVisual tabId={activeTab.id} />
        </div>

        <div className="space-y-4">
          <h3 className="font-display text-2xl font-semibold tracking-tight text-[#0B104A] text-balance sm:text-3xl">
            {activeTab.headline}
          </h3>
          <p className="text-base leading-relaxed text-slate-600">
            {activeTab.description}
          </p>
          <p className="text-xs text-slate-500">{activeTab.caption}</p>
          <div className="pt-2">
            <Link
              href={activeTab.href}
              className="inline-flex items-center gap-2 text-sm font-semibold text-[#1D4ED8] transition-colors hover:text-[#0B104A]"
            >
              <span>{activeTab.ctaLabel}</span>
              <span aria-hidden="true">→</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
