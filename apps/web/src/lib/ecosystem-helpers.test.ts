import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  computeGradeOverrideDelta,
  evaluateSeatQuotaHealth,
  formatConsentStatusLabel,
  sanitizeSlugInput,
} from "./ecosystem-helpers.ts";

describe("Phase 7 & 8 ecosystem pure helpers", () => {
  it("computes teacher override delta and effective percentage accurately", () => {
    const res = computeGradeOverrideDelta({
      aiSuggestedScore: 14.5,
      teacherScore: 17,
      maxMarks: 20,
    });
    assert.equal(res.effectiveScore, 17);
    assert.equal(res.percentage, 85);
    assert.equal(res.overridden, true);
    assert.equal(res.deltaFromAi, 2.5);
  });

  it("falls back to AI suggested score when teacher has not overridden", () => {
    const res = computeGradeOverrideDelta({
      aiSuggestedScore: 12,
      teacherScore: null,
      maxMarks: 20,
    });
    assert.equal(res.effectiveScore, 12);
    assert.equal(res.percentage, 60);
    assert.equal(res.overridden, false);
    assert.equal(res.deltaFromAi, null);
  });

  it("evaluates tenant seat utilization and pauses on cancelled subscription", () => {
    const healthy = evaluateSeatQuotaHealth(45, 150, "active");
    assert.equal(healthy.tone, "healthy");
    assert.equal(healthy.utilizationPct, 30);
    assert.equal(healthy.warning, null);

    const warning = evaluateSeatQuotaHealth(140, 150, "active");
    assert.equal(warning.tone, "degraded");
    assert.match(warning.warning ?? "", /Approaching seat limit/);

    const paused = evaluateSeatQuotaHealth(10, 150, "cancelled");
    assert.equal(paused.tone, "degraded");
    assert.match(paused.warning ?? "", /paused/i);
  });

  it("formats parent consent status badges deterministically", () => {
    assert.deepEqual(formatConsentStatusLabel("verified"), {
      label: "Consent Verified",
      tone: "healthy",
    });
    assert.deepEqual(formatConsentStatusLabel("pending"), {
      label: "Consent Pending",
      tone: "neutral",
    });
    assert.deepEqual(formatConsentStatusLabel("revoked"), {
      label: "Revoked",
      tone: "degraded",
    });
  });

  it("normalizes institution tenant slugs safely", () => {
    assert.equal(
      sanitizeSlugInput("  Delhi Public School — North! "),
      "delhi-public-school-north"
    );
  });
});
