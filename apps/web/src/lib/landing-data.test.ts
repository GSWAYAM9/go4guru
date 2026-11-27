import test from "node:test";
import assert from "node:assert/strict";
import {
  CHECKIN_OPTIONS,
  EXAM_TRACKS,
  FAQ_ITEMS,
  PRICING_TIERS,
  SHOWCASE_TABS,
  computeYearlySavingsPercent,
  formatAlternatePriceNote,
  formatPlanPrice,
} from "./landing-data";

test("formats USD and INR plan prices for monthly and yearly billing", () => {
  const scholar = PRICING_TIERS.find((t) => t.id === "scholar");
  assert.ok(scholar);
  assert.equal(formatPlanPrice(scholar, "USD", "monthly"), "$35");
  assert.equal(formatPlanPrice(scholar, "USD", "yearly"), "$29");
  assert.equal(formatPlanPrice(scholar, "INR", "monthly"), "₹1,899");
  assert.equal(formatPlanPrice(scholar, "INR", "yearly"), "₹1,599");
});

test("computes positive annual savings percentage across all tiers and currencies", () => {
  for (const tier of PRICING_TIERS) {
    const usdSavings = computeYearlySavingsPercent(tier, "USD");
    const inrSavings = computeYearlySavingsPercent(tier, "INR");
    assert.ok(usdSavings > 0 && usdSavings < 50);
    assert.ok(inrSavings > 0 && inrSavings < 50);
  }
});

test("builds accurate alternate billing cadence notes", () => {
  const starter = PRICING_TIERS[0];
  assert.equal(
    formatAlternatePriceNote(starter, "USD", "monthly"),
    "or $15/month when billed annually"
  );
  assert.equal(
    formatAlternatePriceNote(starter, "USD", "yearly"),
    "Billed annually ($180/year)"
  );
});

test("showcase tabs, exam tracks, check-in options, and FAQs have valid routes and structure", () => {
  assert.equal(SHOWCASE_TABS.length, 5);
  for (const tab of SHOWCASE_TABS) {
    assert.ok(tab.href.startsWith("/"), `Invalid route: ${tab.href}`);
    assert.ok(tab.headline.length > 10);
  }
  assert.equal(EXAM_TRACKS.length, 4);
  assert.equal(CHECKIN_OPTIONS.filter((o) => o.isCorrect).length, 1);
  assert.equal(CHECKIN_OPTIONS.filter((o) => !o.isCorrect).length, 1);
  assert.ok(FAQ_ITEMS.length >= 5);
});
