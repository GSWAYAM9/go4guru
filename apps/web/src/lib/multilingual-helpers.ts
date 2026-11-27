/**
 * Pure TypeScript Phase 10 Multilingual helpers:
 * - Client-side UI localization catalog with deterministic English fallback & coverage metrics
 * - Truthful 14-language empirical registry baseline (matching backend seed)
 * - 6-modality independent fallback resolver
 * - Mathematical & scientific notation preservation checker
 * - Presentation tone helpers for StatusBadge ("healthy" | "degraded" | "neutral")
 */

import type {
  BilingualMode,
  LanguageCapabilityOut,
  LanguageModalityKey,
  ModalityResolutionOut,
  NotationPreservationOut,
} from "@go4guru/contracts";

export type BadgeTone = "healthy" | "degraded" | "neutral";

export const UI_LOCALIZATION_CATALOG: Record<string, Record<string, string>> = {
  en: {
    "nav.home": "Home",
    "nav.curriculum": "Curriculum",
    "nav.dashboard": "Dashboard",
    "nav.practice": "Practice",
    "nav.quizzes": "Quizzes",
    "nav.assessments": "Assessments",
    "nav.exams": "Exam Prep",
    "nav.tutor": "AI Tutor",
    "nav.classroom": "Live Classroom",
    "nav.homework": "Homework AI",
    "nav.adaptive": "Adaptive Mastery",
    "nav.revision": "Revision & Plan",
    "nav.analytics": "Analytics",
    "nav.notes": "Notes & Saved",
    "nav.languages": "Languages",
    "nav.teacher": "Teacher Hub",
    "nav.mentor": "Mentor Hub",
    "nav.parent": "Parent Portal",
    "nav.institution": "Institution",
    "nav.admin": "Admin Studio",
    "auth.sign_in": "Sign In",
    "auth.register": "Register",
    "auth.sign_out": "Sign Out",
    "languages.title": "Multilingual Learning & Language Capability Hub",
    "languages.subtitle":
      "Configure independent languages for UI, explanations, voice, subtitles, questions, and answers with transparent provider capability tracking.",
    "languages.save_preferences": "Save Language Preferences",
    "footer.disclaimer":
      "GuruSetu AI — Independent educational ecosystem; not endorsed by or affiliated with NCERT, CBSE, or NTA.",
  },
  hi: {
    "nav.home": "होम",
    "nav.curriculum": "पाठ्यक्रम",
    "nav.dashboard": "डैशबोर्ड",
    "nav.practice": "अभ्यास",
    "nav.quizzes": "क्विज़",
    "nav.assessments": "मूल्यांकन",
    "nav.exams": "परीक्षा तैयारी",
    "nav.tutor": "AI ट्यूटर",
    "nav.classroom": "लाइव क्लासरूम",
    "nav.homework": "होमवर्क AI",
    "nav.adaptive": "अनुकूली महारत",
    "nav.revision": "पुनरावृत्ति योजना",
    "nav.analytics": "विश्लेषण",
    "nav.notes": "नोट्स",
    "nav.languages": "भाषाएँ",
    "nav.teacher": "शिक्षक केंद्र",
    "nav.mentor": "मेंटर केंद्र",
    "nav.parent": "अभिभावक पोर्टल",
    "nav.institution": "संस्थान",
    "nav.admin": "एडमिन स्टूडियो",
    "auth.sign_in": "साइन इन",
    "auth.register": "पंजीकरण",
    "auth.sign_out": "साइन आउट",
    "languages.title": "बहुभाषी शिक्षण और भाषा क्षमता केंद्र",
    "languages.subtitle":
      "UI, व्याख्या, आवाज़, उपशीर्षक, प्रश्न और उत्तर के लिए स्वतंत्र भाषाएँ चुनें और वास्तविक प्रदाता क्षमता देखें।",
    "languages.save_preferences": "भाषा प्राथमिकताएँ सहेजें",
    "footer.disclaimer":
      "GuruSetu AI — स्वतंत्र शैक्षिक मंच; NCERT, CBSE या NTA से संबद्ध नहीं।",
  },
  bn: {
    "nav.home": "হোম",
    "nav.curriculum": "পাঠ্যক্রম",
    "nav.dashboard": "ড্যাশবোর্ড",
    "nav.practice": "অনুশীলন",
    "nav.quizzes": "কুইজ",
    "nav.assessments": "মূল্যায়ন",
    "nav.exams": "পরীক্ষার প্রস্তুতি",
    "nav.tutor": "AI টিউটর",
    "nav.classroom": "লাইভ ক্লাসরুম",
    "nav.homework": "হোমওয়ার্ক AI",
    "nav.languages": "ভাষাসমূহ",
    "auth.sign_in": "সাইন ইন",
    "auth.register": "নিবন্ধন",
    "auth.sign_out": "সাইন আউট",
    "languages.title": "বহুভাষিক শিক্ষণ ও ভাষা সক্ষমতা কেন্দ্র",
    "languages.save_preferences": "ভাষা পছন্দ সংরক্ষণ করুন",
  },
  ta: {
    "nav.home": "முகப்பு",
    "nav.curriculum": "பாடத்திட்டம்",
    "nav.dashboard": "கட்டுப்பாட்டுப் பலகம்",
    "nav.practice": "பயிற்சி",
    "nav.quizzes": "வினாடி வினா",
    "nav.exams": "தேர்வு தயாரிப்பு",
    "nav.tutor": "AI ஆசிரியர்",
    "nav.classroom": "நேரலை வகுப்பறை",
    "nav.homework": "வீட்டுப்பாடம் AI",
    "nav.languages": "மொழிகள்",
    "auth.sign_in": "உள்நுழை",
    "auth.register": "பதிவு செய்",
    "auth.sign_out": "வெளியேறு",
    "languages.title": "பன்மொழி கற்றல் மற்றும் மொழி திறன் மையம்",
    "languages.save_preferences": "மொழி விருப்பங்களைச் சேமி",
  },
  te: {
    "nav.home": "హోమ్",
    "nav.curriculum": "పాఠ్యాంశాలు",
    "nav.dashboard": "డాష్‌బోర్డ్",
    "nav.practice": "అభ్యాసం",
    "nav.exams": "పరీక్ష సన్నద్ధత",
    "nav.tutor": "AI ట్యూటర్",
    "nav.classroom": "లైవ్ క్లాస్‌రూమ్",
    "nav.languages": "భాషలు",
    "auth.sign_in": "సైన్ ఇన్",
    "auth.register": "నమోదు",
    "auth.sign_out": "సైన్ అవుట్",
    "languages.title": "బహుభాషా అభ్యాస & భాషా సామర్థ్య కేంద్రం",
    "languages.save_preferences": "భాషా ప్రాధాన్యతలను సేవ్ చేయండి",
  },
  mr: {
    "nav.home": "मुख्यपृष्ठ",
    "nav.curriculum": "अभ्यासक्रम",
    "nav.dashboard": "डॅशबोर्ड",
    "nav.practice": "सराव",
    "nav.exams": "परीक्षा तयारी",
    "nav.tutor": "AI शिक्षक",
    "nav.classroom": "लाइव्ह वर्ग",
    "nav.languages": "भाषा",
    "auth.sign_in": "साइन इन",
    "auth.register": "नोंदणी",
    "auth.sign_out": "साइन आउट",
    "languages.title": "बहुभाषिक शिक्षण आणि भाषा क्षमता केंद्र",
    "languages.save_preferences": "भाषा प्राधान्ये जतन करा",
  },
  gu: {
    "nav.home": "હોમ",
    "nav.curriculum": "અભ્યાસક્રમ",
    "nav.dashboard": "ડેશબોર્ડ",
    "nav.practice": "અભ્યાસ",
    "nav.exams": "પરીક્ષા તૈયારી",
    "nav.tutor": "AI ટ્યુટર",
    "nav.languages": "ભાષાઓ",
    "auth.sign_in": "સાઇન ઇન",
    "auth.sign_out": "સાઇન આઉટ",
    "languages.title": "બહુભાષી શિક્ષણ અને ભાષા ક્ષમતા કેન્દ્ર",
  },
  kn: {
    "nav.home": "ಮುಖಪುಟ",
    "nav.curriculum": "ಪಠ್ಯಕ್ರಮ",
    "nav.dashboard": "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್",
    "nav.practice": "ಅಭ್ಯಾಸ",
    "nav.exams": "ಪರೀಕ್ಷಾ ತಯಾರಿ",
    "nav.tutor": "AI ಬೋಧಕ",
    "nav.languages": "ಭಾಷೆಗಳು",
    "auth.sign_in": "ಸೈನ್ ಇನ್",
    "auth.sign_out": "ಸೈನ್ ಔಟ್",
    "languages.title": "ಬಹುಭಾಷಾ ಕಲಿಕೆ ಮತ್ತು ಭಾಷಾ ಸಾಮರ್ಥ್ಯ ಕೇಂದ್ರ",
  },
  ml: {
    "nav.home": "ഹോം",
    "nav.curriculum": "പാഠ്യപദ്ധതി",
    "nav.dashboard": "ഡാഷ്ബോർഡ്",
    "nav.practice": "പരിശീലനം",
    "nav.exams": "പരീക്ഷാ തയ്യാറെടുപ്പ്",
    "nav.tutor": "AI ട്യൂട്ടർ",
    "nav.languages": "ഭാഷകൾ",
    "auth.sign_in": "സൈನ್ ഇൻ",
    "auth.sign_out": "സൈൻ ഔട്ട്",
    "languages.title": "ബഹുഭാഷാ പഠനവും ഭാഷാ ശേഷി കേന്ദ്രവും",
  },
  pa: {
    "nav.home": "ਹੋਮ",
    "nav.curriculum": "ਪਾਠਕ੍ਰਮ",
    "nav.dashboard": "ਡੈਸ਼ਬੋਰਡ",
    "nav.practice": "ਅਭਿਆਸ",
    "nav.exams": "ਪ੍ਰੀਖਿਆ ਤਿਆਰੀ",
    "nav.tutor": "AI ਟਿਊਟਰ",
    "nav.languages": "ਭਾਸ਼ਾਵਾਂ",
    "auth.sign_in": "ਸਾਈਨ ਇਨ",
    "auth.sign_out": "ਸਾਈਨ ਆਉਟ",
    "languages.title": "ਬਹੁ-ਭਾਸ਼ਾਈ ਸਿੱਖਿਆ ਅਤੇ ਭਾਸ਼ਾ ਸਮਰੱਥਾ ਕੇਂਦਰ",
  },
  ur: {
    "nav.home": "ہوم",
    "nav.curriculum": "نصاب",
    "nav.dashboard": "ڈیش بورڈ",
    "nav.practice": "مشق",
    "nav.quizzes": "کوئز",
    "nav.exams": "امتحان کی تیاری",
    "nav.tutor": "AI ٹیوٹر",
    "nav.classroom": "لائیو کلاس روم",
    "nav.languages": "زبانیں",
    "auth.sign_in": "سائن ان",
    "auth.register": "رجسٹر",
    "auth.sign_out": "سائن آؤٹ",
    "languages.title": "کثیر لسانی تعلیم اور زبان کی صلاحیت کا مرکز",
    "languages.save_preferences": "زبان کی ترجیحات محفوظ کریں",
  },
};

export const FALLBACK_LANGUAGE_REGISTRY: LanguageCapabilityOut[] = [
  {
    language_code: "en",
    display_name: "English",
    native_name: "English",
    script_name: "Latin",
    rtl: false,
    capability_status: "production",
    testing_status: "passed",
    availability_status: "available",
    text_quality_tier: "tier_1_native",
    translation_status: "native",
    ui_supported: true,
    explanation_supported: true,
    bilingual_supported: true,
    tts_supported: true,
    stt_supported: true,
    voice_provider: "elevenlabs",
    stt_provider: "elevenlabs_scribe",
    translation_provider: "native_canonical",
    pronunciation_tier: "high",
    subtitle_supported: true,
    question_supported: true,
    answer_supported: true,
    academic_review_status: "approved",
    fallback_language_code: "en",
    quality_score_pct: 98.0,
    last_evaluated_at: null,
    provider_matrix: {
      llm: { provider: "gemini/openai/anthropic", status: "verified", quality: "tier_1" },
      tts: { provider: "elevenlabs", status: "verified_key_required", quality: "high" },
      stt: { provider: "elevenlabs_scribe", status: "verified_key_required", quality: "high" },
      translation: { provider: "native_canonical", status: "verified", quality: "native" },
    },
    known_limitations:
      "Primary canonical STEM language. Live audio synthesis and cloud STT require ELEVENLABS_API_KEY; otherwise timed subtitles and browser speech/text fallback apply.",
  },
  {
    language_code: "hi",
    display_name: "Hindi",
    native_name: "हिन्दी",
    script_name: "Devanagari",
    rtl: false,
    capability_status: "production",
    testing_status: "passed",
    availability_status: "available",
    text_quality_tier: "tier_1",
    translation_status: "glossary_guided",
    ui_supported: true,
    explanation_supported: true,
    bilingual_supported: true,
    tts_supported: true,
    stt_supported: true,
    voice_provider: "elevenlabs",
    stt_provider: "elevenlabs_scribe",
    translation_provider: "glossary_guided_llm",
    pronunciation_tier: "good_bilingual",
    subtitle_supported: true,
    question_supported: true,
    answer_supported: true,
    academic_review_status: "approved",
    fallback_language_code: "en",
    quality_score_pct: 91.5,
    last_evaluated_at: null,
    provider_matrix: {
      llm: { provider: "gemini/openai/anthropic", status: "verified", quality: "tier_1" },
      tts: { provider: "elevenlabs", status: "verified_key_required", quality: "good_bilingual" },
      stt: { provider: "elevenlabs_scribe", status: "verified_key_required", quality: "good" },
      translation: { provider: "glossary_guided_llm", status: "reviewed", quality: "high" },
    },
    known_limitations:
      "Recommended in Bilingual STEM mode (Devanagari prose + English technical symbols). ElevenLabs key required for live TTS/STT.",
  },
  {
    language_code: "bn",
    display_name: "Bengali",
    native_name: "বাংলা",
    script_name: "Bengali",
    rtl: false,
    capability_status: "beta",
    testing_status: "partial",
    availability_status: "limited",
    text_quality_tier: "tier_2_beta",
    translation_status: "beta_review",
    ui_supported: true,
    explanation_supported: true,
    bilingual_supported: true,
    tts_supported: false,
    stt_supported: false,
    voice_provider: null,
    stt_provider: null,
    translation_provider: "glossary_guided_llm",
    pronunciation_tier: null,
    subtitle_supported: true,
    question_supported: false,
    answer_supported: true,
    academic_review_status: "in_review",
    fallback_language_code: "en",
    quality_score_pct: 81.0,
    last_evaluated_at: null,
    provider_matrix: {
      llm: { provider: "gemini/openai", status: "beta", quality: "tier_2" },
      tts: { provider: "unverified", status: "disabled_pending_qa", quality: "untested" },
      stt: { provider: "unverified", status: "disabled_pending_qa", quality: "untested" },
      translation: { provider: "glossary_guided_llm", status: "in_review", quality: "beta" },
    },
    known_limitations:
      "UI localization, bilingual explanations, and subtitles available in beta. TTS/STT disabled and question stems fall back to English until native STEM QA passes.",
  },
  {
    language_code: "ta",
    display_name: "Tamil",
    native_name: "தமிழ்",
    script_name: "Tamil",
    rtl: false,
    capability_status: "beta",
    testing_status: "partial",
    availability_status: "limited",
    text_quality_tier: "tier_2_beta",
    translation_status: "beta_review",
    ui_supported: true,
    explanation_supported: true,
    bilingual_supported: true,
    tts_supported: false,
    stt_supported: false,
    voice_provider: null,
    stt_provider: null,
    translation_provider: "glossary_guided_llm",
    pronunciation_tier: null,
    subtitle_supported: true,
    question_supported: false,
    answer_supported: true,
    academic_review_status: "in_review",
    fallback_language_code: "en",
    quality_score_pct: 82.0,
    last_evaluated_at: null,
    provider_matrix: {
      llm: { provider: "gemini/openai", status: "beta", quality: "tier_2" },
      tts: { provider: "unverified", status: "disabled_pending_qa", quality: "untested" },
      stt: { provider: "unverified", status: "disabled_pending_qa", quality: "untested" },
      translation: { provider: "glossary_guided_llm", status: "in_review", quality: "beta" },
    },
    known_limitations:
      "UI, bilingual STEM explanations, and subtitles available in beta. TTS/STT disabled until Indic pronunciation QA completes.",
  },
  {
    language_code: "te",
    display_name: "Telugu",
    native_name: "తెలుగు",
    script_name: "Telugu",
    rtl: false,
    capability_status: "beta",
    testing_status: "partial",
    availability_status: "limited",
    text_quality_tier: "tier_2_beta",
    translation_status: "beta_review",
    ui_supported: true,
    explanation_supported: true,
    bilingual_supported: true,
    tts_supported: false,
    stt_supported: false,
    voice_provider: null,
    stt_provider: null,
    translation_provider: "glossary_guided_llm",
    pronunciation_tier: null,
    subtitle_supported: true,
    question_supported: false,
    answer_supported: true,
    academic_review_status: "in_review",
    fallback_language_code: "en",
    quality_score_pct: 80.5,
    last_evaluated_at: null,
    provider_matrix: {
      llm: { provider: "gemini/openai", status: "beta", quality: "tier_2" },
      tts: { provider: "unverified", status: "disabled_pending_qa", quality: "untested" },
      stt: { provider: "unverified", status: "disabled_pending_qa", quality: "untested" },
      translation: { provider: "glossary_guided_llm", status: "in_review", quality: "beta" },
    },
    known_limitations:
      "UI, bilingual explanations, and subtitles active in beta. TTS/STT disabled and question banks default to English until academic review finishes.",
  },
  {
    language_code: "mr",
    display_name: "Marathi",
    native_name: "मराठी",
    script_name: "Devanagari",
    rtl: false,
    capability_status: "beta",
    testing_status: "partial",
    availability_status: "limited",
    text_quality_tier: "tier_2_beta",
    translation_status: "beta_review",
    ui_supported: true,
    explanation_supported: true,
    bilingual_supported: true,
    tts_supported: false,
    stt_supported: false,
    voice_provider: null,
    stt_provider: null,
    translation_provider: "glossary_guided_llm",
    pronunciation_tier: null,
    subtitle_supported: true,
    question_supported: false,
    answer_supported: true,
    academic_review_status: "in_review",
    fallback_language_code: "hi",
    quality_score_pct: 83.0,
    last_evaluated_at: null,
    provider_matrix: {
      llm: { provider: "gemini/openai", status: "beta", quality: "tier_2" },
      tts: { provider: "unverified", status: "disabled_pending_qa", quality: "untested" },
      stt: { provider: "unverified", status: "disabled_pending_qa", quality: "untested" },
      translation: { provider: "glossary_guided_llm", status: "in_review", quality: "beta" },
    },
    known_limitations:
      "Shares Devanagari script with Hindi; voice TTS/STT falls back to Hindi/English until native Marathi voice QA passes.",
  },
  {
    language_code: "gu",
    display_name: "Gujarati",
    native_name: "ગુજરાતી",
    script_name: "Gujarati",
    rtl: false,
    capability_status: "beta",
    testing_status: "partial",
    availability_status: "limited",
    text_quality_tier: "tier_2_beta",
    translation_status: "beta_review",
    ui_supported: true,
    explanation_supported: true,
    bilingual_supported: true,
    tts_supported: false,
    stt_supported: false,
    voice_provider: null,
    stt_provider: null,
    translation_provider: "glossary_guided_llm",
    pronunciation_tier: null,
    subtitle_supported: true,
    question_supported: false,
    answer_supported: true,
    academic_review_status: "pending",
    fallback_language_code: "en",
    quality_score_pct: 78.5,
    last_evaluated_at: null,
    provider_matrix: {
      llm: { provider: "gemini/openai", status: "beta", quality: "tier_2" },
      tts: { provider: "unverified", status: "disabled_pending_qa", quality: "untested" },
      stt: { provider: "unverified", status: "disabled_pending_qa", quality: "untested" },
      translation: { provider: "glossary_guided_llm", status: "pending", quality: "beta" },
    },
    known_limitations:
      "UI localization and bilingual explanations in beta; TTS, STT, and translated assessment papers remain disabled pending subject-matter review.",
  },
  {
    language_code: "kn",
    display_name: "Kannada",
    native_name: "ಕನ್ನಡ",
    script_name: "Kannada",
    rtl: false,
    capability_status: "beta",
    testing_status: "partial",
    availability_status: "limited",
    text_quality_tier: "tier_2_beta",
    translation_status: "beta_review",
    ui_supported: true,
    explanation_supported: true,
    bilingual_supported: true,
    tts_supported: false,
    stt_supported: false,
    voice_provider: null,
    stt_provider: null,
    translation_provider: "glossary_guided_llm",
    pronunciation_tier: null,
    subtitle_supported: true,
    question_supported: false,
    answer_supported: true,
    academic_review_status: "pending",
    fallback_language_code: "en",
    quality_score_pct: 79.0,
    last_evaluated_at: null,
    provider_matrix: {
      llm: { provider: "gemini/openai", status: "beta", quality: "tier_2" },
      tts: { provider: "unverified", status: "disabled_pending_qa", quality: "untested" },
      stt: { provider: "unverified", status: "disabled_pending_qa", quality: "untested" },
      translation: { provider: "glossary_guided_llm", status: "pending", quality: "beta" },
    },
    known_limitations:
      "UI chrome, bilingual text, and subtitles in beta. Voice synthesis/recognition and translated exam questions are disabled until verified.",
  },
  {
    language_code: "ml",
    display_name: "Malayalam",
    native_name: "മലയാളം",
    script_name: "Malayalam",
    rtl: false,
    capability_status: "beta",
    testing_status: "partial",
    availability_status: "limited",
    text_quality_tier: "tier_2_beta",
    translation_status: "beta_review",
    ui_supported: true,
    explanation_supported: true,
    bilingual_supported: true,
    tts_supported: false,
    stt_supported: false,
    voice_provider: null,
    stt_provider: null,
    translation_provider: "glossary_guided_llm",
    pronunciation_tier: null,
    subtitle_supported: true,
    question_supported: false,
    answer_supported: true,
    academic_review_status: "pending",
    fallback_language_code: "en",
    quality_score_pct: 77.5,
    last_evaluated_at: null,
    provider_matrix: {
      llm: { provider: "gemini/openai", status: "beta", quality: "tier_2" },
      tts: { provider: "unverified", status: "disabled_pending_qa", quality: "untested" },
      stt: { provider: "unverified", status: "disabled_pending_qa", quality: "untested" },
      translation: { provider: "glossary_guided_llm", status: "pending", quality: "beta" },
    },
    known_limitations:
      "UI localization and bilingual STEM prose in beta; TTS/STT and exam paper translation fall back to English pending native academic evaluation.",
  },
  {
    language_code: "pa",
    display_name: "Punjabi",
    native_name: "ਪੰਜਾਬੀ",
    script_name: "Gurmukhi",
    rtl: false,
    capability_status: "beta",
    testing_status: "partial",
    availability_status: "limited",
    text_quality_tier: "tier_2_beta",
    translation_status: "beta_review",
    ui_supported: true,
    explanation_supported: true,
    bilingual_supported: true,
    tts_supported: false,
    stt_supported: false,
    voice_provider: null,
    stt_provider: null,
    translation_provider: "glossary_guided_llm",
    pronunciation_tier: null,
    subtitle_supported: true,
    question_supported: false,
    answer_supported: true,
    academic_review_status: "pending",
    fallback_language_code: "hi",
    quality_score_pct: 76.0,
    last_evaluated_at: null,
    provider_matrix: {
      llm: { provider: "gemini/openai", status: "beta", quality: "tier_2" },
      tts: { provider: "unverified", status: "disabled_pending_qa", quality: "untested" },
      stt: { provider: "unverified", status: "disabled_pending_qa", quality: "untested" },
      translation: { provider: "glossary_guided_llm", status: "pending", quality: "beta" },
    },
    known_limitations:
      "Gurmukhi UI and bilingual explanations in beta. Voice and formal exam papers fall back to Hindi/English until Gurmukhi STEM review completes.",
  },
  {
    language_code: "ur",
    display_name: "Urdu",
    native_name: "اردو",
    script_name: "Perso-Arabic",
    rtl: true,
    capability_status: "beta",
    testing_status: "partial",
    availability_status: "limited",
    text_quality_tier: "tier_2_beta",
    translation_status: "beta_review",
    ui_supported: true,
    explanation_supported: true,
    bilingual_supported: true,
    tts_supported: false,
    stt_supported: false,
    voice_provider: null,
    stt_provider: null,
    translation_provider: "glossary_guided_llm",
    pronunciation_tier: null,
    subtitle_supported: true,
    question_supported: false,
    answer_supported: true,
    academic_review_status: "pending",
    fallback_language_code: "en",
    quality_score_pct: 78.0,
    last_evaluated_at: null,
    provider_matrix: {
      llm: { provider: "gemini/openai", status: "beta", quality: "tier_2" },
      tts: { provider: "unverified", status: "disabled_pending_qa", quality: "untested" },
      stt: { provider: "unverified", status: "disabled_pending_qa", quality: "untested" },
      translation: { provider: "glossary_guided_llm", status: "pending", quality: "beta" },
    },
    known_limitations:
      "RTL document direction active while mathematical equations stay strictly LTR via KaTeX. TTS/STT disabled until native Urdu STEM pronunciation QA completes.",
  },
  {
    language_code: "or",
    display_name: "Odia",
    native_name: "ଓଡ଼ିଆ",
    script_name: "Odia",
    rtl: false,
    capability_status: "experimental",
    testing_status: "pending",
    availability_status: "limited",
    text_quality_tier: "tier_3_experimental",
    translation_status: "pending",
    ui_supported: false,
    explanation_supported: true,
    bilingual_supported: true,
    tts_supported: false,
    stt_supported: false,
    voice_provider: null,
    stt_provider: null,
    translation_provider: "experimental_llm",
    pronunciation_tier: null,
    subtitle_supported: true,
    question_supported: false,
    answer_supported: false,
    academic_review_status: "pending",
    fallback_language_code: "en",
    quality_score_pct: null,
    last_evaluated_at: null,
    provider_matrix: {
      llm: { provider: "gemini", status: "experimental", quality: "tier_3" },
      tts: { provider: "none", status: "unavailable", quality: "untested" },
      stt: { provider: "none", status: "unavailable", quality: "untested" },
      translation: { provider: "experimental_llm", status: "unreviewed", quality: "experimental" },
    },
    known_limitations:
      "Experimental bilingual text and subtitle preview only. UI chrome, voice, STT, and question/answer workflows fall back to English until native QA passes.",
  },
  {
    language_code: "as",
    display_name: "Assamese",
    native_name: "অসমীয়া",
    script_name: "Bengali",
    rtl: false,
    capability_status: "experimental",
    testing_status: "pending",
    availability_status: "limited",
    text_quality_tier: "tier_3_experimental",
    translation_status: "pending",
    ui_supported: false,
    explanation_supported: true,
    bilingual_supported: true,
    tts_supported: false,
    stt_supported: false,
    voice_provider: null,
    stt_provider: null,
    translation_provider: "experimental_llm",
    pronunciation_tier: null,
    subtitle_supported: true,
    question_supported: false,
    answer_supported: false,
    academic_review_status: "pending",
    fallback_language_code: "bn",
    quality_score_pct: null,
    last_evaluated_at: null,
    provider_matrix: {
      llm: { provider: "gemini", status: "experimental", quality: "tier_3" },
      tts: { provider: "none", status: "unavailable", quality: "untested" },
      stt: { provider: "none", status: "unavailable", quality: "untested" },
      translation: { provider: "experimental_llm", status: "unreviewed", quality: "experimental" },
    },
    known_limitations:
      "Experimental bilingual explanation preview only; not yet benchmarked by native academic reviewers. UI and voice fall back through Bengali/English.",
  },
  {
    language_code: "sa",
    display_name: "Sanskrit",
    native_name: "संस्कृतम्",
    script_name: "Devanagari",
    rtl: false,
    capability_status: "planned",
    testing_status: "pending",
    availability_status: "unavailable",
    text_quality_tier: "tier_3_experimental",
    translation_status: "pending",
    ui_supported: false,
    explanation_supported: false,
    bilingual_supported: true,
    tts_supported: false,
    stt_supported: false,
    voice_provider: null,
    stt_provider: null,
    translation_provider: "planned_academic_review",
    pronunciation_tier: null,
    subtitle_supported: false,
    question_supported: false,
    answer_supported: false,
    academic_review_status: "pending",
    fallback_language_code: "hi",
    quality_score_pct: null,
    last_evaluated_at: null,
    provider_matrix: {
      llm: { provider: "unverified", status: "planned", quality: "untested" },
      tts: { provider: "none", status: "unavailable", quality: "untested" },
      stt: { provider: "none", status: "unavailable", quality: "untested" },
      translation: { provider: "none", status: "planned", quality: "untested" },
    },
    known_limitations:
      "Planned classical/academic track. Modern STEM explanations, UI localization, and voice synthesis are disabled and fall back to Hindi/English until vetted.",
  },
];

export function translateUiKey(
  languageCode: string,
  key: string,
  overrides?: Record<string, string>
): string {
  const code = (languageCode || "en").trim().toLowerCase();
  if (overrides && overrides[key]) return overrides[key];
  const localized = UI_LOCALIZATION_CATALOG[code];
  if (localized && localized[key]) return localized[key];
  return UI_LOCALIZATION_CATALOG.en[key] ?? key;
}

export function computeUiLocalizationCoverage(languageCode: string): {
  coveragePct: number;
  translatedKeys: number;
  totalKeys: number;
  rtl: boolean;
} {
  const code = (languageCode || "en").trim().toLowerCase();
  const baseKeys = Object.keys(UI_LOCALIZATION_CATALOG.en);
  const localized = UI_LOCALIZATION_CATALOG[code] ?? {};
  const translatedKeys = baseKeys.filter((k) => Boolean(localized[k]?.trim())).length;
  const cap = FALLBACK_LANGUAGE_REGISTRY.find((c) => c.language_code === code);
  return {
    coveragePct: Math.round((translatedKeys / Math.max(1, baseKeys.length)) * 1000) / 10,
    translatedKeys,
    totalKeys: baseKeys.length,
    rtl: Boolean(cap?.rtl),
  };
}

export function isModalitySupportedOnCapability(
  cap: LanguageCapabilityOut,
  modality: LanguageModalityKey
): boolean {
  switch (modality) {
    case "ui":
      return Boolean(cap.ui_supported);
    case "explanation":
      return cap.explanation_supported !== false;
    case "voice":
      return Boolean(cap.tts_supported);
    case "subtitle":
      return Boolean(cap.subtitle_supported);
    case "question":
      return Boolean(cap.question_supported);
    case "answer":
      return Boolean(cap.answer_supported);
  }
}

export function resolveModalityFallbackClient(
  requestedCode: string,
  modality: LanguageModalityKey,
  registry: LanguageCapabilityOut[]
): ModalityResolutionOut {
  const req = (requestedCode || "en").trim().toLowerCase();
  const byCode = new Map(registry.map((c) => [c.language_code, c]));
  const reqCap = byCode.get(req);
  const enCap = byCode.get("en");

  if (!reqCap) {
    return {
      modality,
      requested_language: req,
      effective_language: "en",
      fallback_applied: true,
      fallback_reason: `Language '${req}' is not registered; falling back to English (en).`,
      capability_status: enCap?.capability_status ?? "production",
      availability_status: enCap?.availability_status ?? "available",
      testing_status: enCap?.testing_status ?? "passed",
      rtl: false,
      provider: null,
    };
  }

  if (isModalitySupportedOnCapability(reqCap, modality)) {
    return {
      modality,
      requested_language: req,
      effective_language: req,
      fallback_applied: false,
      fallback_reason: null,
      capability_status: reqCap.capability_status ?? "beta",
      availability_status: reqCap.availability_status ?? "limited",
      testing_status: reqCap.testing_status ?? "pending",
      rtl: reqCap.rtl,
      provider:
        modality === "voice"
          ? reqCap.voice_provider
          : modality === "answer"
            ? reqCap.stt_provider ?? reqCap.translation_provider ?? null
            : reqCap.translation_provider ?? null,
    };
  }

  const visited = new Set<string>([req]);
  let candidateCode = (reqCap.fallback_language_code || "en").toLowerCase();
  let chosen: LanguageCapabilityOut | undefined;
  while (candidateCode && !visited.has(candidateCode)) {
    visited.add(candidateCode);
    const cand = byCode.get(candidateCode);
    if (cand && isModalitySupportedOnCapability(cand, modality)) {
      chosen = cand;
      break;
    }
    candidateCode = (cand?.fallback_language_code || "en").toLowerCase();
  }
  const effective = chosen ?? enCap ?? reqCap;

  const labels: Record<LanguageModalityKey, string> = {
    ui: "UI localization",
    explanation: "AI explanation",
    voice: "Voice TTS narration",
    subtitle: "Subtitles",
    question: "Question bank translation",
    answer: "Answer input",
  };
  let reason = `${labels[modality]} is not yet verified for ${reqCap.display_name} (${req}); falling back to ${effective.display_name} (${effective.language_code}).`;
  if (modality === "voice" && reqCap.subtitle_supported) {
    reason += ` Synchronized ${reqCap.display_name} subtitles remain active.`;
  }

  return {
    modality,
    requested_language: req,
    effective_language: effective.language_code,
    fallback_applied: true,
    fallback_reason: reason,
    capability_status: effective.capability_status ?? "production",
    availability_status: effective.availability_status ?? "available",
    testing_status: effective.testing_status ?? "passed",
    rtl: effective.rtl,
    provider:
      modality === "voice"
        ? effective.voice_provider
        : effective.translation_provider ?? null,
  };
}

export function verifyClientNotationPreservation(
  sourceText: string,
  targetText: string
): NotationPreservationOut {
  const mathRegex = /(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)/g;
  const sciRegex = /\b\d+(?:\.\d+)?\s*(?:[×x*]\s*10\^\{?[+-]?\d+\}?|[eE][+-]?\d+)\b/g;
  const siRegex =
    /\b\d+(?:\.\d+)?\s*(?:m\/s\^2|m\/s²|m\/s|km\/h|kJ\/mol|mol\^?-?1|Hz|Pa|Ω|μF|kV|mol)\b/g;
  const chemRegex = /\b(?:[A-Z][a-z]?\d*){2,}\b/g;

  const mathExpressions = Array.from(new Set(sourceText.match(mathRegex) ?? []));
  const withoutMath = sourceText.replace(mathRegex, " ");
  const scientificNotations = Array.from(new Set(withoutMath.match(sciRegex) ?? []));
  const siUnitValues = Array.from(new Set(withoutMath.match(siRegex) ?? []));
  const chemicalFormulas = Array.from(
    new Set(
      (withoutMath.match(chemRegex) ?? []).filter(
        (tok) =>
          /\d/.test(tok) ||
          ["NaCl", "HCl", "NaOH", "KOH", "CuO", "MgO"].includes(tok)
      )
    )
  );

  const compactTarget = targetText.replace(/\s+/g, "");
  const hasToken = (tok: string) =>
    targetText.includes(tok) || compactTarget.includes(tok.replace(/\s+/g, ""));

  const missingMath = mathExpressions.filter((m) => !hasToken(m));
  const sciAll = [...scientificNotations, ...siUnitValues, ...chemicalFormulas];
  const missingScience = sciAll.filter((s) => !hasToken(s));

  const mathScore =
    mathExpressions.length === 0
      ? 100
      : Math.round(((mathExpressions.length - missingMath.length) / mathExpressions.length) * 10000) /
        100;
  const sciScore =
    sciAll.length === 0
      ? 100
      : Math.round(((sciAll.length - missingScience.length) / sciAll.length) * 10000) /
        100;

  return {
    math_preserved: missingMath.length === 0,
    science_preserved: missingScience.length === 0,
    all_preserved: missingMath.length === 0 && missingScience.length === 0,
    math_preservation_score: mathScore,
    science_notation_score: sciScore,
    math_expressions: mathExpressions,
    scientific_notations: scientificNotations,
    si_unit_values: siUnitValues,
    chemical_formulas: chemicalFormulas,
    missing_math: missingMath,
    missing_science: missingScience,
  };
}

export function getCapabilityStatusMeta(status: string | undefined): {
  label: string;
  tone: BadgeTone;
} {
  switch (status) {
    case "production":
      return { label: "Production", tone: "healthy" };
    case "beta":
      return { label: "Beta", tone: "degraded" };
    case "experimental":
      return { label: "Experimental", tone: "degraded" };
    case "planned":
      return { label: "Planned", tone: "neutral" };
    default:
      return { label: status || "Unverified", tone: "neutral" };
  }
}

export function getTestingStatusMeta(status: string | undefined): {
  label: string;
  tone: BadgeTone;
} {
  switch (status) {
    case "passed":
      return { label: "QA Passed", tone: "healthy" };
    case "partial":
      return { label: "Partial QA", tone: "degraded" };
    case "failed":
      return { label: "QA Failed", tone: "degraded" };
    default:
      return { label: "Pending QA", tone: "neutral" };
  }
}

export function formatBilingualModeLabel(mode: BilingualMode | string): string {
  switch (mode) {
    case "monolingual":
      return "Monolingual (Target Script Only)";
    case "side_by_side":
      return "Side-by-Side (Target + English Reference)";
    default:
      return "Bilingual STEM (Localized Prose + English Terms)";
  }
}
