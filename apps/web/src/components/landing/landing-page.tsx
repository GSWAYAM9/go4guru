import Link from "next/link";
import { EXAM_TRACKS, EXPLORABLE_TOPICS } from "@/lib/landing-data";
import {
  AdaptiveCheckinWidget,
  FaqAccordion,
  PricingSection,
} from "@/components/landing/interactive-sections";
import { LandingHeader } from "@/components/landing/landing-header";
import {
  HeroClassroomPreview,
  WorkspaceShowcase,
} from "@/components/landing/product-showcase";

const SESSION_STEPS = [
  {
    num: "01",
    title: "Ask a doubt or pick a chapter",
    body: "Open your board syllabus, upload a homework photo, or type any STEM question in your preferred language.",
  },
  {
    num: "02",
    title: "Learn on a live whiteboard",
    body: "Go4Guru breaks each idea into clear visual steps, diagrams, and verified equations at your pace.",
  },
  {
    num: "03",
    title: "Practice with guided hints",
    body: "Attempt targeted questions with graduated hints instead of instant spoilers—every step checked accurately.",
  },
  {
    num: "04",
    title: "Lock it in with revision",
    body: "Every missed question enters your spaced-repetition queue and comes back right before exam week.",
  },
] as const;

const OUTCOME_CARDS = [
  {
    title: "Real mastery, not shortcut answers.",
    body: "Go4Guru explains concepts step by step on a live board and checks whether the student genuinely understood before moving on.",
    accent: "board",
  },
  {
    title: "Mistakes become future marks.",
    body: "Wrong answers and weak concepts automatically generate review cards and targeted practice until the gap disappears.",
    accent: "mistakes",
  },
  {
    title: "Parents stay informed, respectfully.",
    body: "Weekly summaries highlight topics mastered, revision streaks, and weak chapters—while keeping student AI chat private.",
    accent: "parent",
  },
  {
    title: "Focused study, zero distractions.",
    body: "Structured 30-minute sessions stay anchored to your syllabus. No ads, no social feeds, and no selling student data.",
    accent: "focus",
  },
] as const;

function OutcomeGraphic({
  type,
}: {
  type: (typeof OUTCOME_CARDS)[number]["accent"];
}) {
  if (type === "board") {
    return (
      <svg
        viewBox="0 0 88 68"
        aria-hidden="true"
        className="h-16 w-20 shrink-0 rounded-xl border border-slate-200 bg-[#F4F6FB]"
      >
        <rect x="10" y="12" width="68" height="44" rx="6" fill="#FFFFFF" stroke="#CBD5E1" />
        <path d="M18 24 C28 18, 38 30, 48 22" fill="none" stroke="#1D4ED8" strokeWidth="2.5" strokeLinecap="round" />
        <circle cx="62" cy="36" r="10" fill="none" stroke="#D97706" strokeWidth="2.2" />
        <rect x="18" y="38" width="24" height="10" rx="5" fill="#0B104A" />
      </svg>
    );
  }
  if (type === "mistakes") {
    return (
      <svg
        viewBox="0 0 88 68"
        aria-hidden="true"
        className="h-16 w-20 shrink-0 rounded-xl border border-slate-200 bg-[#F4F6FB]"
      >
        <rect x="14" y="13" width="60" height="11" rx="5.5" fill="#FFFFFF" stroke="#CBD5E1" />
        <circle cx="22" cy="18.5" r="3.5" fill="#16A34A" />
        <rect x="30" y="16.5" width="34" height="4" rx="2" fill="#94A3B8" />
        <rect x="14" y="29" width="60" height="11" rx="5.5" fill="#FFFFFF" stroke="#CBD5E1" />
        <circle cx="22" cy="34.5" r="3.5" fill="#16A34A" />
        <rect x="30" y="32.5" width="28" height="4" rx="2" fill="#94A3B8" />
        <rect x="14" y="45" width="60" height="11" rx="5.5" fill="#FFFFFF" stroke="#CBD5E1" />
        <circle cx="22" cy="50.5" r="3.5" fill="#84CC16" />
        <rect x="30" y="48.5" width="38" height="4" rx="2" fill="#0B104A" />
      </svg>
    );
  }
  if (type === "parent") {
    return (
      <svg
        viewBox="0 0 88 68"
        aria-hidden="true"
        className="h-16 w-20 shrink-0 rounded-xl border border-slate-200 bg-[#F4F6FB]"
      >
        <rect x="14" y="12" width="60" height="44" rx="7" fill="#FFFFFF" stroke="#CBD5E1" />
        <rect x="22" y="20" width="22" height="4" rx="2" fill="#0B104A" />
        <rect x="22" y="38" width="10" height="12" rx="2" fill="#93C5FD" />
        <rect x="38" y="31" width="10" height="19" rx="2" fill="#1D4ED8" />
        <rect x="54" y="24" width="10" height="26" rx="2" fill="#0B104A" />
      </svg>
    );
  }
  return (
    <svg
      viewBox="0 0 88 68"
      aria-hidden="true"
      className="h-16 w-20 shrink-0 rounded-xl border border-slate-200 bg-[#F4F6FB]"
    >
      <path
        d="M44 10 L66 19 V35 C66 47 56 55 44 59 C32 55 22 47 22 35 V19 Z"
        fill="#FFFFFF"
        stroke="#CBD5E1"
        strokeWidth="1.75"
      />
      <circle cx="44" cy="34" r="11" fill="none" stroke="#CBD5E1" strokeWidth="3" />
      <path
        d="M44 23 A11 11 0 0 1 55 34"
        fill="none"
        stroke="#0B104A"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <path d="M44 34 L44 27" stroke="#1D4ED8" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

export function LandingPage() {
  return (
    <div className="min-h-screen bg-[#FAFBFD] text-slate-900">
      <LandingHeader />

      <main id="main-content">
        {/* 1. HERO SECTION */}
        <section className="relative overflow-hidden border-b border-slate-200/80 bg-gradient-to-br from-[#FAFBFD] via-[#FAFBFD] to-[#EEF3FB]">
          <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-16 sm:px-6 lg:grid-cols-[1.02fr_1.08fr] lg:py-24">
            <div className="space-y-6">
              <p className="text-xs font-semibold tracking-wide text-[#1D4ED8]">
                Go4Guru by GO4GURU Inc. · Online Tutoring in USA &amp; India
              </p>

              <h1 className="font-display text-4xl font-bold leading-[1.06] tracking-tight text-[#0B104A] text-balance sm:text-5xl lg:text-[3.5rem]">
                Learn deeply.{" "}
                <span className="relative inline-block italic text-[#1D4ED8]">
                  Master
                  <svg
                    viewBox="0 0 200 14"
                    aria-hidden="true"
                    className="absolute -bottom-1.5 left-0 h-3 w-full"
                    preserveAspectRatio="none"
                  >
                    <path
                      d="M4 10 C60 3, 140 3, 196 9"
                      fill="none"
                      stroke="#84CC16"
                      strokeWidth="4.5"
                      strokeLinecap="round"
                    />
                  </svg>
                </span>{" "}
                it for real.
              </h1>

              <p className="max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg">
                A dedicated online tutor and interactive STEM classroom built by
                GO4GURU Inc. Learn every chapter on a live whiteboard, test your
                understanding with verified math &amp; science practice, and
                keep parents clearly updated each week.
              </p>

              <div className="flex flex-wrap items-center gap-5 pt-2">
                <Link
                  href="/register"
                  className="inline-flex whitespace-nowrap items-center gap-2 rounded-lg bg-[#0B104A] px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#17217A]"
                >
                  <span>Start learning free</span>
                  <span aria-hidden="true">→</span>
                </Link>
                <Link
                  href="/exams"
                  className="inline-flex whitespace-nowrap items-center gap-1.5 text-sm font-semibold text-[#B45309] transition-colors hover:text-[#92400E]"
                >
                  <span>Preparing for CBSE, JEE, NEET or SAT?</span>
                  <span aria-hidden="true">→</span>
                </Link>
              </div>

              <p className="text-xs text-slate-500">
                Free starter credits every month · No credit card required ·
                Available in 14+ languages
              </p>
            </div>

            <HeroClassroomPreview />
          </div>
        </section>

        {/* 2. QUIET TRUST STRIP (Unboxed typographic metadata) */}
        <section
          aria-label="Platform highlights"
          className="border-b border-slate-200/80 bg-white py-5"
        >
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-center gap-x-4 gap-y-2 px-4 text-xs font-medium text-slate-600 sm:px-6 sm:text-sm">
            <span>Grades 6–12</span>
            <span aria-hidden="true" className="text-slate-300">
              ·
            </span>
            <span>CBSE · JEE · NEET · SAT</span>
            <span aria-hidden="true" className="text-slate-300">
              ·
            </span>
            <span>Online Tutoring (USA &amp; India)</span>
            <span aria-hidden="true" className="text-slate-300">
              ·
            </span>
            <span>International Educational Tours</span>
            <span aria-hidden="true" className="text-slate-300">
              ·
            </span>
            <span className="font-semibold text-[#0B104A]">
              GO4GURU Inc. (go4guru.com)
            </span>
          </div>
        </section>

        {/* 3. TWO WAYS TO LEARN WITH GO4GURU */}
        <section id="learning-paths" className="scroll-mt-20 py-20 sm:py-24">
          <div className="mx-auto max-w-6xl space-y-12 px-4 sm:px-6">
            <div className="max-w-2xl space-y-3">
              <p className="text-xs font-semibold tracking-wide text-[#1D4ED8]">
                Go4Guru Learning Ecosystem
              </p>
              <h2 className="font-display text-3xl font-bold tracking-tight text-[#0B104A] text-balance sm:text-4xl">
                One platform, built for school mastery and global horizons.
              </h2>
              <p className="text-base leading-relaxed text-slate-600">
                Choose structured daily tutoring aligned to your curriculum or
                explore GO4GURU Inc.’s broader online STEM coaching and
                international educational tour programs.
              </p>
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              {/* Card 1: School & Exam Tutoring */}
              <div className="flex flex-col justify-between rounded-2xl border border-[#0B104A]/15 bg-[#F2F5FC] p-7 sm:p-8">
                <div>
                  {/* Subtle progress-step graphic */}
                  <div className="mb-6 flex items-end gap-2" aria-hidden="true">
                    <span className="h-3 w-7 rounded-sm bg-[#BFDBFE]" />
                    <span className="h-5 w-7 rounded-sm bg-[#93C5FD]" />
                    <span className="h-8 w-7 rounded-sm bg-[#3B82F6]" />
                    <span className="h-11 w-7 rounded-sm bg-[#0B104A]" />
                    <span className="ml-1 font-mono text-xs font-semibold text-emerald-700">
                      ✓ Verified
                    </span>
                  </div>

                  <p className="text-xs font-semibold text-[#1D4ED8]">
                    Go4Guru School Tutoring · Grades 6–12
                  </p>
                  <h3 className="mt-2 font-display text-2xl font-bold tracking-tight text-[#0B104A] text-balance">
                    Structured tutoring built around how students actually learn.
                  </h3>
                  <p className="mt-2 text-sm text-slate-600">
                    For middle &amp; high school learners in India and the USA,
                    and their parents.
                  </p>

                  <ul className="mt-6 space-y-2.5 text-sm text-slate-700">
                    <li className="flex items-start gap-2.5">
                      <span className="font-semibold text-emerald-700" aria-hidden="true">
                        ✓
                      </span>
                      <span>
                        Interactive whiteboard classes that teach step by step
                      </span>
                    </li>
                    <li className="flex items-start gap-2.5">
                      <span className="font-semibold text-emerald-700" aria-hidden="true">
                        ✓
                      </span>
                      <span>
                        Graduated hint homework coaching without spoiling answers
                      </span>
                    </li>
                    <li className="flex items-start gap-2.5">
                      <span className="font-semibold text-emerald-700" aria-hidden="true">
                        ✓
                      </span>
                      <span>
                        Server-checked practice, mistake tracking &amp; spaced
                        revision
                      </span>
                    </li>
                    <li className="flex items-start gap-2.5">
                      <span className="font-semibold text-emerald-700" aria-hidden="true">
                        ✓
                      </span>
                      <span>
                        Privacy-preserving weekly learning summaries for parents
                      </span>
                    </li>
                    <li className="flex items-start gap-2.5">
                      <span className="font-semibold text-emerald-700" aria-hidden="true">
                        ✓
                      </span>
                      <span>
                        Dedicated tracks for CBSE, JEE Main &amp; Adv, NEET &amp;
                        SAT
                      </span>
                    </li>
                  </ul>
                </div>

                <div className="mt-8 flex flex-wrap items-center gap-5">
                  <Link
                    href="/parent"
                    className="inline-flex whitespace-nowrap items-center gap-2 rounded-lg bg-[#0B104A] px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#17217A]"
                  >
                    <span>For parents</span>
                    <span aria-hidden="true">→</span>
                  </Link>
                  <Link
                    href="/exams"
                    className="inline-flex whitespace-nowrap items-center gap-1.5 text-sm font-semibold text-[#B45309] hover:text-[#92400E]"
                  >
                    <span>Exam prep</span>
                    <span aria-hidden="true">→</span>
                  </Link>
                </div>
              </div>

              {/* Card 2: Every Learner + International Educational Tours */}
              <div className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-7 sm:p-8">
                <div>
                  {/* Subtle global orbit graphic */}
                  <div className="mb-6 flex items-center gap-3" aria-hidden="true">
                    <svg viewBox="0 0 112 44" className="h-11 w-28">
                      <ellipse
                        cx="56"
                        cy="22"
                        rx="48"
                        ry="14"
                        fill="none"
                        stroke="#CBD5E1"
                        strokeDasharray="3 3"
                      />
                      <circle cx="56" cy="22" r="7" fill="#0B104A" />
                      <circle cx="14" cy="20" r="4" fill="#84CC16" />
                      <circle cx="96" cy="18" r="4" fill="#1D4ED8" />
                      <circle cx="78" cy="34" r="3.5" fill="#EAB308" />
                    </svg>
                    <span className="font-mono text-xs text-slate-500">
                      USA · India · Global
                    </span>
                  </div>

                  <p className="text-xs font-semibold text-[#1D4ED8]">
                    Go4Guru Global &amp; Educational Tours
                  </p>
                  <h3 className="mt-2 font-display text-2xl font-bold tracking-tight text-[#0B104A] text-balance">
                    On-demand tutoring plus real-world international STEM tours.
                  </h3>
                  <p className="mt-2 text-sm text-slate-600">
                    For curious self-learners, international families, and school
                    delegations worldwide.
                  </p>

                  <ul className="mt-6 space-y-2.5 text-sm text-slate-700">
                    <li className="flex items-start gap-2.5">
                      <span className="font-semibold text-emerald-700" aria-hidden="true">
                        ✓
                      </span>
                      <span>
                        Ask any STEM question and get a guided board explanation
                      </span>
                    </li>
                    <li className="flex items-start gap-2.5">
                      <span className="font-semibold text-emerald-700" aria-hidden="true">
                        ✓
                      </span>
                      <span>
                        Multilingual support across English, Hindi, Tamil, Telugu
                        and more
                      </span>
                    </li>
                    <li className="flex items-start gap-2.5">
                      <span className="font-semibold text-emerald-700" aria-hidden="true">
                        ✓
                      </span>
                      <span>
                        1-on-1 cross-timezone online tutoring bridging USA &amp;
                        India
                      </span>
                    </li>
                    <li className="flex items-start gap-2.5">
                      <span className="font-semibold text-emerald-700" aria-hidden="true">
                        ✓
                      </span>
                      <span>
                        International Educational Tours — NASA Space Camp &amp;
                        university STEM immersion via GO4GURU Inc.
                      </span>
                    </li>
                  </ul>
                </div>

                <div className="mt-8 flex flex-wrap items-center gap-5">
                  <Link
                    href="/tutor"
                    className="inline-flex whitespace-nowrap items-center gap-2 rounded-lg border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-[#0B104A] transition-colors hover:bg-slate-50"
                  >
                    <span>Open AI Tutor</span>
                    <span aria-hidden="true">→</span>
                  </Link>
                  <a
                    href="https://www.go4guru.com"
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex whitespace-nowrap items-center gap-1.5 text-sm font-semibold text-[#1D4ED8] hover:text-[#0B104A]"
                  >
                    <span>Explore Tours at go4guru.com</span>
                    <span aria-hidden="true">↗</span>
                  </a>
                </div>
              </div>
            </div>

            {/* Quick-launch Topic Strip */}
            <div className="border-t border-slate-200 pt-8">
              <p className="mb-3 text-xs font-medium text-slate-500">
                Jump straight into a topic
              </p>
              <div className="flex flex-wrap gap-2">
                {EXPLORABLE_TOPICS.map((topic) => (
                  <Link
                    key={topic.label}
                    href={topic.href}
                    className="whitespace-nowrap rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs font-medium text-slate-700 transition-colors hover:border-[#0B104A] hover:text-[#0B104A]"
                  >
                    {topic.label}
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* 4. PERSONALIZED ADAPTIVE LEARNING */}
        <section className="border-y border-slate-200/80 bg-gradient-to-b from-[#F3F6FC] to-[#FAFBFD] py-20 sm:py-24">
          <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 sm:px-6 lg:grid-cols-[0.95fr_1.05fr]">
            <div className="space-y-8">
              <div className="space-y-3">
                <p className="text-xs font-semibold tracking-wide text-[#1D4ED8]">
                  Adaptive Mastery Loop
                </p>
                <h2 className="font-display text-3xl font-bold tracking-tight text-[#0B104A] text-balance sm:text-4xl">
                  Every learner, taught at their own pace.
                </h2>
                <p className="text-base leading-relaxed text-slate-600">
                  Go4Guru tracks which concepts are solid and where small
                  misconceptions hide, then adjusts board explanations, hints,
                  and spaced revision automatically.
                </p>
              </div>

              <div className="grid gap-6 sm:grid-cols-2">
                <div>
                  <h3 className="text-sm font-bold text-[#0B104A]">
                    Checks before moving on
                  </h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-slate-600">
                    When an idea hasn’t clicked yet, Go4Guru pauses and explains
                    it again from a fresh angle.
                  </p>
                </div>
                <div>
                  <h3 className="text-sm font-bold text-[#0B104A]">
                    Adaptive hints &amp; practice
                  </h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-slate-600">
                    Questions scale to current mastery—offering gentle nudges
                    when stuck and harder problems when ready.
                  </p>
                </div>
                <div>
                  <h3 className="text-sm font-bold text-[#0B104A]">
                    Driven by real mistakes
                  </h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-slate-600">
                    Missed questions enter spaced revision so tricky formulas
                    resurface right before they fade.
                  </p>
                </div>
                <div>
                  <h3 className="text-sm font-bold text-[#0B104A]">
                    Clear daily direction
                  </h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-slate-600">
                    Your study planner lays out the highest-impact chapter or
                    flashcard deck to tackle next.
                  </p>
                </div>
              </div>
            </div>

            <AdaptiveCheckinWidget />
          </div>
        </section>

        {/* 5. STUDENT OUTCOMES (2x2 Clean Hairline Grid) */}
        <section className="py-20 sm:py-24">
          <div className="mx-auto max-w-6xl space-y-12 px-4 sm:px-6">
            <div className="max-w-2xl space-y-3">
              <p className="text-xs font-semibold tracking-wide text-[#1D4ED8]">
                For Your Child
              </p>
              <h2 className="font-display text-3xl font-bold tracking-tight text-[#0B104A] text-balance sm:text-4xl">
                What families notice after a few weeks.
              </h2>
              <p className="text-base leading-relaxed text-slate-600">
                Steadier homework evenings, fewer repeated exam slips, and clear
                visibility into study progress without hovering.
              </p>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              {OUTCOME_CARDS.map((card) => (
                <div
                  key={card.title}
                  className="flex flex-col gap-5 rounded-2xl border border-slate-200 bg-white p-6 sm:flex-row sm:items-start"
                >
                  <OutcomeGraphic type={card.accent} />
                  <div>
                    <h3 className="font-display text-xl font-bold text-[#0B104A]">
                      {card.title}
                    </h3>
                    <p className="mt-2 text-sm leading-relaxed text-slate-600">
                      {card.body}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* 6. INSIDE GO4GURU (5-Tab Interactive Workspace Tour) */}
        <section className="border-y border-slate-200/80 bg-[#F4F6FB] py-20 sm:py-24">
          <div className="mx-auto max-w-6xl space-y-10 px-4 sm:px-6">
            <div className="max-w-2xl space-y-3">
              <p className="text-xs font-semibold tracking-wide text-[#1D4ED8]">
                Inside Go4Guru
              </p>
              <h2 className="font-display text-3xl font-bold tracking-tight text-[#0B104A] text-balance sm:text-4xl">
                A complete classroom, not just a chat box.
              </h2>
              <p className="text-base leading-relaxed text-slate-600">
                Teaching, curriculum reading, guided practice, spaced revision,
                and progress tracking all work together in one workspace.
              </p>
            </div>

            <WorkspaceShowcase />

            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-slate-200 pt-6 text-xs text-slate-600">
              <span className="font-semibold text-[#0B104A]">Also inside:</span>
              <Link href="/homework" className="hover:text-[#1D4ED8]">
                Homework OCR &amp; Hints
              </Link>
              <Link href="/parent" className="hover:text-[#1D4ED8]">
                Parent Portal
              </Link>
              <Link href="/languages" className="hover:text-[#1D4ED8]">
                14+ Language Preferences
              </Link>
              <Link href="/teacher" className="hover:text-[#1D4ED8]">
                Teacher &amp; Mentor Hubs
              </Link>
            </div>
          </div>
        </section>

        {/* 7. HOW A SESSION WORKS (4-Step Editorial Sequence) */}
        <section className="py-20 sm:py-24">
          <div className="mx-auto max-w-6xl space-y-10 px-4 sm:px-6">
            <div className="space-y-3">
              <p className="text-xs font-semibold tracking-wide text-[#1D4ED8]">
                How a Session Works
              </p>
              <h2 className="font-display text-3xl font-bold tracking-tight text-[#0B104A] text-balance sm:text-4xl">
                Ask it, see it, practice it, retain it.
              </h2>
            </div>

            <div className="h-0.5 w-full bg-gradient-to-r from-[#0B104A] via-[#1D4ED8] to-[#84CC16]" />

            <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
              {SESSION_STEPS.map((step) => (
                <div
                  key={step.num}
                  className="space-y-2.5 border-slate-200 sm:border-l sm:pl-6 first:border-l-0 first:pl-0"
                >
                  <p className="font-mono text-xs font-semibold text-[#1D4ED8]">
                    {step.num}
                  </p>
                  <h3 className="text-base font-bold text-[#0B104A]">
                    {step.title}
                  </h3>
                  <p className="text-sm leading-relaxed text-slate-600">
                    {step.body}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* 8. FOR PARENTS */}
        <section
          id="parents"
          className="scroll-mt-20 border-y border-slate-200/80 bg-[#F4F6FB] py-20 sm:py-24"
        >
          <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 sm:px-6 lg:grid-cols-2">
            {/* Parent Summary Preview */}
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 shadow-[0_20px_48px_-30px_rgba(11,16,74,0.2)]">
              <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                <div>
                  <p className="text-xs font-semibold text-[#1D4ED8]">
                    Go4Guru Parent Portal · Weekly Digest
                  </p>
                  <p className="mt-0.5 text-sm font-bold text-[#0B104A]">
                    Meera · Grade 10 · CBSE &amp; STEM
                  </p>
                </div>
                <span className="font-mono text-xs font-semibold text-emerald-700">
                  Consent Verified
                </span>
              </div>

              <div className="mt-5 grid grid-cols-3 gap-3">
                <div className="rounded-xl bg-[#F8FAFC] p-3.5">
                  <p className="text-[11px] text-slate-500">Accuracy</p>
                  <p className="mt-1 font-mono text-xl font-bold text-[#0B104A] tabular-nums">
                    84%
                  </p>
                </div>
                <div className="rounded-xl bg-[#F8FAFC] p-3.5">
                  <p className="text-[11px] text-slate-500">Revision Cards</p>
                  <p className="mt-1 font-mono text-xl font-bold text-[#0B104A] tabular-nums">
                    24 done
                  </p>
                </div>
                <div className="rounded-xl bg-[#F8FAFC] p-3.5">
                  <p className="text-[11px] text-slate-500">Homework</p>
                  <p className="mt-1 font-mono text-xl font-bold text-[#0B104A] tabular-nums">
                    5 / 5
                  </p>
                </div>
              </div>

              <div className="mt-4 rounded-xl border border-slate-200/80 p-4 text-xs text-slate-600">
                <p className="font-semibold text-[#0B104A]">
                  Focus this week: Quadratic Discriminants &amp; Refraction
                </p>
                <p className="mt-1">
                  Privacy lock active: Raw student AI tutor chat transcripts are
                  never shared with guardians so students ask doubts freely.
                </p>
              </div>
            </div>

            <div className="space-y-6">
              <p className="text-xs font-semibold tracking-wide text-[#1D4ED8]">
                For Parents &amp; Guardians
              </p>
              <h2 className="font-display text-3xl font-bold tracking-tight text-[#0B104A] text-balance sm:text-4xl">
                See real learning progress, not just hours on a screen.
              </h2>
              <p className="text-base leading-relaxed text-slate-600">
                Parent summaries show what your child studied, which concepts
                clicked, and what needs another look. Go4Guru contains zero ads,
                never sells student data, and enforces guardian consent controls
                for minors.
              </p>

              <div className="divide-y divide-slate-200 border-y border-slate-200 text-sm font-semibold text-[#0B104A]">
                <Link
                  href="/parent"
                  className="flex items-center justify-between py-3.5 transition-colors hover:text-[#1D4ED8]"
                >
                  <span>Open Parent Portal &amp; privacy settings</span>
                  <span aria-hidden="true">→</span>
                </Link>
                <a
                  href="#pricing"
                  className="flex items-center justify-between py-3.5 transition-colors hover:text-[#1D4ED8]"
                >
                  <span>Clear family plans in USD &amp; INR</span>
                  <span aria-hidden="true">→</span>
                </a>
                <a
                  href="#faq"
                  className="flex items-center justify-between py-3.5 transition-colors hover:text-[#1D4ED8]"
                >
                  <span>Your questions, answered</span>
                  <span aria-hidden="true">→</span>
                </a>
              </div>
            </div>
          </div>
        </section>

        {/* 9. COMPETITIVE EXAM PREP */}
        <section
          id="exam-prep"
          className="scroll-mt-20 border-b border-amber-200/60 bg-[#FDF8F3] py-20 sm:py-24"
        >
          <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 sm:px-6 lg:grid-cols-[0.95fr_1.05fr]">
            <div className="space-y-5">
              <p className="text-xs font-semibold tracking-wide text-[#B45309]">
                Competitive &amp; Board Exam Prep
              </p>
              <h2 className="font-display text-3xl font-bold tracking-tight text-[#0B104A] text-balance sm:text-4xl">
                Aiming for a major exam? Follow its dedicated track.
              </h2>
              <p className="text-base leading-relaxed text-slate-600">
                Versioned exam blueprints, chapter weightages, verified Previous
                Year Question provenance, timed server-scored mocks, and
                speed-versus-accuracy diagnostics built right in.
              </p>
              <div className="pt-2">
                <Link
                  href="/exams"
                  className="inline-flex whitespace-nowrap items-center gap-2 rounded-lg bg-[#C2410C] px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#9A3412]"
                >
                  <span>Go to Exam Prep</span>
                  <span aria-hidden="true">→</span>
                </Link>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              {EXAM_TRACKS.map((track) => (
                <Link
                  key={track.id}
                  href={track.href}
                  className="group flex flex-col justify-between rounded-2xl border border-amber-200/80 bg-white p-6 transition-colors hover:border-[#C2410C]"
                >
                  <div>
                    <h3 className="font-display text-2xl font-bold text-[#0B104A]">
                      {track.title}
                    </h3>
                    <p className="mt-1.5 text-sm text-slate-600">
                      {track.subtitle}
                    </p>
                  </div>
                  <span
                    aria-hidden="true"
                    className="mt-5 inline-block text-sm font-semibold text-[#C2410C] transition-transform group-hover:translate-x-1"
                  >
                    →
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* 10. PRICING (USA USD & INDIA INR) */}
        <section id="pricing" className="scroll-mt-20 py-20 sm:py-24">
          <div className="mx-auto max-w-6xl space-y-10 px-4 sm:px-6">
            <div className="max-w-2xl space-y-3">
              <p className="text-xs font-semibold tracking-wide text-[#1D4ED8]">
                Pricing · USA &amp; India
              </p>
              <h2 className="font-display text-3xl font-bold tracking-tight text-[#0B104A] text-balance sm:text-4xl">
                Free to start. Straightforward plans as you grow.
              </h2>
              <p className="text-base leading-relaxed text-slate-600">
                Every tier includes interactive whiteboard lessons, server-checked
                practice, spaced revision, and weekly parent summaries. Switch
                between USD and INR anytime.
              </p>
            </div>

            <PricingSection />
          </div>
        </section>

        {/* 11. FAQ */}
        <section
          id="faq"
          className="scroll-mt-20 border-t border-slate-200/80 bg-white py-20 sm:py-24"
        >
          <div className="mx-auto max-w-4xl space-y-8 px-4 sm:px-6">
            <div className="space-y-2">
              <p className="text-xs font-semibold tracking-wide text-[#1D4ED8]">
                Frequently Asked Questions
              </p>
              <h2 className="font-display text-3xl font-bold tracking-tight text-[#0B104A]">
                Clear answers for students, parents, and schools.
              </h2>
            </div>

            <FaqAccordion />
          </div>
        </section>

        {/* 12. DEEP ROYAL NAVY CONVERSION BAND (Go4Guru Signature) */}
        <section className="relative overflow-hidden bg-gradient-to-br from-[#070B34] via-[#0B104A] to-[#17247E] py-20 text-white sm:py-24">
          <div className="mx-auto flex max-w-3xl flex-col items-center px-4 text-center sm:px-6">
            <div className="rounded-2xl border border-white/20 bg-[#090B46] p-2.5 shadow-lg">
              <img
                src="/assets/aistudio/image_2e20d262.png"
                alt="Go4Guru emblem"
                referrerPolicy="no-referrer"
                className="h-14 w-36 rounded-xl bg-[#090B46] object-cover object-center"
              />
            </div>

            <h2 className="mt-7 font-display text-3xl font-bold tracking-tight text-white text-balance sm:text-5xl">
              What do you want to{" "}
              <span className="italic text-[#A6F038]">master</span> today?
            </h2>

            <p className="mt-4 max-w-xl text-base text-slate-200">
              Open Go4Guru right in your browser, start a whiteboard lesson, or
              test your readiness across CBSE, JEE, NEET, and SAT.
            </p>

            <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
              <Link
                href="/register"
                className="inline-flex whitespace-nowrap items-center gap-2 rounded-lg bg-white px-6 py-3 text-sm font-semibold text-[#0B104A] transition-colors hover:bg-[#ECFCCB]"
              >
                <span>Start learning free</span>
                <span aria-hidden="true">→</span>
              </Link>
              <Link
                href="/curriculum"
                className="inline-flex whitespace-nowrap items-center gap-2 rounded-lg border border-white/30 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-white/10"
              >
                <span>Browse Curriculum</span>
              </Link>
            </div>

            <p className="mt-4 text-xs text-slate-300">
              Free starter access · No credit card needed
            </p>
          </div>
        </section>

        {/* 13. FOR SCHOOLS & EDUCATIONAL TOURS */}
        <section className="bg-[#FAFBFD] py-16">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <div className="flex flex-col justify-between gap-6 rounded-2xl border border-slate-200 bg-[#F2F5FC] p-7 sm:flex-row sm:items-center sm:p-9">
              <div className="max-w-2xl space-y-2">
                <p className="text-xs font-semibold tracking-wide text-[#1D4ED8]">
                  For Schools &amp; Global Educational Tours
                </p>
                <h2 className="font-display text-2xl font-bold text-[#0B104A] sm:text-3xl">
                  Bring Go4Guru to your school or organize an international STEM
                  tour.
                </h2>
                <p className="text-sm leading-relaxed text-slate-600">
                  Manage multi-branch classrooms, teacher grading, and cohort
                  analytics inside the Go4Guru Institution Portal—or partner
                  with GO4GURU Inc. for international educational tours across
                  the USA and beyond.
                </p>
              </div>
              <div className="flex shrink-0 flex-wrap gap-3">
                <Link
                  href="/institution"
                  className="inline-flex whitespace-nowrap items-center gap-2 rounded-lg bg-white px-5 py-2.5 text-sm font-semibold text-[#0B104A] border border-slate-300 transition-colors hover:border-[#0B104A]"
                >
                  <span>Institution Portal</span>
                  <span aria-hidden="true">→</span>
                </Link>
                <a
                  href="https://www.go4guru.com"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex whitespace-nowrap items-center gap-2 rounded-lg bg-[#0B104A] px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#17217A]"
                >
                  <span>go4guru.com</span>
                  <span aria-hidden="true">↗</span>
                </a>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* 14. CLEAN STRUCTURED FOOTER */}
      <footer className="border-t border-slate-200 bg-white pt-14 pb-10">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="grid gap-10 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
            <div className="space-y-4">
              <Link
                href="/"
                className="inline-flex items-center gap-3 whitespace-nowrap"
              >
                <img
                  src="/assets/aistudio/image_2e20d262.png"
                  alt="Go4Guru logo"
                  referrerPolicy="no-referrer"
                  className="h-9 w-[84px] rounded-lg bg-[#090B46] object-cover object-center"
                />
                <span className="font-display text-xl font-bold text-[#0B104A]">
                  Go4Guru
                </span>
              </Link>
              <p className="max-w-xs text-sm leading-relaxed text-slate-600">
                Online Tutoring &amp; International Educational Tour Operators
                by GO4GURU Inc., serving students and schools across the USA and
                India.
              </p>
              <p className="text-xs font-medium text-slate-500">
                Main website:{" "}
                <a
                  href="https://www.go4guru.com"
                  target="_blank"
                  rel="noreferrer"
                  className="text-[#1D4ED8] underline-offset-4 hover:underline"
                >
                  www.go4guru.com
                </a>
              </p>
            </div>

            <div className="space-y-3 text-sm">
              <p className="text-xs font-semibold tracking-wide text-slate-500">
                Learn
              </p>
              <ul className="space-y-2.5 text-slate-700">
                <li>
                  <Link href="/curriculum" className="hover:text-[#0B104A]">
                    Curriculum Explorer
                  </Link>
                </li>
                <li>
                  <Link href="/classroom" className="hover:text-[#0B104A]">
                    Live Whiteboard Classroom
                  </Link>
                </li>
                <li>
                  <Link href="/exams" className="hover:text-[#0B104A]">
                    Exam Prep (CBSE, JEE, NEET)
                  </Link>
                </li>
                <li>
                  <Link href="/homework" className="hover:text-[#0B104A]">
                    Homework AI Hints
                  </Link>
                </li>
                <li>
                  <Link href="/languages" className="hover:text-[#0B104A]">
                    Multilingual Preferences
                  </Link>
                </li>
              </ul>
            </div>

            <div className="space-y-3 text-sm">
              <p className="text-xs font-semibold tracking-wide text-slate-500">
                Portals &amp; Trust
              </p>
              <ul className="space-y-2.5 text-slate-700">
                <li>
                  <Link href="/parent" className="hover:text-[#0B104A]">
                    Parent Portal &amp; Child Safety
                  </Link>
                </li>
                <li>
                  <Link href="/teacher" className="hover:text-[#0B104A]">
                    Teacher Hub
                  </Link>
                </li>
                <li>
                  <Link href="/mentor" className="hover:text-[#0B104A]">
                    Mentor Hub
                  </Link>
                </li>
                <li>
                  <Link href="/institution" className="hover:text-[#0B104A]">
                    School &amp; Institution Admin
                  </Link>
                </li>
                <li>
                  <a href="#faq" className="hover:text-[#0B104A]">
                    FAQ &amp; Data Privacy
                  </a>
                </li>
              </ul>
            </div>

            <div className="space-y-3 text-sm">
              <p className="text-xs font-semibold tracking-wide text-slate-500">
                Get Started
              </p>
              <ul className="space-y-2.5 text-slate-700">
                <li>
                  <Link href="/register" className="hover:text-[#0B104A]">
                    Create Free Account
                  </Link>
                </li>
                <li>
                  <Link href="/login" className="hover:text-[#0B104A]">
                    Sign In
                  </Link>
                </li>
                <li>
                  <Link href="/dashboard" className="hover:text-[#0B104A]">
                    Open Web App
                  </Link>
                </li>
                <li>
                  <a
                    href="https://www.go4guru.com"
                    target="_blank"
                    rel="noreferrer"
                    className="hover:text-[#0B104A]"
                  >
                    Educational Tours ↗
                  </a>
                </li>
              </ul>
            </div>
          </div>

          <div className="mt-12 flex flex-col justify-between gap-3 border-t border-slate-200 pt-6 text-xs text-slate-500 sm:flex-row sm:items-center">
            <p>
              Go4Guru is a product of GO4GURU Inc. (USA &amp; India). Independent
              educational platform; not endorsed by or affiliated with NCERT,
              CBSE, NTA, or College Board.
            </p>
            <p className="shrink-0">
              © {new Date().getFullYear()} GO4GURU Inc. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
