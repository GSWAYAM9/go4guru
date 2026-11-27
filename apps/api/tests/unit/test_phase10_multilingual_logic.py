"""Pure-stdlib unit & language-specific evaluation tests for Phase 10 Multilingual Expansion.

Runs directly with:
`PYTHONPATH=apps/api python3 -m unittest -v apps/api/tests/unit/test_phase10_multilingual_logic.py`
"""

from __future__ import annotations

import unittest

from src.modules.classroom.multilingual_logic import (
    CANONICAL_LANGUAGE_SEEDS,
    GlossaryTermEntry,
    LanguageEvaluationSample,
    audit_terminology_consistency,
    build_bilingual_explanation,
    check_script_fidelity,
    default_capability_map,
    extract_protected_notations,
    get_ui_localization_bundle,
    protect_notations_with_tokens,
    resolve_all_six_preferences,
    resolve_language_for_modality,
    restore_protected_notations,
    run_language_quality_suite,
    verify_notation_preservation,
)


class TestLanguageCapabilityRegistryHonesty(unittest.TestCase):
    def test_all_14_canonical_languages_present_with_differentiated_capabilities(self) -> None:
        caps = default_capability_map()
        expected = {"en", "hi", "bn", "ta", "te", "mr", "gu", "kn", "ml", "pa", "ur", "or", "as", "sa"}
        self.assertEqual(set(caps.keys()), expected)
        self.assertEqual(len(CANONICAL_LANGUAGE_SEEDS), 14)

        # Must never claim every language is production or TTS/STT verified
        production_langs = [c.language_code for c in caps.values() if c.capability_status == "production"]
        tts_langs = [c.language_code for c in caps.values() if c.tts_supported]
        stt_langs = [c.language_code for c in caps.values() if c.stt_supported]

        self.assertEqual(set(production_langs), {"en", "hi"})
        self.assertEqual(set(tts_langs), {"en", "hi"})
        self.assertEqual(set(stt_langs), {"en", "hi"})
        self.assertTrue(caps["ur"].rtl)
        self.assertFalse(caps["hi"].rtl)
        self.assertEqual(caps["sa"].capability_status, "planned")
        self.assertIsNone(caps["sa"].quality_score_pct)
        self.assertEqual(caps["or"].capability_status, "experimental")
        self.assertEqual(caps["as"].capability_status, "experimental")

        # Every language must document explicit limitations
        for code, cap in caps.items():
            self.assertTrue(
                bool(cap.known_limitations and cap.known_limitations.strip()),
                f"Language {code} missing honest known_limitations disclosure",
            )


class TestNotationPreservationGuard(unittest.TestCase):
    def test_extracts_and_verifies_latex_si_units_and_chemistry(self) -> None:
        src = (
            "Apply $v^2 = u^2 + 2as$ with $g = 9.8 m/s^2$, Avogadro constant 6.022 × 10^23 mol^-1, "
            "and reaction 2NaOH + H2SO4 -> Na2SO4 + 2H2O."
        )
        extracted = extract_protected_notations(src)
        self.assertIn("$v^2 = u^2 + 2as$", extracted.math_expressions)
        self.assertIn("$g = 9.8 m/s^2$", extracted.math_expressions)
        self.assertIn("6.022 × 10^23", extracted.scientific_notations)
        self.assertIn("H2SO4", extracted.chemical_formulas)
        self.assertIn("Na2SO4", extracted.chemical_formulas)
        self.assertIn("->", extracted.reaction_arrows)

        translated_good = (
            "नियत त्वरण में $v^2 = u^2 + 2as$ और $g = 9.8 m/s^2$ तथा 6.022 × 10^23 mol^-1 "
            "के साथ अभिक्रिया 2NaOH + H2SO4 -> Na2SO4 + 2H2O लागू करें।"
        )
        report_ok = verify_notation_preservation(src, translated_good)
        self.assertTrue(report_ok.all_preserved)
        self.assertEqual(report_ok.math_preservation_score, 100.0)
        self.assertEqual(report_ok.science_notation_score, 100.0)

    def test_detects_corrupted_formula_and_mutated_chemical_formula(self) -> None:
        src = "Velocity obeys $v = u + at$ for H2SO4 at 9.8 m/s^2."
        corrupted = "वेग $v = u - at$ का पालन करता है और H2O 9.8 पर होता है।"
        report = verify_notation_preservation(src, corrupted)
        self.assertFalse(report.math_preserved)
        self.assertFalse(report.science_preserved)
        self.assertFalse(report.all_preserved)
        self.assertIn("$v = u + at$", report.missing_math)
        self.assertIn("H2SO4", report.missing_science)

    def test_token_protection_round_trip(self) -> None:
        src = "Use $$F = ma$$ with 9.8 m/s^2 and 3.0e8 m/s."
        protected, token_map = protect_notations_with_tokens(src)
        self.assertNotIn("$$F = ma$$", protected)
        self.assertGreaterEqual(len(token_map), 2)
        restored = restore_protected_notations(protected, token_map)
        self.assertEqual(restored, src)


class TestSixDimensionLanguageFallback(unittest.TestCase):
    def test_independent_six_modalities_and_multi_hop_fallback(self) -> None:
        caps = default_capability_map()
        resolved = resolve_all_six_preferences(
            ui_language="ur",
            explanation_language="hi",
            voice_language="ta",
            subtitle_language="ta",
            question_language="mr",
            answer_language="bn",
            capabilities_by_code=caps,
        )
        # UI Urdu supported & RTL
        self.assertEqual(resolved["ui"].effective_language, "ur")
        self.assertFalse(resolved["ui"].fallback_applied)
        self.assertTrue(resolved["ui"].rtl)

        # Explanation Hindi supported natively
        self.assertEqual(resolved["explanation"].effective_language, "hi")
        self.assertFalse(resolved["explanation"].fallback_applied)

        # Voice Tamil disabled -> falls back to English with explicit subtitle preservation note
        self.assertEqual(resolved["voice"].effective_language, "en")
        self.assertTrue(resolved["voice"].fallback_applied)
        self.assertIn("subtitles remain available", resolved["voice"].fallback_reason or "")

        # Subtitle Tamil supported natively!
        self.assertEqual(resolved["subtitle"].effective_language, "ta")
        self.assertFalse(resolved["subtitle"].fallback_applied)

        # Question Marathi not verified -> falls back to configured fallback 'hi' (which supports question)
        self.assertEqual(resolved["question"].effective_language, "hi")
        self.assertTrue(resolved["question"].fallback_applied)

        # Answer Bengali supported
        self.assertEqual(resolved["answer"].effective_language, "bn")
        self.assertFalse(resolved["answer"].fallback_applied)

    def test_sanskrit_and_unknown_language_fallbacks(self) -> None:
        caps = default_capability_map()
        sa_voice = resolve_language_for_modality("sa", "voice", caps)
        self.assertTrue(sa_voice.fallback_applied)
        self.assertEqual(sa_voice.effective_language, "hi")

        unknown = resolve_language_for_modality("xx", "ui", caps)
        self.assertTrue(unknown.fallback_applied)
        self.assertEqual(unknown.effective_language, "en")


class TestBilingualGlossaryAndLanguageQualityEvals(unittest.TestCase):
    def setUp(self) -> None:
        self.caps = default_capability_map()
        self.glossary = [
            GlossaryTermEntry("physics.velocity", "Physics", "velocity", "hi", "वेग", "veg", True, r"\vec{v}"),
            GlossaryTermEntry("physics.acceleration", "Physics", "acceleration", "hi", "त्वरण", "tvaran", True, r"\vec{a}"),
            GlossaryTermEntry("physics.velocity", "Physics", "velocity", "ta", "திசைவேகம்", "thisaivegam", True, r"\vec{v}"),
            GlossaryTermEntry("physics.velocity", "Physics", "velocity", "ur", "رفتار", "raftar", True, r"\vec{v}"),
            GlossaryTermEntry("physics.velocity", "Physics", "velocity", "bn", "বেগ", "beg", True, r"\vec{v}"),
        ]

    def test_bilingual_explanation_preserves_katex_and_injects_stem_terms(self) -> None:
        src = "Calculate final velocity using $v^2 = u^2 + 2as$ under constant acceleration 9.8 m/s^2."
        out = build_bilingual_explanation(
            source_text=src,
            target_language_code="hi",
            bilingual_mode="bilingual_stem_en",
            glossary_terms=self.glossary,
        )
        self.assertIn("वेग (velocity)", out.rendered_text)
        self.assertIn("त्वरण (acceleration)", out.rendered_text)
        self.assertTrue(out.notation_report.all_preserved)
        self.assertIn("$v^2 = u^2 + 2as$", out.rendered_text)
        self.assertIn("9.8 m/s^2", out.rendered_text)

    def test_terminology_audit_flags_missing_terms(self) -> None:
        score, warnings = audit_terminology_consistency(
            source_text="Measure velocity and acceleration.",
            translated_text="अंतिम गति मापें।",
            target_language_code="hi",
            glossary_terms=self.glossary,
        )
        self.assertEqual(score, 0.0)
        self.assertEqual(len(warnings), 2)

    def test_language_specific_script_fidelity_across_indic_and_rtl_scripts(self) -> None:
        scripts_samples = [
            ("Devanagari", "नियत त्वरण में वेग (velocity) का मान $v = u + at$ है।"),
            ("Bengali", "স্থির ত্বরণে বেগ (velocity) সমীকরণ $v = u + at$ মেনে চলে।"),
            ("Tamil", "நிலையான முடுக்கத்தில் திசைவேகம் (velocity) $v = u + at$ ஆகும்."),
            ("Telugu", "స్థిర త్వరణంలో వేగం (velocity) సూత్రం $v = u + at$."),
            ("Perso-Arabic", "مستقل اسراع کے تحت رفتار (velocity) کا فارمولا $v = u + at$ ہے۔"),
            ("Gurmukhi", "ਸਥਿਰ ਪ੍ਰਵੇਗ ਹੇਠ ਵੇਗ (velocity) ਦਾ ਸੂਤਰ $v = u + at$ ਹੈ।"),
            ("Gujarati", "અચળ પ્રવેગમાં વેગ (velocity) નું સૂત્ર $v = u + at$ છે."),
            ("Kannada", "ಸ್ಥಿರ ವೇಗೋತ್ಕರ್ಷದಲ್ಲಿ ವೇಗ (velocity) ಸೂತ್ರ $v = u + at$."),
            ("Malayalam", "സ്ഥിര ത്വരണത്തിൽ പ്രവേഗം (velocity) സമവാക്യം $v = u + at$ ആണ്."),
            ("Odia", "ସ୍ଥିର ତ୍ୱରଣରେ ବେଗ (velocity) ସୂତ୍ର $v = u + at$ ଅଟେ।"),
        ]
        for script_name, text in scripts_samples:
            score, note = check_script_fidelity(text, script_name)
            self.assertGreaterEqual(score, 60.0, f"{script_name} failed script fidelity: {note}")

        # Untranslated English must fail Devanagari script check
        bad_score, bad_note = check_script_fidelity("Velocity equals u plus at.", "Devanagari")
        self.assertEqual(bad_score, 0.0)
        self.assertIsNotNone(bad_note)

    def test_quality_evaluation_suite_passes_valid_hindi_and_fails_corrupted_output(self) -> None:
        good_suite = run_language_quality_suite(
            capability=self.caps["hi"],
            modality="bilingual",
            samples=[
                LanguageEvaluationSample(
                    sample_id="hi-kinematics",
                    source_text="Final velocity under acceleration obeys $v^2 = u^2 + 2as$ with 9.8 m/s^2.",
                    candidate_text="नियत त्वरण (acceleration) में अंतिम वेग (velocity) $v^2 = u^2 + 2as$ और 9.8 m/s^2 का पालन करता है।",
                )
            ],
            glossary_terms=self.glossary,
        )
        self.assertTrue(good_suite.passed)
        self.assertEqual(good_suite.math_preservation_score, 100.0)
        self.assertEqual(good_suite.science_notation_score, 100.0)
        self.assertGreaterEqual(good_suite.overall_score, 90.0)

        bad_suite = run_language_quality_suite(
            capability=self.caps["ta"],
            modality="bilingual",
            samples=[
                LanguageEvaluationSample(
                    sample_id="ta-corrupted",
                    source_text="Velocity obeys $v^2 = u^2 + 2as$ for H2SO4.",
                    candidate_text="Velocity obeys wrong formula without Tamil script.",
                )
            ],
            glossary_terms=self.glossary,
        )
        self.assertFalse(bad_suite.passed)
        self.assertEqual(bad_suite.script_fidelity_score, 0.0)
        self.assertEqual(bad_suite.math_preservation_score, 0.0)

    def test_ui_localization_bundle_tracks_coverage_honestly(self) -> None:
        en_bundle = get_ui_localization_bundle("en")
        self.assertEqual(en_bundle["coverage_pct"], 100.0)
        self.assertEqual(en_bundle["fallback_keys"], [])

        hi_bundle = get_ui_localization_bundle("hi")
        self.assertEqual(hi_bundle["coverage_pct"], 100.0)
        self.assertEqual(hi_bundle["strings"]["nav.languages"], "भाषाएँ")

        ur_bundle = get_ui_localization_bundle("ur")
        self.assertTrue(ur_bundle["rtl"])
        self.assertGreater(ur_bundle["coverage_pct"], 30.0)
        self.assertGreater(len(ur_bundle["fallback_keys"]), 0)

        sa_bundle = get_ui_localization_bundle("sa")
        self.assertEqual(sa_bundle["effective_language"], "en")
        self.assertEqual(sa_bundle["coverage_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
