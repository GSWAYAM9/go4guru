"use client";

import Link from "next/link";
import { useState } from "react";
import {
  CHECKIN_OPTIONS,
  FAQ_ITEMS,
  PRICING_TIERS,
  computeYearlySavingsPercent,
  formatAlternatePriceNote,
  formatPlanPrice,
  type BillingCycle,
  type CheckinOption,
  type PricingCurrency,
} from "@/lib/landing-data";

export function AdaptiveCheckinWidget() {
  const [selectedId, setSelectedId] = useState<CheckinOption["id"]>("oxygen");
  const selected =
    CHECKIN_OPTIONS.find((opt) => opt.id === selectedId) ?? CHECKIN_OPTIONS[0];

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-[0_20px_50px_-30px_rgba(11,16,74,0.18)] sm:p-8">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
        <span className="font-semibold text-[#1D4ED8]">
          Interactive Check-In · Photosynthesis
        </span>
        <span>Adapts to your answer</span>
      </div>

      <h3 className="mt-4 font-display text-xl font-semibold tracking-tight text-[#0B104A] text-balance sm:text-2xl">
        Which gas do green plants release while making food?
      </h3>

      <div
        className="mt-5 grid gap-3 sm:grid-cols-2"
        role="radiogroup"
        aria-label="Try an adaptive check-in answer"
      >
        {CHECKIN_OPTIONS.map((option) => {
          const active = option.id === selected.id;
          return (
            <button
              key={option.id}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => setSelectedId(option.id)}
              className={`rounded-xl border p-4 text-left transition-colors ${
                active
                  ? option.isCorrect
                    ? "border-emerald-600 bg-emerald-50/70"
                    : "border-[#1D4ED8] bg-[#EEF2FF]/70"
                  : "border-slate-200 bg-[#FAFBFD] hover:border-slate-300"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-semibold text-[#0B104A]">
                  “{option.answerLabel}”
                </span>
                <span
                  className={`text-xs font-medium ${
                    option.isCorrect ? "text-emerald-700" : "text-[#1D4ED8]"
                  }`}
                >
                  {option.isCorrect ? "Verified" : "Misconception"}
                </span>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-slate-600">
                {option.tutorResponse}
              </p>
              <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
                <div
                  className={`h-full rounded-full transition-all duration-200 ${
                    option.isCorrect ? "bg-emerald-600" : "bg-[#1D4ED8]"
                  }`}
                  style={{ width: `${option.progressPercent}%` }}
                />
              </div>
            </button>
          );
        })}
      </div>

      <div className="mt-4 rounded-xl border border-slate-200/80 bg-[#F8FAFC] p-4 text-xs leading-relaxed text-slate-700">
        <p className="font-semibold text-[#0B104A]">{selected.nextStep}</p>
        <p className="mt-1 text-slate-600">{selected.revisionNote}</p>
      </div>
    </div>
  );
}

export function PricingSection() {
  const [currency, setCurrency] = useState<PricingCurrency>("USD");
  const [cycle, setCycle] = useState<BillingCycle>("monthly");

  const maxSavings = Math.max(
    ...PRICING_TIERS.map((tier) => computeYearlySavingsPercent(tier, currency))
  );

  return (
    <div className="space-y-8">
      {/* Controls row: Currency (USA / India) & Cadence */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white p-1"
          role="group"
          aria-label="Select pricing currency"
        >
          {(["USD", "INR"] as const).map((code) => (
            <button
              key={code}
              type="button"
              aria-pressed={currency === code}
              onClick={() => setCurrency(code)}
              className={`whitespace-nowrap rounded-md px-3.5 py-1.5 text-xs font-semibold transition-colors ${
                currency === code
                  ? "bg-[#0B104A] text-white"
                  : "text-slate-600 hover:text-[#0B104A]"
              }`}
            >
              {code === "USD" ? "USA · USD ($)" : "India · INR (₹)"}
            </button>
          ))}
        </div>

        <div
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white p-1"
          role="group"
          aria-label="Select billing cycle"
        >
          <button
            type="button"
            aria-pressed={cycle === "monthly"}
            onClick={() => setCycle("monthly")}
            className={`whitespace-nowrap rounded-md px-3.5 py-1.5 text-xs font-semibold transition-colors ${
              cycle === "monthly"
                ? "bg-[#0B104A] text-white"
                : "text-slate-600 hover:text-[#0B104A]"
            }`}
          >
            Monthly
          </button>
          <button
            type="button"
            aria-pressed={cycle === "yearly"}
            onClick={() => setCycle("yearly")}
            className={`whitespace-nowrap rounded-md px-3.5 py-1.5 text-xs font-semibold transition-colors ${
              cycle === "yearly"
                ? "bg-[#0B104A] text-white"
                : "text-slate-600 hover:text-[#0B104A]"
            }`}
          >
            Yearly (Save up to {maxSavings}%)
          </button>
        </div>
      </div>

      {/* Free Starter Banner */}
      <div className="flex flex-col justify-between gap-5 rounded-2xl border border-[#0B104A]/15 bg-[#F2F5FC] p-6 sm:flex-row sm:items-center sm:p-7">
        <div className="space-y-2">
          <h3 className="font-display text-xl font-semibold text-[#0B104A]">
            Start free before choosing a plan
          </h3>
          <p className="text-sm text-slate-600">
            Free starter credits every month · Includes a 30-minute live
            whiteboard lesson · No credit card required
          </p>
        </div>
        <Link
          href="/register"
          className="inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-lg bg-[#0B104A] px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#17217A]"
        >
          <span>Start learning free</span>
          <span aria-hidden="true">→</span>
        </Link>
      </div>

      {/* 3 Paid Tiers */}
      <div className="grid gap-6 md:grid-cols-3">
        {PRICING_TIERS.map((tier) => {
          const priceLabel = formatPlanPrice(tier, currency, cycle);
          const altNote = formatAlternatePriceNote(tier, currency, cycle);
          return (
            <div
              key={tier.id}
              className={`flex flex-col justify-between rounded-2xl border bg-white p-6 ${
                tier.highlighted
                  ? "border-[#0B104A] shadow-[0_20px_48px_-28px_rgba(11,16,74,0.22)]"
                  : "border-slate-200"
              }`}
            >
              <div>
                <div className="flex items-baseline justify-between gap-2">
                  <h3 className="font-display text-2xl font-semibold text-[#0B104A]">
                    {tier.name}
                  </h3>
                  {tier.highlighted ? (
                    <span className="text-xs font-semibold text-[#1D4ED8]">
                      Most popular
                    </span>
                  ) : null}
                </div>
                <p className="mt-1.5 text-sm text-slate-600">{tier.tagline}</p>

                <div className="mt-6 flex items-baseline gap-1.5">
                  <span className="font-display text-4xl font-bold tracking-tight text-[#0B104A] tabular-nums">
                    {priceLabel}
                  </span>
                  <span className="text-sm text-slate-500">/ month</span>
                </div>
                <p className="mt-1.5 text-xs text-slate-500 tabular-nums">
                  {altNote}
                </p>

                <div className="my-5 border-t border-slate-100" />

                <p className="text-sm font-semibold text-slate-900">
                  {tier.tutoringSummary}
                </p>
                <p className="mt-1 text-xs leading-relaxed text-slate-600">
                  {tier.cadenceNote}
                </p>
              </div>

              <div className="mt-6">
                <Link
                  href={tier.ctaHref}
                  className={`inline-flex w-full items-center justify-center gap-2 whitespace-nowrap rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors ${
                    tier.highlighted
                      ? "bg-[#0B104A] text-white hover:bg-[#17217A]"
                      : "border border-slate-300 bg-white text-[#0B104A] hover:bg-slate-50"
                  }`}
                >
                  <span>Choose {tier.name}</span>
                  <span aria-hidden="true">→</span>
                </Link>
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500">
        <p>
          Showing {currency === "USD" ? "US Dollar ($)" : "Indian Rupee (₹)"}{" "}
          estimates for individual families. Institutional plans are managed in
          the{" "}
          <Link
            href="/institution"
            className="font-medium text-[#1D4ED8] underline-offset-4 hover:underline"
          >
            School &amp; Institution Portal
          </Link>
          .
        </p>
        <Link
          href="/register"
          className="font-semibold text-[#0B104A] hover:text-[#1D4ED8]"
        >
          Get started free →
        </Link>
      </div>
    </div>
  );
}

export function FaqAccordion() {
  const [openId, setOpenId] = useState<string>(FAQ_ITEMS[0].id);

  return (
    <div className="divide-y divide-slate-200 border-y border-slate-200">
      {FAQ_ITEMS.map((item) => {
        const isOpen = openId === item.id;
        return (
          <div key={item.id} className="py-5">
            <button
              type="button"
              aria-expanded={isOpen}
              onClick={() => setOpenId(isOpen ? "" : item.id)}
              className="flex w-full items-center justify-between gap-4 text-left"
            >
              <span className="text-base font-semibold text-[#0B104A]">
                {item.question}
              </span>
              <span
                aria-hidden="true"
                className="shrink-0 font-mono text-lg text-slate-500"
              >
                {isOpen ? "−" : "+"}
              </span>
            </button>
            {isOpen ? (
              <p className="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600">
                {item.answer}
              </p>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
