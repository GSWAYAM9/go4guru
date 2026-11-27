import assert from "node:assert/strict";
import test from "node:test";
import {
  FALLBACK_LANGUAGE_REGISTRY,
  computeUiLocalizationCoverage,
  getCapabilityStatusMeta,
  resolveModalityFallbackClient,
  translateUiKey,
  verifyClientNotationPreservation,
} from "./multilingual-helpers";

test("truthful 14-language registry tracks distinct statuses without claiming full parity", () => {
  assert.equal(FALLBACK_LANGUAGE_REGISTRY.length, 14);
  const ttsVerified = FALLBACK_LANGUAGE_REGISTRY.filter((c) => c.tts_supported).map(
    (c) => c.language_code
  );
  assert.deepEqual(ttsVerified.sort(), ["en", "hi"]);
  const urdu = FALLBACK_LANGUAGE_REGISTRY.find((c) => c.language_code === "ur");
  assert.equal(urdu?.rtl, true);
  const sanskrit = FALLBACK_LANGUAGE_REGISTRY.find((c) => c.language_code === "sa");
  assert.equal(sanskrit?.capability_status, "planned");
  assert.equal(sanskrit?.quality_score_pct, null);
});

test("UI localization falls back cleanly to English per missing key and reports honest coverage", () => {
  assert.equal(translateUiKey("hi", "nav.languages"), "भाषाएँ");
  assert.equal(translateUiKey("ur", "nav.languages"), "زبانیں");
  // Missing key in Urdu falls back to English
  assert.equal(translateUiKey("ur", "nav.adaptive"), "Adaptive Mastery");

  const hiCov = computeUiLocalizationCoverage("hi");
  assert.equal(hiCov.coveragePct, 100);
  assert.equal(hiCov.rtl, false);

  const urCov = computeUiLocalizationCoverage("ur");
  assert.equal(urCov.rtl, true);
  assert.ok(urCov.coveragePct > 30 && urCov.coveragePct < 100);

  const saCov = computeUiLocalizationCoverage("sa");
  assert.equal(saCov.coveragePct, 0);
});

test("6-modality client fallback resolver routes unverified voice & question dimensions honestly", () => {
  const taVoice = resolveModalityFallbackClient(
    "ta",
    "voice",
    FALLBACK_LANGUAGE_REGISTRY
  );
  assert.equal(taVoice.fallback_applied, true);
  assert.equal(taVoice.effective_language, "en");
  assert.match(taVoice.fallback_reason ?? "", /subtitles remain active/i);

  const taSub = resolveModalityFallbackClient(
    "ta",
    "subtitle",
    FALLBACK_LANGUAGE_REGISTRY
  );
  assert.equal(taSub.fallback_applied, false);
  assert.equal(taSub.effective_language, "ta");

  const mrQuestion = resolveModalityFallbackClient(
    "mr",
    "question",
    FALLBACK_LANGUAGE_REGISTRY
  );
  assert.equal(mrQuestion.fallback_applied, true);
  assert.equal(mrQuestion.effective_language, "hi");
});

test("mathematical and scientific notation preservation checker detects intact vs corrupted formulas", () => {
  const src = "Use $v^2 = u^2 + 2as$ with 9.8 m/s^2 and H2SO4 at 6.022 × 10^23 mol^-1.";
  const intact = verifyClientNotationPreservation(
    src,
    "वेग के लिए $v^2 = u^2 + 2as$, 9.8 m/s^2, H2SO4 और 6.022 × 10^23 mol^-1 उपयोग करें।"
  );
  assert.equal(intact.all_preserved, true);
  assert.equal(intact.math_preservation_score, 100);
  assert.equal(intact.science_notation_score, 100);

  const broken = verifyClientNotationPreservation(
    src,
    "वेग के लिए $v^2 = u^2 - 2as$ और H2O उपयोग करें।"
  );
  assert.equal(broken.all_preserved, false);
  assert.equal(broken.math_preserved, false);
  assert.equal(broken.science_preserved, false);
  assert.ok(broken.missing_math.includes("$v^2 = u^2 + 2as$"));
  assert.ok(broken.missing_science.includes("H2SO4"));
});

test("capability status badges use valid StatusBadge tones only", () => {
  assert.equal(getCapabilityStatusMeta("production").tone, "healthy");
  assert.equal(getCapabilityStatusMeta("beta").tone, "degraded");
  assert.equal(getCapabilityStatusMeta("experimental").tone, "degraded");
  assert.equal(getCapabilityStatusMeta("planned").tone, "neutral");
});
