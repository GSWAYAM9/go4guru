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
  mode: "standard" | "partial_subset";
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

export interface LanguageCapabilityOut {
  language_code: string;
  display_name: string;
  native_name: string;
  rtl: boolean;
  text_quality_tier: string;
  translation_status: string;
  tts_supported: boolean;
  stt_supported: boolean;
  voice_provider: string | null;
  pronunciation_tier: string | null;
  subtitle_supported: boolean;
  academic_review_status: string;
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
