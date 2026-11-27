export type PricingCurrency = "USD" | "INR";
export type BillingCycle = "monthly" | "yearly";

export interface PricingTier {
  id: string;
  name: string;
  tagline: string;
  monthlyUsd: number;
  yearlyMonthlyUsd: number;
  monthlyInr: number;
  yearlyMonthlyInr: number;
  tutoringSummary: string;
  cadenceNote: string;
  highlighted?: boolean;
  ctaHref: string;
}

export interface ShowcaseTab {
  id: "whiteboard" | "curriculum" | "practice" | "revision" | "dashboard";
  label: string;
  headline: string;
  description: string;
  caption: string;
  href: string;
  ctaLabel: string;
}

export interface CheckinOption {
  id: "oxygen" | "co2";
  answerLabel: string;
  isCorrect: boolean;
  tutorResponse: string;
  nextStep: string;
  progressPercent: number;
  revisionNote: string;
}

export interface ExamTrack {
  id: string;
  title: string;
  subtitle: string;
  href: string;
}

export interface FaqItem {
  id: string;
  question: string;
  answer: string;
}

export const PRICING_TIERS: readonly PricingTier[] = [
  {
    id: "starter",
    name: "Starter",
    tagline: "Steady guided help a few times each week.",
    monthlyUsd: 19,
    yearlyMonthlyUsd: 15,
    monthlyInr: 1199,
    yearlyMonthlyInr: 949,
    tutoringSummary: "8–12 hours of guided tutoring monthly",
    cadenceNote: "Ideal for 3–4 focused sessions per week",
    ctaHref: "/register",
  },
  {
    id: "scholar",
    name: "Scholar",
    tagline: "Consistent daily learning across core school subjects.",
    monthlyUsd: 35,
    yearlyMonthlyUsd: 29,
    monthlyInr: 1899,
    yearlyMonthlyInr: 1599,
    tutoringSummary: "20–28 hours of live & AI board tutoring",
    cadenceNote: "Includes homework hints & weekly parent digest",
    highlighted: true,
    ctaHref: "/register",
  },
  {
    id: "exam-pro",
    name: "Exam Pro",
    tagline: "Intensive preparation for CBSE, JEE, NEET, and SAT.",
    monthlyUsd: 55,
    yearlyMonthlyUsd: 45,
    monthlyInr: 2899,
    yearlyMonthlyInr: 2399,
    tutoringSummary: "Up to 50 hours of tutoring & timed mocks",
    cadenceNote: "Full verified PYQ sets, analytics & revision plans",
    ctaHref: "/register",
  },
] as const;

export const SHOWCASE_TABS: readonly ShowcaseTab[] = [
  {
    id: "whiteboard",
    label: "Live Whiteboard",
    headline: "A patient tutor at the board, ready when you are.",
    description:
      "Go4Guru walks through formulas, diagrams, and worked examples step by step on an interactive board—pausing to check your understanding before moving ahead.",
    caption: "Go4Guru Live Classroom · Interactive SVG & KaTeX Whiteboard",
    href: "/classroom",
    ctaLabel: "Explore Live Classroom",
  },
  {
    id: "curriculum",
    label: "Curriculum & Notes",
    headline: "Your syllabus organized down to every concept.",
    description:
      "Navigate Grades 6–12 boards, chapters, topics, and learning objectives in one structured tree. Keep your personal notes and saved questions linked to each chapter.",
    caption: "Go4Guru Curriculum Explorer · Grades 6–12 Structured Syllabus",
    href: "/curriculum",
    ctaLabel: "Browse Curriculum",
  },
  {
    id: "practice",
    label: "Guided Practice",
    headline: "Practice that checks your reasoning, not just the answer.",
    description:
      "Work through targeted questions at your pace. Ask for graduated hints when you get stuck without spoiling the final solution, then verify math steps deterministically.",
    caption: "Go4Guru Practice & Homework AI · Graduated Hint Mode",
    href: "/practice",
    ctaLabel: "Try Guided Practice",
  },
  {
    id: "revision",
    label: "Revision & Mistakes",
    headline: "Every slip turns into a scheduled review card.",
    description:
      "Missed questions and weak concepts flow straight into spaced-repetition flashcards and daily study tasks so fragile topics come back right before you forget them.",
    caption: "Go4Guru Spaced Revision · SM-2 Flashcards & Study Planner",
    href: "/revision",
    ctaLabel: "Open Revision Planner",
  },
  {
    id: "dashboard",
    label: "Student Hub",
    headline: "One clear next step every time you sit down to study.",
    description:
      "Pick up exactly where you left off with recent assessments, subject accuracy, due flashcards, and quick entry into AI tutoring or timed exam simulations.",
    caption: "Go4Guru Student Dashboard · Unified Study Workspace",
    href: "/dashboard",
    ctaLabel: "Open Student Hub",
  },
] as const;

export const CHECKIN_OPTIONS: readonly CheckinOption[] = [
  {
    id: "oxygen",
    answerLabel: "Oxygen (O₂)",
    isCorrect: true,
    tutorResponse:
      "Spot on. Plants split water using sunlight and release oxygen as a byproduct while building glucose.",
    nextStep: "Advancing to light-dependent vs. Calvin cycle reactions.",
    progressPercent: 82,
    revisionNote:
      "Concept confirmed. Scheduled for a quick 7-day mastery check.",
  },
  {
    id: "co2",
    answerLabel: "Carbon dioxide (CO₂)",
    isCorrect: false,
    tutorResponse:
      "Close—plants absorb carbon dioxide through stomata as an input, then release oxygen after converting light energy.",
    nextStep: "Sketching the chloroplast input/output diagram on the board.",
    progressPercent: 46,
    revisionNote:
      "Saved to your Mistake Book. Returns in spaced revision before it fades.",
  },
] as const;

export const EXAM_TRACKS: readonly ExamTrack[] = [
  {
    id: "cbse",
    title: "CBSE Boards",
    subtitle: "Class 10 & 12 blueprints, step-marking rubrics",
    href: "/exams",
  },
  {
    id: "jee",
    title: "JEE Main & Advanced",
    subtitle: "Physics, Chemistry & Maths with partial marking",
    href: "/exams",
  },
  {
    id: "neet",
    title: "NEET UG",
    subtitle: "Biology, Chemistry & Physics speed diagnostics",
    href: "/exams",
  },
  {
    id: "sat",
    title: "SAT & Olympiads",
    subtitle: "Quantitative reasoning, STEM & global prep",
    href: "/exams",
  },
] as const;

export const EXPLORABLE_TOPICS: readonly { label: string; href: string }[] = [
  { label: "Quadratic Equations", href: "/tutor" },
  { label: "Photosynthesis", href: "/tutor" },
  { label: "Newton's Laws of Motion", href: "/curriculum" },
  { label: "Organic Nomenclature", href: "/curriculum" },
  { label: "Coordinate Geometry", href: "/practice" },
  { label: "Electrochemistry", href: "/practice" },
  { label: "Cell Division & Mitosis", href: "/tutor" },
  { label: "Trigonometric Identities", href: "/exams" },
  { label: "Probability & Combinatorics", href: "/exams" },
  { label: "Thermodynamics", href: "/curriculum" },
] as const;

export const FAQ_ITEMS: readonly FaqItem[] = [
  {
    id: "who-is-go4guru",
    question: "What is Go4Guru and how does GO4GURU Inc. operate across USA & India?",
    answer:
      "GO4GURU Inc. is an online tutoring company and international educational tour operator based in the USA and India (www.go4guru.com). This web platform brings our structured tutoring methodology online with interactive whiteboards, curriculum-aligned practice, competitive exam prep, and multilingual support.",
  },
  {
    id: "live-and-ai",
    question: "How does the live whiteboard classroom differ from a standard chatbot?",
    answer:
      "Instead of dumping a wall of text or giving away homework answers immediately, Go4Guru teaches in structured lesson stages on an interactive math and science whiteboard, checks understanding with graduated hints, and verifies algebra, physics units, and chemical equations deterministically.",
  },
  {
    id: "parent-visibility",
    question: "What can parents see in the Parent Portal?",
    answer:
      "Verified parents and guardians receive clear learning summaries—topics covered, accuracy trends, weak concepts, revision streaks, and upcoming tests—while keeping raw student AI tutor chat transcripts private so learners feel safe asking every question.",
  },
  {
    id: "exam-coverage",
    question: "Which school boards and competitive exams are supported?",
    answer:
      "Go4Guru supports Grades 6–12 STEM and core subjects alongside dedicated configurable exam workspaces for CBSE Board exams, JEE Main, JEE Advanced, NEET UG, and SAT/Olympiad quantitative prep—with verified PYQ provenance tags and timed server-scored mocks.",
  },
  {
    id: "educational-tours",
    question: "Does GO4GURU Inc. also organize International Educational Tours?",
    answer:
      "Yes. Alongside online tutoring, GO4GURU Inc. operates international STEM and academic educational tours—including NASA Space Camp and global university exposure programs for schools and student cohorts. Visit www.go4guru.com for upcoming tour itineraries.",
  },
] as const;

export function formatPlanPrice(
  tier: PricingTier,
  currency: PricingCurrency,
  cycle: BillingCycle
): string {
  const amount =
    currency === "USD"
      ? cycle === "monthly"
        ? tier.monthlyUsd
        : tier.yearlyMonthlyUsd
      : cycle === "monthly"
        ? tier.monthlyInr
        : tier.yearlyMonthlyInr;

  if (currency === "USD") {
    return `$${amount.toLocaleString("en-US")}`;
  }
  return `₹${amount.toLocaleString("en-IN")}`;
}

export function formatAlternatePriceNote(
  tier: PricingTier,
  currency: PricingCurrency,
  cycle: BillingCycle
): string {
  if (cycle === "monthly") {
    const yearlyRate = formatPlanPrice(tier, currency, "yearly");
    return `or ${yearlyRate}/month when billed annually`;
  }
  const annualTotal =
    currency === "USD"
      ? `$${(tier.yearlyMonthlyUsd * 12).toLocaleString("en-US")}`
      : `₹${(tier.yearlyMonthlyInr * 12).toLocaleString("en-IN")}`;
  return `Billed annually (${annualTotal}/year)`;
}

export function computeYearlySavingsPercent(
  tier: PricingTier,
  currency: PricingCurrency
): number {
  const monthly = currency === "USD" ? tier.monthlyUsd : tier.monthlyInr;
  const yearlyMonthly =
    currency === "USD" ? tier.yearlyMonthlyUsd : tier.yearlyMonthlyInr;
  if (monthly <= 0) return 0;
  return Math.round(((monthly - yearlyMonthly) / monthly) * 100);
}
