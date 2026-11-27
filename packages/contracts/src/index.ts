/**
 * Canonical cross-app TypeScript contracts for Go4Guru (Phase 0 + Phase 1).
 */

export type UserRole =
  | "student"
  | "parent"
  | "teacher"
  | "mentor"
  | "school_admin"
  | "content_admin"
  | "academic_reviewer"
  | "platform_admin";

export interface ErrorDetail {
  code: string;
  message: string;
  details: unknown;
  request_id: string;
}

export interface ErrorEnvelope {
  error: ErrorDetail;
}

export interface DependencyStatus {
  status: "up" | "down";
  error: string | null;
}

export interface ReadinessResponse {
  status: "ready" | "degraded";
  service: string;
  version: string;
  environment: string;
  phase: string;
  checks: Record<string, DependencyStatus>;
  timestamp: string;
}

export interface ModuleBoundaryInfo {
  name: string;
  status: string;
  planned_phase: string;
}

export interface ApiMetaResponse {
  service: string;
  version: string;
  environment: string;
  api_prefix: string;
  ws_prefix: string;
  phase: string;
  modules: ModuleBoundaryInfo[];
}

export interface UserSummary {
  id: string;
  email: string;
  display_name: string;
  roles: string[];
  permissions: string[];
  is_minor: boolean;
  mfa_enabled: boolean;
  mfa_verified: boolean;
  status: string;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in_seconds: number;
  mfa_required: boolean;
  mfa_verified: boolean;
  user: UserSummary;
}

export interface MfaSetupResponse {
  secret: string;
  provisioning_uri: string;
}

export interface UserProfileResponse {
  id: string;
  email: string;
  status: string;
  is_minor: boolean;
  mfa_enabled: boolean;
  roles: string[];
  permissions: string[];
  display_name: string;
  avatar_url: string | null;
  timezone: string;
  ui_language: string;
  preferred_explanation_language: string;
  preferred_voice_language: string;
  preferred_subtitle_language: string;
  preferred_question_language: string;
  preferred_answer_language: string;
}

export interface StudentProfileResponse {
  user_id: string;
  board_id: string | null;
  academic_session_id: string | null;
  grade_id: string | null;
  curriculum_version_id: string | null;
  primary_exam_target: string;
  daily_study_minutes_target: number;
  onboarding_completed_at: string | null;
}

export interface BoardOut {
  id: string;
  code: string;
  name: string;
  country: string;
}

export interface AcademicSessionOut {
  id: string;
  code: string;
  starts_on: string;
  ends_on: string;
  is_active: boolean;
}

export interface GradeOut {
  id: string;
  number: number;
  label: string;
}

export interface SubjectOut {
  id: string;
  code: string;
  name: string;
  discipline: string;
}

export interface CurriculumVersionOut {
  id: string;
  board_id: string;
  academic_session_id: string;
  version_tag: string;
  status: string;
  published_at: string | null;
}

export interface LearningObjectiveNode {
  id: string;
  bloom_level: string;
  statement: string;
}

export interface ConceptNode {
  id: string;
  code: string;
  title: string;
  difficulty_baseline: number;
  skill_tags: string[];
  exam_tags: string[];
  learning_objectives: LearningObjectiveNode[];
}

export interface TopicNode {
  id: string;
  section_id: string | null;
  sequence_no: number;
  title: string;
  concepts: ConceptNode[];
}

export interface ChapterNode {
  id: string;
  sequence_no: number;
  code: string;
  title: string;
  summary: string | null;
  topics: TopicNode[];
}

export interface BookNode {
  id: string;
  grade_id: string;
  grade_label: string;
  subject_id: string;
  subject_name: string;
  title: string;
  publisher: string;
  official_source_url: string | null;
  edition_year: number | null;
  chapters: ChapterNode[];
}

export interface CurriculumTreeResponse {
  version: CurriculumVersionOut;
  board: BoardOut;
  academic_session: AcademicSessionOut;
  books: BookNode[];
}

export interface ContentSourceResponse {
  id: string;
  name: string;
  owner_name: string;
  source_category: string;
  official_url: string | null;
}

export interface ContentLicenseResponse {
  id: string;
  source_id: string;
  license_name: string;
  hosting_allowed: boolean;
  embedding_allowed: boolean;
  legal_review_status: string;
}

export interface OptionOut {
  option_key: string;
  content_markdown: string;
  is_correct: boolean | null;
}

export interface ProvenanceOut {
  source_id: string;
  license_id: string;
  source_type: string;
  is_pyq: boolean;
  exam_name: string | null;
  exam_year: number | null;
  verification_status: string;
}

export interface QuestionOut {
  id: string;
  version_id: string;
  version_no: number;
  status: string;
  question_type: string;
  language_code: string;
  grade_id: string;
  subject_id: string;
  chapter_id: string;
  topic_id: string | null;
  concept_id: string | null;
  stem_markdown: string;
  difficulty: string;
  default_marks: number;
  ai_generated: boolean;
  options: OptionOut[];
  hints_available_count: number;
  provenance: ProvenanceOut | null;
  correct_answer_jsonb: Record<string, unknown> | null;
}

export interface QuestionSearchResponse {
  items: QuestionOut[];
  total: number;
  limit: number;
  offset: number;
}

export interface DetectedSheetInfo {
  sheet_name: string;
  row_count: number;
  headers: string[];
  sample_rows: Record<string, unknown>[];
}

export interface ImportBatchOut {
  id: string;
  original_filename: string;
  file_format: string;
  file_sha256: string;
  status: string;
  selected_sheet: string | null;
  detected_sheets: DetectedSheetInfo[];
  column_mapping: Record<string, unknown>;
  total_rows: number;
  valid_rows: number;
  warning_rows: number;
  error_rows: number;
  duplicate_rows: number;
  duplicate_file_warning: string | null;
}

export interface StagingRowOut {
  id: string;
  sheet_name: string;
  row_number: number;
  validation_status: string;
  raw_payload: Record<string, unknown>;
  errors: string[];
  warnings: string[];
  created_question_id: string | null;
}

export interface ImportPreviewResponse {
  batch: ImportBatchOut;
  rows: StagingRowOut[];
}

export interface PracticeQuestionView {
  question_id: string;
  question_version_id: string;
  question_type: string;
  stem_markdown: string;
  difficulty: string;
  default_marks: number;
  options: { option_key: string; content_markdown: string }[];
}

export interface AttemptResultOut {
  id: string;
  question_id: string;
  question_version_id: string;
  is_correct: boolean;
  score_awarded: number;
  hints_used_count: number;
  time_spent_seconds: number;
  attempted_at: string;
  correct_answer_jsonb: Record<string, unknown> | null;
  explanation_markdown: string | null;
  steps: string[];
  common_mistakes_markdown: string | null;
}

export interface PracticeSessionOut {
  id: string;
  mode: string;
  subject_id: string | null;
  chapter_id: string | null;
  started_at: string;
  questions: PracticeQuestionView[];
  attempts: AttemptResultOut[];
  hints_revealed: Record<string, { hint_level: number; hint_markdown: string }[]>;
}

export interface StudentNoteOut {
  id: string;
  concept_id: string | null;
  question_id: string | null;
  title: string;
  body_markdown: string;
  created_at: string;
  updated_at: string;
}

export interface BookmarkOut {
  question_id: string;
  folder_name: string;
  created_at: string;
}

export interface StudentDashboardResponse {
  onboarding_completed: boolean;
  primary_exam_target: string;
  daily_study_minutes_target: number;
  total_attempts: number;
  correct_attempts: number;
  accuracy_pct: number;
  total_practice_sessions: number;
  hints_used_total: number;
  saved_questions_count: number;
  notes_count: number;
  subject_activity: {
    subject_id: string | null;
    subject_name: string;
    practice_sessions_count: number;
  }[];
  recent_attempts: {
    attempt_id: string;
    question_id: string;
    is_correct: boolean;
    score_awarded: number;
    hints_used_count: number;
    attempted_at: string;
  }[];
  unimplemented_features_note: string;
}

export interface ScoringRuleContract {
  mode: "standard" | "partial_subset" | "jee_adv_partial";
  correct_marks: number;
  wrong_marks: number;
  unanswered_marks: number;
  partial_credit_per_correct_option: number;
}

export interface ExamSectionRuleContract {
  code: string;
  name: string;
  question_count: number;
  attempt_limit: number | null;
  allowed_question_types: string[];
  difficulty_distribution: Record<string, number>;
  question_type_distribution: Record<string, number>;
  scoring: ScoringRuleContract;
}

export interface ExamPatternRulesContract {
  duration_seconds: number | null;
  grace_seconds: number;
  shuffle_questions: boolean;
  shuffle_options: boolean;
  retake_policy: {
    max_attempts: number | null;
    cooldown_minutes: number;
  };
  sections: ExamSectionRuleContract[];
}

export interface ExamPatternOut {
  id: string;
  exam_track_id: string;
  exam_track_code: string;
  exam_track_name: string;
  version_label: string;
  effective_year: number;
  is_active: boolean;
  rules: ExamPatternRulesContract;
}

export interface QuizOut {
  id: string;
  quiz_type: string;
  title: string;
  status: string;
  question_count: number;
  duration_seconds: number | null;
  shuffle_questions: boolean;
  is_ai_generated: boolean;
  created_at: string;
}

export interface TestSectionOut {
  id: string;
  sequence_no: number;
  name: string;
  attempt_limit: number | null;
  question_count: number;
  marking_rule: ScoringRuleContract;
}

export interface TestOut {
  id: string;
  title: string;
  description: string | null;
  test_category: string;
  exam_pattern_id: string | null;
  duration_seconds: number | null;
  grace_seconds: number;
  total_marks: number;
  status: string;
  sections: TestSectionOut[];
  created_at: string;
}

export interface AttemptQuestionStateItem {
  sequence_no: number;
  section_id: string | null;
  section_name: string | null;
  question_id: string;
  question_version_id: string;
  question_type: string;
  stem_markdown: string;
  difficulty: string;
  marks: number;
  negative_marks: number;
  options: { option_key: string; content_markdown: string }[];
  response_jsonb: Record<string, unknown>;
  is_visited: boolean;
  is_marked_for_review: boolean;
  time_spent_seconds: number;
}

export interface AttemptStateResponse {
  attempt_id: string;
  title: string;
  source_kind: "quiz" | "test";
  status: string;
  started_at: string;
  expires_at: string | null;
  grace_until: string | null;
  server_now_utc: string;
  remaining_seconds: number | null;
  questions: AttemptQuestionStateItem[];
}

export interface AutosaveResponse {
  attempt_id: string;
  saved_count: number;
  server_now_utc: string;
  remaining_seconds: number | null;
}

export interface SectionScoreSummary {
  section_id: string | null;
  section_name: string;
  total_questions: number;
  attempted: number;
  correct: number;
  wrong: number;
  raw_score: number;
  max_score: number;
}

export interface AttemptResultQuestionItem {
  sequence_no: number;
  section_name: string | null;
  question_id: string;
  question_version_id: string;
  question_type: string;
  stem_markdown: string;
  options: { option_key: string; content_markdown: string }[];
  student_response_jsonb: Record<string, unknown>;
  correct_answer_jsonb: Record<string, unknown>;
  is_visited: boolean;
  is_marked_for_review: boolean;
  time_spent_seconds: number;
  is_correct: boolean;
  marks_awarded: number;
  explanation_markdown: string | null;
  steps: string[];
  common_mistakes_markdown: string | null;
}

export interface AttemptResultResponse {
  attempt_id: string;
  title: string;
  source_kind: "quiz" | "test";
  status: string;
  raw_score: number;
  max_score: number;
  accuracy_pct: number;
  correct_count: number;
  wrong_count: number;
  unanswered_count: number;
  started_at: string;
  submitted_at: string | null;
  section_breakdown: SectionScoreSummary[];
  items: AttemptResultQuestionItem[];
}

export interface AttemptHistoryItem {
  attempt_id: string;
  title: string;
  source_kind: "quiz" | "test";
  status: string;
  raw_score: number | null;
  max_score: number | null;
  accuracy_pct: number | null;
  started_at: string;
  submitted_at: string | null;
}

export interface LearningEventOut {
  id: string;
  event_type: string;
  concept_id: string | null;
  entity_id: string | null;
  metrics_jsonb: Record<string, unknown>;
  occurred_at: string;
}

export interface StudentAnalyticsOverviewResponse {
  assessments_completed: number;
  average_assessment_accuracy_pct: number;
  practice_attempts: number;
  practice_correct: number;
  practice_accuracy_pct: number;
  total_learning_events: number;
  recent_events: LearningEventOut[];
}

export interface CohortAnalyticsResponse {
  total_submitted_attempts: number;
  average_accuracy_pct: number;
}

// --- Phase 3: Modular AI Tutor, Hybrid RAG, Verification & Evals ---

export type TeachingMode =
  | "explain"
  | "hint"
  | "socratic"
  | "step_by_step"
  | "practice"
  | "exam_prep"
  | "revision";

export interface CitedChunkOut {
  chunk_id: string;
  document_id: string;
  hierarchy_path: string;
  section_title: string | null;
  language_code: string;
  excerpt: string;
  source_attribution: string | null;
  score: number;
}

export interface PracticeDraftOut {
  question_type: string;
  stem_markdown: string;
  options: { option_key: string; content_markdown: string; is_correct: boolean }[];
  hint_markdown: string | null;
  is_ai_generated: boolean;
  is_pyq: boolean;
  verification_status: string;
}

export interface AiCurriculumContextOut {
  board_code: string | null;
  grade_number: number | null;
  subject_id: string | null;
  subject_name: string | null;
  discipline: string | null;
  chapter_id: string | null;
  chapter_title: string | null;
  topic_id: string | null;
  topic_title: string | null;
  concept_id: string | null;
  concept_title: string | null;
  learning_objectives: string[];
  prerequisites: string[];
}

export interface AiSessionOut {
  id: string;
  session_type: string;
  title: string;
  teaching_mode: TeachingMode;
  language_code: string;
  curriculum_context: AiCurriculumContextOut;
  context_summary: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface AiMessageOut {
  id: string;
  role: string;
  content_markdown: string;
  intent: string | null;
  pedagogical_mode: string | null;
  spoiler_guard: boolean;
  citations: CitedChunkOut[];
  follow_up_questions: string[];
  generated_practice: PracticeDraftOut[];
  verification_status: string;
  verification_summary: Record<string, unknown>;
  provider_used: string | null;
  model_used: string | null;
  prompt_version: string | null;
  is_fallback: boolean;
  safety_verdict: string;
  tokens_in: number;
  tokens_out: number;
  latency_ms: number;
  created_at: string;
}

export interface AiTurnResponse {
  session_id: string;
  student_message: AiMessageOut;
  assistant_message: AiMessageOut;
}

export interface ModelCapabilityOut {
  provider: string;
  configured: boolean;
  fast_model: string;
  reasoning_model: string;
  circuit_state: string;
  notes: string;
}

export interface AiModelsCatalogResponse {
  primary_provider: string;
  providers: ModelCapabilityOut[];
  daily_turn_limit: number;
  rpm_limit: number;
  supported_languages: string[];
  known_limitations: string[];
}

export interface AiUsageQuotaResponse {
  turns_used_today: number;
  daily_turn_limit: number;
  turns_remaining_today: number;
  estimated_cost_usd_today: number;
  rpm_limit: number;
}

export interface AiReviewQueueOut {
  id: string;
  ai_session_id: string;
  ai_message_id: string;
  reason: string;
  status: string;
  reviewer_notes: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export interface AiEvalRunResponse {
  id: string;
  dataset_name: string;
  dataset_version: string;
  provider: string;
  model_id: string;
  prompt_version: string;
  total_items: number;
  passed_items: number;
  pass_rate_pct: number;
  metrics: Record<string, unknown>;
  created_at: string;
}

export interface AiCostSummaryResponse {
  total_events: number;
  total_tokens_in: number;
  total_tokens_out: number;
  total_estimated_cost_usd: number;
  fallback_count: number;
}

// ------------------------------------------------------------------
// Phase 4: Live AI Classroom, Schema-Driven Whiteboard & Voice
// ------------------------------------------------------------------
export type ClassroomState =
  | "IDLE"
  | "READY"
  | "PLAYING_SEGMENT"
  | "PAUSED"
  | "CHECKPOINT_WAIT"
  | "DOUBT_INTERRUPTION"
  | "COMPLETED";

export interface ClassroomWhiteboardAction {
  id: string;
  opcode:
    | "WRITE_TEXT"
    | "INSERT_FORMULA"
    | "DRAW_LINE"
    | "DRAW_ARROW"
    | "DRAW_SHAPE"
    | "DRAW_GRAPH"
    | "DRAW_DIAGRAM"
    | "INSERT_IMAGE"
    | "HIGHLIGHT"
    | "ERASE"
    | "MOVE"
    | "TRANSFORM";
  sequence: number;
  at_ms: number;
  aria_summary: string;
  payload: Record<string, unknown>;
}

export type CapabilityStatus = "production" | "beta" | "experimental" | "planned";
export type TestingStatus = "passed" | "partial" | "pending" | "failed";
export type AvailabilityStatus =
  | "available"
  | "limited"
  | "provider_key_required"
  | "unavailable";
export type BilingualMode = "monolingual" | "bilingual_stem_en" | "side_by_side";

export interface ProviderModalityCapability {
  provider: string;
  status: string;
  quality: string;
}

export interface LanguageCapabilityOut {
  language_code: string;
  display_name: string;
  native_name: string;
  script_name?: string;
  rtl: boolean;
  capability_status?: CapabilityStatus | string;
  testing_status?: TestingStatus | string;
  availability_status?: AvailabilityStatus | string;
  text_quality_tier: string;
  translation_status: string;
  ui_supported?: boolean;
  explanation_supported?: boolean;
  bilingual_supported?: boolean;
  tts_supported: boolean;
  stt_supported: boolean;
  voice_provider: string | null;
  stt_provider?: string | null;
  translation_provider?: string | null;
  pronunciation_tier: string | null;
  subtitle_supported: boolean;
  question_supported?: boolean;
  answer_supported?: boolean;
  academic_review_status: string;
  fallback_language_code?: string;
  quality_score_pct?: number | null;
  last_evaluated_at?: string | null;
  provider_matrix?: Record<string, ProviderModalityCapability>;
  known_limitations: string | null;
}

export interface SubtitleCue {
  start_ms: number;
  end_ms: number;
  text: string;
}

export interface CheckpointOption {
  key: string;
  text: string;
}

export interface CheckpointSpec {
  question_type: "mcq_single" | "numerical";
  prompt: string;
  options: CheckpointOption[];
  correct_key: string | null;
  expected_value: number | null;
  remediation_hint: string;
}

export interface LessonSegment {
  sequence: number;
  type: "concept_explanation" | "worked_example" | "checkpoint_question" | "summary";
  title: string;
  narration: string;
  subtitle_cues: SubtitleCue[];
  canvas_actions: ClassroomWhiteboardAction[];
  checkpoint: CheckpointSpec | null;
  duration_ms: number;
}

export interface LessonArtifact {
  schema_version: string;
  title: string;
  curriculum_context: Record<string, unknown>;
  language: string;
  voice_language: string;
  subtitle_language: string;
  objectives: string[];
  segments: LessonSegment[];
}

export interface LessonPlanOut {
  id: string;
  title: string;
  language_code: string;
  voice_language: string;
  subtitle_language: string;
  schema_version: string;
  artifact: LessonArtifact;
  created_at: string;
}

export interface TTSResponseOut {
  audio_available: boolean;
  audio_url: string | null;
  cache_key: string | null;
  normalized_speakable_text: string;
  provider: string;
  voice_id: string;
  language_code: string;
  characters_count: number;
  estimated_duration_ms: number;
  cache_hit: boolean;
  is_fallback: boolean;
  fallback_mode: string | null;
  limitation_notice: string | null;
}

export interface ClassroomSessionSummaryOut {
  id: string;
  lesson_plan_id: string;
  title: string;
  state: ClassroomState;
  current_segment_seq: number;
  total_segments: number;
  playback_speed: number;
  voice_language: string;
  subtitle_language: string;
  started_at: string;
  last_active_at: string;
  completed_at: string | null;
}

export interface ClassroomSessionDetailOut {
  id: string;
  lesson_plan_id: string;
  state: ClassroomState;
  current_segment_seq: number;
  playback_position_ms: number;
  playback_speed: number;
  voice_language: string;
  subtitle_language: string;
  checkpoint_results: Record<string, { passed: boolean; answered_at: string }>;
  lesson_artifact: LessonArtifact;
  active_whiteboard_actions: ClassroomWhiteboardAction[];
  can_undo: boolean;
  can_redo: boolean;
  tts_preview: TTSResponseOut | null;
  started_at: string;
  last_active_at: string;
  completed_at: string | null;
}

export interface CheckpointSubmitResponse {
  passed: boolean;
  feedback: string;
  session: ClassroomSessionDetailOut;
}

export interface DoubtInterruptResponse {
  answer_markdown: string;
  verification_status: string;
  safety_verdict: string;
  overlay_actions: ClassroomWhiteboardAction[];
  session: ClassroomSessionDetailOut;
}

export interface WhiteboardEventOut {
  id: string;
  segment_seq: number;
  sequence_no: number;
  actor: string;
  action_type: string;
  action: ClassroomWhiteboardAction;
  is_undone: boolean;
  created_at: string;
}

export interface WhiteboardSnapshotOut {
  id: string;
  segment_seq: number;
  version: number;
  actions: ClassroomWhiteboardAction[];
  created_at: string;
}

// ------------------------------------------------------------------
// Phase 5: Adaptive Concept Mastery, Flashcards, Study Plans & Notifications
// ------------------------------------------------------------------
export type MasteryBand = "novice" | "developing" | "proficient" | "mastered";

export interface ConceptMasteryOut {
  concept_id: string;
  concept_code: string;
  concept_title: string;
  subject_name: string | null;
  chapter_title: string | null;
  mastery_score: number;
  confidence: number;
  retention_score: number;
  independent_solve_ratio: number;
  transfer_score: number;
  improvement_slope: number;
  difficulty_weighted_accuracy: number;
  band: MasteryBand;
  attempts_count: number;
  last_practiced_at: string | null;
  next_review_due_at: string | null;
  breakdown: Record<string, unknown>;
  evidence_summary: Record<string, unknown>;
}

export interface MisconceptionOut {
  id: string;
  concept_id: string;
  concept_title: string;
  question_id: string | null;
  misconception_code: string;
  title: string;
  description: string;
  severity: string;
  occurrence_count: number;
  last_observed_at: string;
  resolved_at: string | null;
}

export interface RecommendationItemOut {
  concept_id: string;
  concept_title: string;
  item_type: string;
  priority_score: number;
  reason: string;
  action_route: string;
}

export interface LearningPathItemOut {
  id: string;
  concept_id: string;
  concept_title: string;
  item_type: string;
  sequence_no: number;
  priority_score: number;
  reason: string;
  status: string;
  completed_at: string | null;
}

export interface LearningPathOut {
  id: string;
  title: string;
  goal_exam_track: string | null;
  status: string;
  items: LearningPathItemOut[];
  created_at: string;
}

export interface AdaptiveOverviewOut {
  concepts: ConceptMasteryOut[];
  weak_concepts: ConceptMasteryOut[];
  mastered_concepts: ConceptMasteryOut[];
  unresolved_misconceptions: MisconceptionOut[];
  recommendations: RecommendationItemOut[];
  algorithm_version: string;
  limitations_note: string;
}

export type FlashcardType = "concept" | "formula" | "vocabulary" | "missed_question";

export interface FlashcardOut {
  id: string;
  card_type: FlashcardType;
  concept_id: string | null;
  concept_title: string | null;
  subject_id: string | null;
  source_question_id: string | null;
  language_code: string;
  front_markdown: string;
  back_markdown: string;
  hint_markdown: string | null;
  tags: string[];
  due_at: string;
  interval_days: number;
  ease_factor: number;
  repetitions: number;
  lapse_count: number;
  last_quality: number | null;
  last_reviewed_at: string | null;
  priority_score: number;
  is_due: boolean;
}

export interface FlashcardReviewResponse {
  flashcard: FlashcardOut;
  previous_interval_days: number;
  new_interval_days: number;
  previous_ease: number;
  new_ease: number;
}

export interface SyncMissedResponse {
  created_count: number;
  existing_count: number;
  flashcards: FlashcardOut[];
}

export interface StudyPlanItemOut {
  id: string;
  concept_id: string | null;
  flashcard_id: string | null;
  item_type: string;
  title: string;
  description: string;
  estimated_minutes: number;
  priority_score: number;
  scheduled_for: string;
  status: string;
  completed_at: string | null;
}

export interface StudyPlanOut {
  id: string;
  title: string;
  target_date: string | null;
  daily_minutes_budget: number;
  status: string;
  items: StudyPlanItemOut[];
  created_at: string;
}

export interface RevisionAnalyticsOut {
  total_flashcards: number;
  due_now_count: number;
  mastered_cards_count: number;
  lapsed_cards_count: number;
  missed_question_cards_count: number;
  total_reviews: number;
  average_quality: number;
  retention_success_rate_pct: number;
  active_plan_completion_pct: number;
  by_card_type: Record<string, number>;
}

export interface NotificationOut {
  id: string;
  notification_type: string;
  title: string;
  body: string;
  action_url: string | null;
  is_read: boolean;
  read_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

// ------------------------------------------------------------------
// Phase 6: Homework AI (Uploads, OCR, Subject-Aware Evaluation, Hints & Retries)
// ------------------------------------------------------------------
export type HomeworkSubjectArea =
  | "mathematics"
  | "physics"
  | "chemistry"
  | "english"
  | "social_science";

export type HomeworkSubjectSelection = "auto" | HomeworkSubjectArea;

export type HomeworkSubmissionStatus =
  | "uploaded"
  | "ocr_processing"
  | "needs_review"
  | "analyzing"
  | "feedback_ready"
  | "retry_pending"
  | "completed"
  | "failed";

export type HomeworkEvaluationOverallStatus =
  | "correct"
  | "partially_correct"
  | "needs_correction"
  | "unreadable_or_uncertain";

export type HomeworkConfidenceBand = "high" | "medium" | "low" | "uncertain";

export interface HomeworkFileOut {
  id: string;
  page_no: number;
  original_filename: string;
  mime_type: string;
  detected_format: string;
  size_bytes: number;
  sha256: string;
  exif_stripped: boolean;
  pdf_page_count: number | null;
  scan_status: string;
  download_url: string;
  created_at: string;
}

export interface HomeworkOcrPageOut {
  id: string;
  page_no: number;
  ocr_provider: string;
  extracted_text: string;
  extracted_latex: string | null;
  handwriting_detected: boolean;
  handwriting_supported: boolean;
  confidence: number;
  needs_review: boolean;
  student_corrected_text: string | null;
  effective_text: string;
  warnings: string[];
}

export interface HomeworkExtractedStepOut {
  step_no: number;
  content: string;
  expression: string | null;
}

export interface HomeworkStepEvaluationOut {
  step_no: number;
  student_work: string;
  status: "correct" | "partially_correct" | "incorrect" | "missing" | "uncertain";
  explanation: string;
  error_categories: string[];
  verifier_note: string | null;
}

export interface HomeworkErrorClassificationOut {
  subject_area: HomeworkSubjectArea;
  category: string;
  severity: "low" | "medium" | "high";
  step_no: number | null;
  summary: string;
  guidance: string;
}

export interface HomeworkGraduatedHintOut {
  level: 1 | 2 | 3;
  stage: "conceptual_nudge" | "method_scaffold" | "targeted_correction";
  title: string;
  content_markdown: string;
  spoiler_checked: boolean;
}

export interface HomeworkRevisionRecommendationOut {
  topic_title: string;
  reason: string;
  recommended_action:
    | "review_flashcards"
    | "guided_practice"
    | "adaptive_remediation"
    | "tutor_socratic_drill";
  action_route: string;
  priority: "high" | "medium" | "low";
  error_categories: string[];
}

export interface HomeworkFeedbackValidationReportOut {
  passed: boolean;
  spoiler_guard_passed: boolean;
  taxonomy_valid: boolean;
  verifier_agreement: "verified" | "partial" | "discrepancy" | "not_applicable";
  safety_passed: boolean;
  confidence_adjusted: boolean;
  issues: string[];
}

export interface HomeworkEvaluationOut {
  id: string;
  attempt_no: number;
  subject_area: HomeworkSubjectArea;
  detected_question: string;
  student_work_summary: string;
  extracted_steps: HomeworkExtractedStepOut[];
  step_evaluations: HomeworkStepEvaluationOut[];
  error_classifications: HomeworkErrorClassificationOut[];
  overall_status: HomeworkEvaluationOverallStatus;
  feedback_summary: string;
  strengths: string[];
  unlocked_hints: HomeworkGraduatedHintOut[];
  current_hint_level_unlocked: number;
  max_hint_level: number;
  has_more_hints: boolean;
  solution_revealed: boolean;
  complete_solution_markdown: string | null;
  verifier_results: Record<string, unknown>;
  validation_report: HomeworkFeedbackValidationReportOut;
  revision_recommendations: HomeworkRevisionRecommendationOut[];
  confidence: number;
  confidence_band: HomeworkConfidenceBand;
  provider_used: string;
  model_id: string;
  is_fallback: boolean;
  safety_verdict: string;
  created_at: string;
}

export interface HomeworkSubmissionSummaryOut {
  id: string;
  title: string;
  selected_subject: HomeworkSubjectSelection;
  detected_subject: HomeworkSubjectArea | null;
  subject_confidence: number | null;
  language_code: string;
  status: HomeworkSubmissionStatus;
  page_count: number;
  retry_count: number;
  needs_ocr_review: boolean;
  latest_overall_status: HomeworkEvaluationOverallStatus | null;
  latest_confidence: number | null;
  error_count: number;
  created_at: string;
  updated_at: string;
}

export interface HomeworkSubmissionDetailOut {
  id: string;
  student_id: string;
  title: string;
  selected_subject: HomeworkSubjectSelection;
  detected_subject: HomeworkSubjectArea | null;
  subject_confidence: number | null;
  language_code: string;
  status: HomeworkSubmissionStatus;
  page_count: number;
  retry_count: number;
  needs_ocr_review: boolean;
  failure_reason: string | null;
  files: HomeworkFileOut[];
  ocr_pages: HomeworkOcrPageOut[];
  latest_evaluation: HomeworkEvaluationOut | null;
  evaluation_history: HomeworkEvaluationOut[];
  created_at: string;
  updated_at: string;
}

// ------------------------------------------------------------------
// Phase 7: Teacher, Mentor & Parent Ecosystem
// ------------------------------------------------------------------
export interface TeacherSectionOut {
  id: string;
  class_id: string;
  name: string;
  code: string;
  capacity: number;
  enrolled_count: number;
}

export interface TeacherClassOut {
  id: string;
  tenant_id: string | null;
  teacher_id: string;
  name: string;
  grade_label: string;
  subject_name: string;
  status: string;
  sections_count: number;
  students_count: number;
  assignments_count: number;
  created_at: string;
}

export interface ClassEnrollmentOut {
  id: string;
  class_id: string;
  section_id: string | null;
  section_name: string | null;
  student_id: string;
  student_name: string;
  student_email: string;
  roll_no: string | null;
  status: string;
  enrolled_at: string;
}

export interface QuestionBankOptionOut {
  question_id: string;
  question_version_id: string;
  question_type: string;
  difficulty: string;
  default_marks: number;
  stem_preview: string;
}

export interface TeacherAssignmentOut {
  id: string;
  class_id: string;
  section_id: string | null;
  teacher_id: string;
  title: string;
  instructions: string;
  assignment_type: "assignment" | "quiz" | "test";
  question_ids: string[];
  max_marks: number;
  due_at: string | null;
  status: "draft" | "published" | "closed";
  submissions_count: number;
  graded_count: number;
  created_at: string;
}

export interface AssignmentSubmissionOut {
  id: string;
  assignment_id: string;
  student_id: string;
  student_name: string;
  student_email: string;
  response_text: string;
  ai_suggested_score: number | null;
  ai_feedback_summary: string | null;
  teacher_score: number | null;
  teacher_override_reason: string | null;
  teacher_feedback: string | null;
  effective_score: number | null;
  max_marks: number;
  status: "submitted" | "ai_graded" | "teacher_reviewed" | "returned";
  graded_by: string | null;
  graded_at: string | null;
  created_at: string;
}

export interface TeacherWeakConceptOut {
  concept_id: string;
  average_mastery_pct: number;
  affected_students_count: number;
}

export interface TeacherClassAnalyticsOut {
  class_id: string;
  class_name: string;
  total_students: number;
  total_assignments: number;
  total_submissions: number;
  graded_submissions: number;
  average_score_pct: number;
  average_mastery_pct: number;
  weak_concepts: TeacherWeakConceptOut[];
}

export interface TeacherStudentAnalyticsOut {
  student_id: string;
  student_name: string;
  student_email: string;
  enrolled_classes_count: number;
  practice_total_attempts: number;
  practice_accuracy_pct: number;
  mastery_average_pct: number;
  weak_concepts: TeacherWeakConceptOut[];
  submissions_total: number;
  submissions_average_pct: number;
}

export interface TeacherDashboardOut {
  teacher_id: string;
  total_classes: number;
  total_students: number;
  total_assignments: number;
  pending_reviews_count: number;
  classes: TeacherClassOut[];
  recent_assignments: TeacherAssignmentOut[];
}

export interface MentorStudentRosterOut {
  assignment_id: string;
  student_id: string;
  student_name: string;
  student_email: string;
  status: string;
  notes: string | null;
  active_goals_count: number;
  open_follow_ups_count: number;
  created_at: string;
}

export interface MentorGoalOut {
  id: string;
  mentor_id: string;
  student_id: string;
  title: string;
  description: string;
  target_date: string | null;
  progress_pct: number;
  status: "active" | "completed" | "paused";
  created_at: string;
}

export interface MentorSessionOut {
  id: string;
  mentor_id: string;
  student_id: string;
  scheduled_at: string;
  duration_minutes: number;
  status: "scheduled" | "completed" | "cancelled";
  summary_notes: string;
  recommendations: string[];
  created_at: string;
}

export interface MentorFollowUpOut {
  id: string;
  session_id: string | null;
  mentor_id: string;
  student_id: string;
  title: string;
  due_date: string | null;
  status: "open" | "in_progress" | "completed";
  created_at: string;
}

export interface MentorWeakConceptOut {
  concept_id: string;
  mastery_score: number;
  band: string;
}

export interface MentorStudentReviewOut {
  student_id: string;
  student_name: string;
  student_email: string;
  primary_exam_target: string;
  daily_study_minutes_target: number;
  practice_total_attempts: number;
  practice_accuracy_pct: number;
  mastery_average_pct: number;
  weak_concepts: MentorWeakConceptOut[];
  due_flashcards_count: number;
  active_study_plans_count: number;
  completed_plan_items_count: number;
  homework_evaluated_count: number;
  recommended_interventions: string[];
  goals: MentorGoalOut[];
  sessions: MentorSessionOut[];
  follow_ups: MentorFollowUpOut[];
}

export interface MentorDashboardOut {
  mentor_id: string;
  assigned_students_count: number;
  active_goals_count: number;
  upcoming_sessions_count: number;
  open_follow_ups_count: number;
  students: MentorStudentRosterOut[];
}

export interface ParentPrivacySettingsOut {
  share_learning_summary: boolean;
  share_weak_topics: boolean;
  share_upcoming_tests: boolean;
  allow_raw_ai_transcripts: boolean;
}

export interface GuardianLinkOut {
  id: string;
  parent_user_id: string;
  student_user_id: string;
  student_name: string;
  student_email: string;
  relationship_type: "parent" | "guardian";
  consent_status: "pending" | "verified" | "revoked";
  consent_granted_at: string | null;
  revoked_at: string | null;
  privacy_settings: ParentPrivacySettingsOut;
  verification_code_preview?: string | null;
  created_at: string;
}

export interface ParentGoalOut {
  id: string;
  parent_user_id: string;
  student_user_id: string;
  title: string;
  target_date: string | null;
  target_minutes_per_day: number;
  status: "active" | "achieved" | "archived";
  created_at: string;
}

export interface ParentUpcomingTestOut {
  id: string;
  title: string;
  assignment_type: string;
  due_at: string | null;
  max_marks: number;
}

export interface ParentLearningSummaryOut {
  student_user_id: string;
  student_name: string;
  consent_status: string;
  privacy_notice: string;
  privacy_settings: ParentPrivacySettingsOut;
  onboarding_completed: boolean;
  primary_exam_target: string;
  daily_study_minutes_target: number;
  practice_total_attempts: number;
  practice_correct_attempts: number;
  practice_accuracy_pct: number;
  practice_sessions_completed: number;
  mastery_average_pct: number;
  mastered_concepts_count: number;
  weak_topics: MentorWeakConceptOut[];
  revision_due_flashcards: number;
  revision_total_flashcards: number;
  revision_active_study_plans: number;
  revision_completed_plan_items: number;
  homework_total_submissions: number;
  homework_evaluated_submissions: number;
  upcoming_assessments: ParentUpcomingTestOut[];
  goals: ParentGoalOut[];
  generated_at: string;
}

export interface ParentDashboardOut {
  parent_user_id: string;
  linked_students: GuardianLinkOut[];
  active_goals_count: number;
  verified_links_count: number;
  pending_links_count: number;
}

// ------------------------------------------------------------------
// Phase 8: Institutional Multi-Tenant Platform & Subscriptions
// ------------------------------------------------------------------
export interface SubscriptionPlanOut {
  id: string;
  code: string;
  name: string;
  tier: string;
  monthly_price_inr: number;
  max_students: number;
  max_teachers: number;
  max_branches: number;
  entitlements: Record<string, boolean>;
  is_active: boolean;
}

export interface TenantSubscriptionOut {
  id: string;
  tenant_id: string;
  plan_id: string;
  plan_code: string;
  plan_name: string;
  tier: string;
  status: "trial" | "active" | "past_due" | "cancelled";
  seat_limit: number;
  max_teachers: number;
  max_branches: number;
  effective_entitlements: Record<string, boolean>;
  starts_at: string;
  ends_at: string | null;
}

export interface OrganizationOut {
  id: string;
  slug: string;
  name: string;
  organization_type: "school_group" | "coaching_institute" | "standalone_school";
  status: string;
  contact_email: string;
  config: Record<string, unknown>;
  plan_code: string | null;
  plan_name: string | null;
  subscription_status: string | null;
  seat_limit: number;
  max_teachers: number;
  max_branches: number;
  entitlements: Record<string, boolean>;
  created_at: string;
}

export interface SchoolOut {
  id: string;
  tenant_id: string;
  code: string;
  name: string;
  board_code: string;
  city: string | null;
  status: string;
  config: Record<string, unknown>;
  branches_count: number;
  batches_count: number;
  created_at: string;
}

export interface BranchOut {
  id: string;
  tenant_id: string;
  school_id: string;
  code: string;
  name: string;
  address: string | null;
  status: string;
  created_at: string;
}

export interface AcademicYearOut {
  id: string;
  tenant_id: string;
  school_id: string;
  label: string;
  starts_on: string;
  ends_on: string;
  is_current: boolean;
}

export interface InstitutionBatchOut {
  id: string;
  tenant_id: string;
  school_id: string;
  branch_id: string | null;
  academic_year_id: string | null;
  name: string;
  grade_label: string;
  section_name: string;
  exam_track: string;
  capacity: number;
  status: string;
  enrolled_count: number;
}

export interface InstitutionMemberOut {
  id: string;
  tenant_id: string;
  school_id: string | null;
  branch_id: string | null;
  user_id: string;
  user_name: string;
  user_email: string;
  member_role: "school_admin" | "teacher" | "mentor" | "student";
  status: string;
  created_at: string;
}

export interface BatchEnrollmentOut {
  id: string;
  tenant_id: string;
  batch_id: string;
  student_id: string;
  student_name: string;
  student_email: string;
  roll_no: string | null;
  status: string;
  enrolled_at: string;
}

export interface InstitutionAssessmentOut {
  id: string;
  tenant_id: string;
  school_id: string;
  batch_id: string | null;
  title: string;
  kind: "assignment" | "test";
  due_at: string | null;
  max_marks: number;
  status: string;
  created_at: string;
}

export interface InstitutionSchoolSummaryOut {
  school_id: string;
  school_name: string;
  board_code: string;
  branches_count: number;
  batches_count: number;
  assessments_count: number;
}

export interface InstitutionReportOut {
  tenant_id: string;
  organization_name: string;
  plan_code: string;
  subscription_status: string;
  schools_count: number;
  branches_count: number;
  max_branches: number;
  batches_count: number;
  teachers_count: number;
  max_teachers: number;
  mentors_count: number;
  students_count: number;
  seat_limit: number;
  seat_utilization_pct: number;
  assessments_count: number;
  average_student_practice_accuracy_pct: number;
  average_student_mastery_pct: number;
  schools_breakdown: InstitutionSchoolSummaryOut[];
  generated_at: string;
}

// ------------------------------------------------------------------
// Phase 9: Examination Preparation Ecosystem (CBSE, JEE Main, JEE Adv, NEET)
// ------------------------------------------------------------------
export type ExamTrackCode = "CBSE_BOARD" | "JEE_MAIN" | "JEE_ADVANCED" | "NEET" | string;

export type ExamCoverageStatus =
  | "empty"
  | "partial_unverified"
  | "audited_partial"
  | "audited_complete";

export interface ExamCoverageAuditOut {
  exam_code: ExamTrackCode;
  mapped_chapters_count: number;
  included_chapters_count: number;
  audited_chapters_count: number;
  chapters_with_questions_count: number;
  published_question_count: number;
  verified_pyq_count: number;
  unverified_pyq_excluded_count: number;
  audited_coverage_pct: number;
  question_coverage_pct: number;
  coverage_status: ExamCoverageStatus;
  coverage_disclaimer: string;
}

export interface ExamTrackOverviewOut {
  id: string;
  code: ExamTrackCode;
  name: string;
  target_seconds_per_question: number;
  active_pattern: ExamPatternOut | null;
  patterns: ExamPatternOut[];
  coverage_audit: ExamCoverageAuditOut;
}

export interface SyllabusTopicItemOut {
  id: string;
  title: string;
}

export interface ExamSyllabusChapterOut {
  id: string;
  exam_track_id: string;
  pattern_version_label: string;
  subject_id: string;
  subject_name: string;
  chapter_id: string;
  chapter_title: string;
  weightage_pct: number;
  expected_questions: number;
  priority_tier: "high_yield" | "core" | "optional";
  syllabus_status: "included" | "reduced" | "excluded";
  notes: string | null;
  audit_verified: boolean;
  audited_at: string | null;
  published_question_count: number;
  verified_pyq_count: number;
  topics: SyllabusTopicItemOut[];
}

export interface ExamSyllabusResponse {
  exam_code: ExamTrackCode;
  exam_name: string;
  pattern_version_label: string;
  coverage_audit: ExamCoverageAuditOut;
  chapters: ExamSyllabusChapterOut[];
}

export interface VerifiedPyqBadgeOut {
  is_verified_pyq: true;
  badge_label: string;
  exam_name: string;
  exam_year: number;
  exam_session: string | null;
  exam_shift: string | null;
  paper_code: string | null;
  question_number: string | null;
  source_url: string | null;
  verification_status: "verified";
}

export interface ExamQuestionOptionRedactedOut {
  option_key: string;
  content_markdown: string;
}

export interface ExamQuestionItemOut {
  question_id: string;
  question_version_id: string;
  question_type: string;
  subject_id: string;
  subject_name: string;
  chapter_id: string;
  chapter_title: string;
  topic_id: string | null;
  topic_title: string | null;
  concept_id: string | null;
  concept_title: string | null;
  stem_markdown: string;
  difficulty: string;
  default_marks: number;
  default_negative_marks: number;
  estimated_seconds: number;
  options: ExamQuestionOptionRedactedOut[];
  pyq_provenance: VerifiedPyqBadgeOut | null;
}

export interface ExamQuestionFacetsOut {
  available_years: number[];
  available_sessions: string[];
  available_difficulties: string[];
  available_question_types: string[];
  total_published_questions: number;
  total_verified_pyqs: number;
  unverified_pyq_excluded_count: number;
}

export interface ExamQuestionsExplorerResponse {
  exam_code: ExamTrackCode;
  verified_pyq_only: boolean;
  facets: ExamQuestionFacetsOut;
  questions: ExamQuestionItemOut[];
}

export interface LaunchedExamAttemptOut {
  attempt_id: string;
  exam_code: ExamTrackCode;
  test_id: string | null;
  quiz_id: string | null;
  title: string;
  pattern_version_label: string | null;
  question_count: number;
  duration_seconds: number | null;
  started_at: string;
  expires_at: string | null;
}

export interface WeaknessBucketOut {
  entity_id: string | null;
  name: string;
  attempts: number;
  correct: number;
  accuracy_pct: number;
  avg_seconds: number;
  severity: "critical" | "needs_focus" | "developing";
}

export interface ExamPerformanceHistoryItemOut {
  attempt_id: string;
  title: string;
  category: string;
  submitted_at: string;
  raw_score: number;
  max_score: number;
  accuracy_pct: number;
  avg_seconds_per_question: number;
}

export interface ExamAnalyticsResponse {
  exam_code: ExamTrackCode;
  exam_name: string;
  total_attempts: number;
  total_questions_answered: number;
  overall_accuracy_pct: number;
  average_seconds_per_question: number;
  target_seconds_per_question: number;
  pacing_status: string;
  weak_subjects: WeaknessBucketOut[];
  weak_chapters: WeaknessBucketOut[];
  weak_concepts: WeaknessBucketOut[];
  performance_history: ExamPerformanceHistoryItemOut[];
  improvement_recommendations: string[];
}

export interface FormulaVariableItem {
  symbol: string;
  meaning: string;
  unit?: string | null;
}

export interface ExamFormulaOut {
  id: string;
  exam_track_id: string;
  subject_id: string;
  subject_name: string;
  chapter_id: string;
  chapter_title: string;
  topic_id: string | null;
  topic_title: string | null;
  title: string;
  formula_latex: string;
  variables: FormulaVariableItem[];
  when_to_use: string;
  common_pitfall: string | null;
  difficulty: string;
  is_high_yield: boolean;
  status: string;
}

export interface ExamRevisionPlanBlock {
  activity: string;
  title: string;
  minutes: number;
  chapter_id: string | null;
  focus_note: string;
}

export interface ExamRevisionPlanDay {
  day_number: number;
  date: string;
  total_minutes: number;
  blocks: ExamRevisionPlanBlock[];
}

export interface ExamRevisionPlanOut {
  id: string;
  exam_track_id: string;
  exam_code: ExamTrackCode;
  exam_pattern_id: string | null;
  title: string;
  target_exam_date: string;
  daily_minutes: number;
  focus_chapters: Array<{
    chapter_id: string;
    chapter_title: string;
    subject_name: string;
    weightage_pct: number;
    priority_tier: string;
    student_accuracy_pct: number | null;
  }>;
  schedule: ExamRevisionPlanDay[];
  status: string;
  created_at: string;
}

export interface DetailedSolutionItemOut {
  sequence_no: number;
  question_id: string;
  question_version_id: string;
  question_type: string;
  subject_name: string;
  chapter_title: string;
  stem_markdown: string;
  options: ExamQuestionOptionRedactedOut[];
  student_response_jsonb: Record<string, unknown>;
  correct_answer_jsonb: Record<string, unknown>;
  is_correct: boolean | null;
  marks_awarded: number;
  time_spent_seconds: number;
  explanation_markdown: string | null;
  steps: string[];
  common_mistakes_markdown: string | null;
}

export interface AttemptDetailedSolutionsResponse {
  attempt_id: string;
  title: string;
  status: string;
  raw_score: number;
  max_score: number;
  accuracy_pct: number;
  submitted_at: string | null;
  items: DetailedSolutionItemOut[];
}

// ------------------------------------------------------------------
// Phase 10: Multilingual Learning Expansion Contracts
// ------------------------------------------------------------------
export type LanguageModalityKey =
  | "ui"
  | "explanation"
  | "voice"
  | "subtitle"
  | "question"
  | "answer";

export interface ModalityResolutionOut {
  modality: string;
  requested_language: string;
  effective_language: string;
  fallback_applied: boolean;
  fallback_reason: string | null;
  capability_status: string;
  availability_status: string;
  testing_status: string;
  rtl: boolean;
  provider: string | NoneOrString;
}

type NoneOrString = string | null;

export interface UserLanguagePreferencesOut {
  ui_language: string;
  preferred_explanation_language: string;
  preferred_voice_language: string;
  preferred_subtitle_language: string;
  preferred_question_language: string;
  preferred_answer_language: string;
  bilingual_explanation_mode: BilingualMode | string;
  resolutions: Record<string, ModalityResolutionOut>;
}

export interface UiLocalizationBundleOut {
  requested_language: string;
  effective_language: string;
  rtl: boolean;
  coverage_pct: number;
  translated_key_count: number;
  total_key_count: number;
  fallback_keys: string[];
  strings: Record<string, string>;
}

export interface GlossaryTermOut {
  id: string;
  concept_key: string;
  subject_area: string;
  english_term: string;
  language_code: string;
  localized_term: string;
  transliteration: string | null;
  preserve_english_in_bilingual: boolean;
  latex_symbol: string | null;
  review_status: string;
  notes: string | null;
  created_at: string;
}

export interface NotationPreservationOut {
  math_preserved: boolean;
  science_preserved: boolean;
  all_preserved: boolean;
  math_preservation_score: number;
  science_notation_score: number;
  math_expressions: string[];
  scientific_notations: string[];
  si_unit_values: string[];
  chemical_formulas: string[];
  missing_math: string[];
  missing_science: string[];
}

export interface BilingualPreviewResponse {
  rendered_text: string;
  bilingual_mode: string;
  explanation_resolution: ModalityResolutionOut;
  subtitle_resolution: ModalityResolutionOut;
  voice_resolution: ModalityResolutionOut;
  speakable_math_text: string;
  notation_report: NotationPreservationOut;
  matched_glossary_terms: Array<{
    concept_key?: string;
    english_term: string;
    localized_term: string;
    transliteration?: string | null;
    latex_symbol?: string | null;
    preserve_english_in_bilingual?: boolean;
  }>;
  tts_provider_configured: boolean;
  stt_provider_configured: boolean;
}

export interface TranslationEntryOut {
  id: string;
  resource_type: string;
  resource_key: string;
  source_language_code: string;
  target_language_code: string;
  source_text: string;
  translated_text: string;
  bilingual_text: string | null;
  notation_preserved: boolean;
  terminology_warnings: string[];
  status: string;
  quality_score: number | null;
  reviewer_notes: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface LanguageQualityEvaluationOut {
  id: string;
  language_code: string;
  modality: string;
  provider_name: string;
  test_suite_version: string;
  script_fidelity_score: number;
  math_preservation_score: number;
  science_notation_score: number;
  terminology_accuracy_score: number;
  fluency_score: number;
  overall_score: number;
  passed: boolean;
  sample_count: number;
  findings: Array<{
    sample_id?: string;
    math_preserved?: boolean;
    science_preserved?: boolean;
    script_ratio?: number;
    issues?: string[];
  }>;
  evaluated_at: string;
}

export interface STTResponseOut {
  stt_available: boolean;
  transcript: string | null;
  confidence: number | null;
  requested_language: string;
  effective_language: string;
  fallback_applied: boolean;
  provider: string;
  latency_ms: number;
  audio_seconds: number;
  is_fallback: boolean;
  fallback_mode: string | null;
  limitation_notice: string | null;
}

export interface VoiceProviderStatusOut {
  elevenlabs_configured: boolean;
  tts_model_id: string;
  stt_model_id: string;
  verified_tts_languages: string[];
  verified_stt_languages: string[];
  honest_status_notice: string;
}




