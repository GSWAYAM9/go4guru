import type {
  AcademicSessionOut,
  AcademicYearOut,
  AdaptiveOverviewOut,
  AiCostSummaryResponse,
  AiEvalRunResponse,
  AiMessageOut,
  AiModelsCatalogResponse,
  AiReviewQueueOut,
  AiSessionOut,
  AiTurnResponse,
  AiUsageQuotaResponse,
  ApiMetaResponse,
  AssignmentSubmissionOut,
  AttemptDetailedSolutionsResponse,
  AttemptHistoryItem,
  AttemptResultOut,
  AttemptResultResponse,
  AttemptStateResponse,
  AuthTokenResponse,
  AutosaveResponse,
  BatchEnrollmentOut,
  BilingualMode,
  BilingualPreviewResponse,
  BoardOut,
  BookmarkOut,
  BranchOut,
  CheckpointSubmitResponse,
  ClassEnrollmentOut,
  ClassroomSessionDetailOut,
  ClassroomSessionSummaryOut,
  ClassroomWhiteboardAction,
  CohortAnalyticsResponse,
  ConceptMasteryOut,
  ContentLicenseResponse,
  ContentSourceResponse,
  CurriculumTreeResponse,
  CurriculumVersionOut,
  DoubtInterruptResponse,
  ErrorEnvelope,
  ExamAnalyticsResponse,
  ExamFormulaOut,
  ExamPatternOut,
  ExamQuestionsExplorerResponse,
  ExamRevisionPlanOut,
  ExamSyllabusChapterOut,
  ExamSyllabusResponse,
  ExamTrackOverviewOut,
  FlashcardOut,
  FlashcardReviewResponse,
  FlashcardType,
  FormulaVariableItem,
  GlossaryTermOut,
  GradeOut,
  GuardianLinkOut,
  HomeworkEvaluationOut,
  HomeworkSubmissionDetailOut,
  HomeworkSubmissionSummaryOut,
  HomeworkSubjectSelection,
  ImportBatchOut,
  ImportPreviewResponse,
  InstitutionAssessmentOut,
  InstitutionBatchOut,
  InstitutionMemberOut,
  InstitutionReportOut,
  LanguageCapabilityOut,
  LanguageQualityEvaluationOut,
  LaunchedExamAttemptOut,
  LearningPathItemOut,
  LearningPathOut,
  LessonPlanOut,
  MentorDashboardOut,
  MentorFollowUpOut,
  MentorGoalOut,
  MentorSessionOut,
  MentorStudentReviewOut,
  MentorStudentRosterOut,
  MfaSetupResponse,
  MisconceptionOut,
  NotificationOut,
  OrganizationOut,
  ParentDashboardOut,
  ParentGoalOut,
  ParentLearningSummaryOut,
  PracticeSessionOut,
  QuestionBankOptionOut,
  QuestionOut,
  QuestionSearchResponse,
  QuizOut,
  ReadinessResponse,
  RevisionAnalyticsOut,
  STTResponseOut,
  SchoolOut,
  ScoringRuleContract,
  StudentAnalyticsOverviewResponse,
  StudentDashboardResponse,
  StudentNoteOut,
  StudentProfileResponse,
  StudyPlanItemOut,
  StudyPlanOut,
  SubjectOut,
  SubscriptionPlanOut,
  SyncMissedResponse,
  TTSResponseOut,
  TeacherAssignmentOut,
  TeacherClassAnalyticsOut,
  TeacherClassOut,
  TeacherDashboardOut,
  TeacherSectionOut,
  TeacherStudentAnalyticsOut,
  TeachingMode,
  TenantSubscriptionOut,
  TestOut,
  TranslationEntryOut,
  UiLocalizationBundleOut,
  UserLanguagePreferencesOut,
  UserProfileResponse,
  VoiceProviderStatusOut,
  WhiteboardEventOut,
  WhiteboardSnapshotOut,
} from "@go4guru/contracts";
import { publicEnv } from "./env";

export class ApiClientError extends Error {
  readonly code: string;
  readonly requestId?: string;
  readonly statusCode: number;

  constructor(
    message: string,
    opts: { code: string; statusCode: number; requestId?: string }
  ) {
    super(message);
    this.name = "ApiClientError";
    this.code = opts.code;
    this.statusCode = opts.statusCode;
    this.requestId = opts.requestId;
  }
}

async function parseErrorOrThrow(response: Response): Promise<never> {
  try {
    const body = (await response.json()) as Partial<ErrorEnvelope>;
    if (body.error) {
      throw new ApiClientError(body.error.message, {
        code: body.error.code,
        statusCode: response.status,
        requestId: body.error.request_id,
      });
    }
  } catch (err) {
    if (err instanceof ApiClientError) {
      throw err;
    }
  }
  throw new ApiClientError(`HTTP ${response.status} from API`, {
    code: `HTTP_${response.status}`,
    statusCode: response.status,
  });
}

async function apiFetch<T>(
  path: string,
  opts: RequestInit & { token?: string | null; baseUrl?: string } = {}
): Promise<T> {
  const baseUrl = opts.baseUrl ?? publicEnv.apiBaseUrl;
  const headers = new Headers(opts.headers);
  if (opts.token) {
    headers.set("Authorization", `Bearer ${opts.token}`);
  }
  if (
    opts.body &&
    typeof opts.body === "string" &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${baseUrl}${path}`, {
    ...opts,
    headers,
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    return parseErrorOrThrow(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function fetchReadiness(
  baseUrl: string = publicEnv.apiBaseUrl
): Promise<ReadinessResponse> {
  const response = await fetch(`${baseUrl}/api/v1/health/ready`, {
    cache: "no-store",
  });
  if (response.status === 200 || response.status === 503) {
    return (await response.json()) as ReadinessResponse;
  }
  return parseErrorOrThrow(response);
}

export async function fetchApiMeta(
  baseUrl: string = publicEnv.apiBaseUrl
): Promise<ApiMetaResponse> {
  return apiFetch<ApiMetaResponse>("/api/v1/meta", { baseUrl });
}

export async function registerAccount(payload: {
  email: string;
  password: string;
  display_name: string;
  date_of_birth_year?: number | null;
  role?: "student" | "parent";
}): Promise<AuthTokenResponse> {
  return apiFetch<AuthTokenResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function loginAccount(payload: {
  email: string;
  password: string;
  totp_code?: string | null;
}): Promise<AuthTokenResponse> {
  return apiFetch<AuthTokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function refreshAuthSession(): Promise<AuthTokenResponse> {
  return apiFetch<AuthTokenResponse>("/api/v1/auth/refresh", {
    method: "POST",
  });
}

export async function logoutAccount(token: string): Promise<void> {
  return apiFetch<void>("/api/v1/auth/logout", {
    method: "POST",
    token,
  });
}

export async function setupMfa(token: string): Promise<MfaSetupResponse> {
  return apiFetch<MfaSetupResponse>("/api/v1/auth/mfa/setup", {
    method: "POST",
    token,
  });
}

export async function verifyMfa(
  token: string,
  code: string
): Promise<AuthTokenResponse> {
  return apiFetch<AuthTokenResponse>("/api/v1/auth/mfa/verify", {
    method: "POST",
    token,
    body: JSON.stringify({ code }),
  });
}

export async function fetchMeProfile(token: string): Promise<UserProfileResponse> {
  return apiFetch<UserProfileResponse>("/api/v1/users/me", { token });
}

export async function fetchStudentProfile(
  token: string
): Promise<StudentProfileResponse> {
  return apiFetch<StudentProfileResponse>("/api/v1/users/me/student-profile", {
    token,
  });
}

export async function updateStudentProfile(
  token: string,
  payload: {
    board_id: string | null;
    academic_session_id: string | null;
    grade_id: string | null;
    curriculum_version_id: string | null;
    primary_exam_target: string;
    daily_study_minutes_target: number;
  }
): Promise<StudentProfileResponse> {
  return apiFetch<StudentProfileResponse>("/api/v1/users/me/student-profile", {
    method: "PUT",
    token,
    body: JSON.stringify(payload),
  });
}

export async function fetchStudentDashboard(
  token: string
): Promise<StudentDashboardResponse> {
  return apiFetch<StudentDashboardResponse>("/api/v1/dashboard/student", {
    token,
  });
}

export async function fetchBoards(): Promise<BoardOut[]> {
  return apiFetch<BoardOut[]>("/api/v1/curriculum/boards");
}

export async function fetchSessions(): Promise<AcademicSessionOut[]> {
  return apiFetch<AcademicSessionOut[]>("/api/v1/curriculum/sessions");
}

export async function fetchGrades(): Promise<GradeOut[]> {
  return apiFetch<GradeOut[]>("/api/v1/curriculum/grades");
}

export async function fetchSubjects(): Promise<SubjectOut[]> {
  return apiFetch<SubjectOut[]>("/api/v1/curriculum/subjects");
}

export async function fetchCurriculumVersions(
  token?: string | null,
  includeDrafts = false
): Promise<CurriculumVersionOut[]> {
  return apiFetch<CurriculumVersionOut[]>(
    `/api/v1/curriculum/versions?include_drafts=${includeDrafts}`,
    { token }
  );
}

export async function fetchCurriculumTree(params: {
  versionId?: string;
  gradeId?: string;
  subjectId?: string;
  includeDrafts?: boolean;
  token?: string | null;
}): Promise<CurriculumTreeResponse | null> {
  const qs = new URLSearchParams();
  if (params.versionId) qs.set("version_id", params.versionId);
  if (params.gradeId) qs.set("grade_id", params.gradeId);
  if (params.subjectId) qs.set("subject_id", params.subjectId);
  if (params.includeDrafts) qs.set("include_drafts", "true");
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiFetch<CurriculumTreeResponse | null>(
    `/api/v1/curriculum/tree${suffix}`,
    { token: params.token }
  );
}

export async function createCurriculumEntity(
  token: string,
  path: string,
  payload: Record<string, unknown>
): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(`/api/v1/curriculum${path}`, {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function fetchContentSources(
  token: string
): Promise<ContentSourceResponse[]> {
  return apiFetch<ContentSourceResponse[]>("/api/v1/content-rights/sources", {
    token,
  });
}

export async function fetchContentLicenses(
  token: string
): Promise<ContentLicenseResponse[]> {
  return apiFetch<ContentLicenseResponse[]>("/api/v1/content-rights/licenses", {
    token,
  });
}

export async function searchQuestionsApi(
  token: string,
  params: { q?: string; chapterId?: string; subjectId?: string; limit?: number }
): Promise<QuestionSearchResponse> {
  const qs = new URLSearchParams();
  if (params.q) qs.set("q", params.q);
  if (params.chapterId) qs.set("chapter_id", params.chapterId);
  if (params.subjectId) qs.set("subject_id", params.subjectId);
  if (params.limit) qs.set("limit", String(params.limit));
  return apiFetch<QuestionSearchResponse>(`/api/v1/questions?${qs.toString()}`, {
    token,
  });
}

export async function createQuestionApi(
  token: string,
  payload: Record<string, unknown>
): Promise<QuestionOut> {
  return apiFetch<QuestionOut>("/api/v1/questions", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function reviewQuestionApi(
  token: string,
  questionId: string,
  payload: { decision: string; feedback?: string; publish: boolean }
): Promise<QuestionOut> {
  return apiFetch<QuestionOut>(`/api/v1/questions/${questionId}/review`, {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function uploadImportWorkbook(
  token: string,
  file: File
): Promise<ImportBatchOut> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<ImportBatchOut>("/api/v1/imports/upload", {
    method: "POST",
    token,
    body: form,
  });
}

export async function saveImportMapping(
  token: string,
  batchId: string,
  payload: Record<string, unknown>
): Promise<ImportBatchOut> {
  return apiFetch<ImportBatchOut>(`/api/v1/imports/${batchId}/mapping`, {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function validateImportBatch(
  token: string,
  batchId: string
): Promise<ImportBatchOut> {
  return apiFetch<ImportBatchOut>(`/api/v1/imports/${batchId}/validate`, {
    method: "POST",
    token,
  });
}

export async function fetchImportPreview(
  token: string,
  batchId: string
): Promise<ImportPreviewResponse> {
  return apiFetch<ImportPreviewResponse>(`/api/v1/imports/${batchId}/preview`, {
    token,
  });
}

export async function commitImportBatch(
  token: string,
  batchId: string
): Promise<{ committed_count: number; skipped_count: number; status: string }> {
  return apiFetch(`/api/v1/imports/${batchId}/commit`, {
    method: "POST",
    token,
    body: JSON.stringify({ target_status: "REVIEW", include_warnings: true }),
  });
}

export async function rollbackImportBatch(
  token: string,
  batchId: string
): Promise<{ rolled_back_questions: number; status: string }> {
  return apiFetch(`/api/v1/imports/${batchId}/rollback`, {
    method: "POST",
    token,
  });
}

export async function startPracticeSession(
  token: string,
  payload: {
    subject_id?: string | null;
    chapter_id?: string | null;
    topic_id?: string | null;
    concept_id?: string | null;
    limit?: number;
  }
): Promise<PracticeSessionOut> {
  return apiFetch<PracticeSessionOut>("/api/v1/practice/sessions", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function revealPracticeHint(
  token: string,
  sessionId: string,
  questionId: string,
  hintLevel: number
): Promise<{ hint_markdown: string | null; hints_used_count: number }> {
  return apiFetch(`/api/v1/practice/sessions/${sessionId}/hints`, {
    method: "POST",
    token,
    body: JSON.stringify({ question_id: questionId, hint_level: hintLevel }),
  });
}

export async function submitPracticeAttempt(
  token: string,
  sessionId: string,
  payload: {
    question_id: string;
    response_jsonb: Record<string, unknown>;
    time_spent_seconds?: number;
  }
): Promise<AttemptResultOut> {
  return apiFetch<AttemptResultOut>(
    `/api/v1/practice/sessions/${sessionId}/attempts`,
    {
      method: "POST",
      token,
      body: JSON.stringify(payload),
    }
  );
}

export async function listStudentNotes(token: string): Promise<StudentNoteOut[]> {
  return apiFetch<StudentNoteOut[]>("/api/v1/notes", { token });
}

export async function createStudentNote(
  token: string,
  payload: {
    title: string;
    body_markdown: string;
    concept_id?: string | null;
    question_id?: string | null;
  }
): Promise<StudentNoteOut> {
  return apiFetch<StudentNoteOut>("/api/v1/notes", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function deleteStudentNote(
  token: string,
  noteId: string
): Promise<void> {
  return apiFetch<void>(`/api/v1/notes/${noteId}`, {
    method: "DELETE",
    token,
  });
}

export async function listBookmarks(token: string): Promise<BookmarkOut[]> {
  return apiFetch<BookmarkOut[]>("/api/v1/bookmarks", { token });
}

export async function saveBookmark(
  token: string,
  questionId: string,
  folderName = "General"
): Promise<BookmarkOut> {
  return apiFetch<BookmarkOut>("/api/v1/bookmarks", {
    method: "POST",
    token,
    body: JSON.stringify({ question_id: questionId, folder_name: folderName }),
  });
}

export async function deleteBookmark(
  token: string,
  questionId: string
): Promise<void> {
  return apiFetch<void>(`/api/v1/bookmarks/${questionId}`, {
    method: "DELETE",
    token,
  });
}

// --- Phase 2: Quizzes, Configurable Assessments & Analytics ---

export interface AutosaveAnswerPayload {
  question_version_id: string;
  response_jsonb: Record<string, unknown>;
  is_visited: boolean;
  is_marked_for_review: boolean;
  time_spent_seconds: number;
}

export async function listQuizzes(token: string): Promise<QuizOut[]> {
  return apiFetch<QuizOut[]>("/api/v1/quizzes", { token });
}

export async function generateQuiz(
  token: string,
  payload: {
    quiz_type: string;
    title: string;
    subject_id?: string | null;
    chapter_id?: string | null;
    topic_id?: string | null;
    concept_id?: string | null;
    exam_pattern_id?: string | null;
    question_count: number;
    duration_seconds?: number | null;
    grace_seconds?: number;
    shuffle_questions?: boolean;
    difficulty_distribution?: Record<string, number>;
    question_type_distribution?: Record<string, number>;
    scoring_rule?: ScoringRuleContract;
    seed?: number;
  }
): Promise<QuizOut> {
  return apiFetch<QuizOut>("/api/v1/quizzes/generate", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function startQuizAttempt(
  token: string,
  quizId: string
): Promise<AttemptStateResponse> {
  return apiFetch<AttemptStateResponse>(`/api/v1/quizzes/${quizId}/start`, {
    method: "POST",
    token,
  });
}

export async function listExamPatterns(
  token: string
): Promise<ExamPatternOut[]> {
  return apiFetch<ExamPatternOut[]>("/api/v1/assessments/exam-patterns", {
    token,
  });
}

export async function listTests(token: string): Promise<TestOut[]> {
  return apiFetch<TestOut[]>("/api/v1/assessments/tests", { token });
}

export async function createTestTemplate(
  token: string,
  payload: {
    title: string;
    description?: string | null;
    test_category: string;
    exam_pattern_id?: string | null;
    duration_seconds?: number | null;
    grace_seconds?: number;
    max_attempts?: number | null;
    shuffle_questions?: boolean;
    sections: {
      name: string;
      subject_id?: string | null;
      chapter_id?: string | null;
      question_count: number;
      attempt_limit?: number | null;
      scoring_rule: ScoringRuleContract;
      explicit_question_ids?: string[];
    }[];
  }
): Promise<TestOut> {
  return apiFetch<TestOut>("/api/v1/assessments/tests", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function publishTestTemplate(
  token: string,
  testId: string
): Promise<TestOut> {
  return apiFetch<TestOut>(`/api/v1/assessments/tests/${testId}/publish`, {
    method: "POST",
    token,
  });
}

export async function startTestAttempt(
  token: string,
  testId: string
): Promise<AttemptStateResponse> {
  return apiFetch<AttemptStateResponse>(
    `/api/v1/assessments/tests/${testId}/attempts`,
    {
      method: "POST",
      token,
    }
  );
}

export async function listAttemptHistory(
  token: string
): Promise<AttemptHistoryItem[]> {
  return apiFetch<AttemptHistoryItem[]>("/api/v1/assessments/attempts", {
    token,
  });
}

export async function getAttemptState(
  token: string,
  attemptId: string
): Promise<AttemptStateResponse> {
  return apiFetch<AttemptStateResponse>(
    `/api/v1/assessments/attempts/${attemptId}/state`,
    { token }
  );
}

export async function autosaveAttemptAnswers(
  token: string,
  attemptId: string,
  answers: AutosaveAnswerPayload[]
): Promise<AutosaveResponse> {
  return apiFetch<AutosaveResponse>(
    `/api/v1/assessments/attempts/${attemptId}/answers`,
    {
      method: "PUT",
      token,
      body: JSON.stringify({ answers }),
    }
  );
}

export async function submitAttempt(
  token: string,
  attemptId: string,
  idempotencyKey: string,
  answers: AutosaveAnswerPayload[] = []
): Promise<AttemptResultResponse> {
  return apiFetch<AttemptResultResponse>(
    `/api/v1/assessments/attempts/${attemptId}/submit`,
    {
      method: "POST",
      token,
      headers: {
        "Idempotency-Key": idempotencyKey,
      },
      body: JSON.stringify({ answers }),
    }
  );
}

export async function getAttemptResult(
  token: string,
  attemptId: string
): Promise<AttemptResultResponse> {
  return apiFetch<AttemptResultResponse>(
    `/api/v1/assessments/attempts/${attemptId}/result`,
    { token }
  );
}

export async function fetchStudentAnalyticsOverview(
  token: string
): Promise<StudentAnalyticsOverviewResponse> {
  return apiFetch<StudentAnalyticsOverviewResponse>(
    "/api/v1/analytics/student/overview",
    { token }
  );
}

export async function fetchCohortAnalytics(
  token: string
): Promise<CohortAnalyticsResponse> {
  return apiFetch<CohortAnalyticsResponse>("/api/v1/analytics/cohort", {
    token,
  });
}

// --- Phase 3: Modular AI Tutor, Hybrid RAG & Evaluations ---

export async function fetchAiModels(
  token: string
): Promise<AiModelsCatalogResponse> {
  return apiFetch<AiModelsCatalogResponse>("/api/v1/ai/models", { token });
}

export async function fetchAiUsage(
  token: string
): Promise<AiUsageQuotaResponse> {
  return apiFetch<AiUsageQuotaResponse>("/api/v1/ai/usage", { token });
}

export async function listAiSessions(token: string): Promise<AiSessionOut[]> {
  return apiFetch<AiSessionOut[]>("/api/v1/ai/sessions", { token });
}

export async function createAiSession(
  token: string,
  payload: {
    session_type?: string;
    title: string;
    teaching_mode: TeachingMode;
    language_code?: string;
    subject_id?: string | null;
    chapter_id?: string | null;
    concept_id?: string | null;
  }
): Promise<AiSessionOut> {
  return apiFetch<AiSessionOut>("/api/v1/ai/sessions", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function updateAiSessionMode(
  token: string,
  sessionId: string,
  payload: { teaching_mode: TeachingMode; language_code?: string }
): Promise<AiSessionOut> {
  return apiFetch<AiSessionOut>(`/api/v1/ai/sessions/${sessionId}/mode`, {
    method: "PATCH",
    token,
    body: JSON.stringify(payload),
  });
}

export async function listAiMessages(
  token: string,
  sessionId: string
): Promise<AiMessageOut[]> {
  return apiFetch<AiMessageOut[]>(`/api/v1/ai/sessions/${sessionId}/messages`, {
    token,
  });
}

export async function sendAiTurn(
  token: string,
  sessionId: string,
  payload: {
    message: string;
    teaching_mode?: TeachingMode;
    language_code?: string;
    preferred_provider?: "auto" | "gemini" | "openai" | "anthropic";
  }
): Promise<AiTurnResponse> {
  return apiFetch<AiTurnResponse>(`/api/v1/ai/sessions/${sessionId}/turns`, {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function flagAiMessage(
  token: string,
  messageId: string,
  reason: string
): Promise<AiReviewQueueOut> {
  return apiFetch<AiReviewQueueOut>(`/api/v1/ai/messages/${messageId}/flag`, {
    method: "POST",
    token,
    body: JSON.stringify({ reason }),
  });
}

export async function runAiEvals(token: string): Promise<AiEvalRunResponse> {
  return apiFetch<AiEvalRunResponse>("/api/v1/ai/evals/run", {
    method: "POST",
    token,
  });
}

export async function listAiReviewQueue(
  token: string
): Promise<AiReviewQueueOut[]> {
  return apiFetch<AiReviewQueueOut[]>("/api/v1/ai/review-queue", { token });
}

export async function fetchAdminAiCosts(
  token: string
): Promise<AiCostSummaryResponse> {
  return apiFetch<AiCostSummaryResponse>("/api/v1/admin/ai-costs", { token });
}

// ------------------------------------------------------------------
// Phase 4: Live Classroom, Language Capability Registry, Whiteboard & Voice
// ------------------------------------------------------------------
export function buildClassroomWsUrl(sessionId: string): string {
  const base = publicEnv.apiBaseUrl.replace(/^http/i, "ws").replace(/\/+$/, "");
  return `${base}/ws/v1/classroom/${encodeURIComponent(sessionId)}`;
}

export async function fetchLanguageCapabilities(): Promise<
  LanguageCapabilityOut[]
> {
  return apiFetch<LanguageCapabilityOut[]>("/api/v1/languages/capabilities");
}

export async function generateClassroomLesson(
  token: string,
  payload: {
    topic_title: string;
    subject_id?: string | null;
    chapter_id?: string | null;
    concept_id?: string | null;
    language_code?: string;
    voice_language?: string;
    subtitle_language?: string;
  }
): Promise<LessonPlanOut> {
  return apiFetch<LessonPlanOut>("/api/v1/classroom/lessons/generate", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function listClassroomLessons(
  token: string
): Promise<LessonPlanOut[]> {
  return apiFetch<LessonPlanOut[]>("/api/v1/classroom/lessons", { token });
}

export async function createClassroomSession(
  token: string,
  payload: {
    lesson_plan_id: string;
    playback_speed?: number;
    voice_language?: string;
    subtitle_language?: string;
  }
): Promise<ClassroomSessionDetailOut> {
  return apiFetch<ClassroomSessionDetailOut>("/api/v1/classroom/sessions", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function listClassroomSessions(
  token: string
): Promise<ClassroomSessionSummaryOut[]> {
  return apiFetch<ClassroomSessionSummaryOut[]>("/api/v1/classroom/sessions", {
    token,
  });
}

export async function getClassroomSession(
  token: string,
  sessionId: string
): Promise<ClassroomSessionDetailOut> {
  return apiFetch<ClassroomSessionDetailOut>(
    `/api/v1/classroom/sessions/${sessionId}`,
    { token }
  );
}

export async function controlClassroomSession(
  token: string,
  sessionId: string,
  payload: {
    action:
      | "play"
      | "pause"
      | "resume"
      | "repeat"
      | "next"
      | "previous"
      | "seek"
      | "set_speed"
      | "set_language"
      | "complete";
    playback_position_ms?: number;
    playback_speed?: number;
    voice_language?: string;
    subtitle_language?: string;
  }
): Promise<ClassroomSessionDetailOut> {
  return apiFetch<ClassroomSessionDetailOut>(
    `/api/v1/classroom/sessions/${sessionId}/control`,
    {
      method: "POST",
      token,
      body: JSON.stringify(payload),
    }
  );
}

export async function submitClassroomCheckpoint(
  token: string,
  sessionId: string,
  payload: { selected_key?: string; numeric_value?: number }
): Promise<CheckpointSubmitResponse> {
  return apiFetch<CheckpointSubmitResponse>(
    `/api/v1/classroom/sessions/${sessionId}/checkpoint`,
    {
      method: "POST",
      token,
      body: JSON.stringify(payload),
    }
  );
}

export async function askClassroomDoubt(
  token: string,
  sessionId: string,
  question: string
): Promise<DoubtInterruptResponse> {
  return apiFetch<DoubtInterruptResponse>(
    `/api/v1/classroom/sessions/${sessionId}/doubt`,
    {
      method: "POST",
      token,
      body: JSON.stringify({ question }),
    }
  );
}

export async function listWhiteboardEvents(
  token: string,
  sessionId: string
): Promise<WhiteboardEventOut[]> {
  return apiFetch<WhiteboardEventOut[]>(
    `/api/v1/whiteboard/sessions/${sessionId}/events`,
    { token }
  );
}

export async function postWhiteboardAction(
  token: string,
  sessionId: string,
  action: ClassroomWhiteboardAction
): Promise<ClassroomSessionDetailOut> {
  return apiFetch<ClassroomSessionDetailOut>(
    `/api/v1/whiteboard/sessions/${sessionId}/events`,
    {
      method: "POST",
      token,
      body: JSON.stringify({ action }),
    }
  );
}

export async function undoWhiteboard(
  token: string,
  sessionId: string
): Promise<ClassroomSessionDetailOut> {
  return apiFetch<ClassroomSessionDetailOut>(
    `/api/v1/whiteboard/sessions/${sessionId}/undo`,
    { method: "POST", token }
  );
}

export async function redoWhiteboard(
  token: string,
  sessionId: string
): Promise<ClassroomSessionDetailOut> {
  return apiFetch<ClassroomSessionDetailOut>(
    `/api/v1/whiteboard/sessions/${sessionId}/redo`,
    { method: "POST", token }
  );
}

export async function saveWhiteboardSnapshot(
  token: string,
  sessionId: string
): Promise<WhiteboardSnapshotOut> {
  return apiFetch<WhiteboardSnapshotOut>(
    `/api/v1/whiteboard/sessions/${sessionId}/snapshot`,
    { method: "POST", token }
  );
}

export async function getLatestWhiteboardSnapshot(
  token: string,
  sessionId: string
): Promise<WhiteboardSnapshotOut> {
  return apiFetch<WhiteboardSnapshotOut>(
    `/api/v1/whiteboard/sessions/${sessionId}/snapshots/latest`,
    { token }
  );
}

export async function synthesizeVoiceTts(
  token: string,
  payload: {
    text: string;
    language_code?: string;
    speed?: number;
    classroom_session_id?: string | null;
  }
): Promise<TTSResponseOut> {
  return apiFetch<TTSResponseOut>("/api/v1/voice/tts", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

// ------------------------------------------------------------------
// Phase 5: Adaptive Mastery, Spaced Repetition & Study Planner
// ------------------------------------------------------------------
export async function fetchAdaptiveOverview(
  token: string
): Promise<AdaptiveOverviewOut> {
  return apiFetch<AdaptiveOverviewOut>("/api/v1/learning/overview", { token });
}

export async function recomputeAdaptiveMastery(
  token: string
): Promise<AdaptiveOverviewOut> {
  return apiFetch<AdaptiveOverviewOut>("/api/v1/learning/recompute", {
    method: "POST",
    token,
  });
}

export async function listConceptMastery(
  token: string
): Promise<ConceptMasteryOut[]> {
  return apiFetch<ConceptMasteryOut[]>("/api/v1/learning/mastery", { token });
}

export async function resolveMisconception(
  token: string,
  misconceptionId: string
): Promise<MisconceptionOut> {
  return apiFetch<MisconceptionOut>(
    `/api/v1/learning/misconceptions/${misconceptionId}/resolve`,
    { method: "POST", token }
  );
}

export async function generateLearningPath(
  token: string,
  payload: { title: string; goal_exam_track?: string | null }
): Promise<LearningPathOut> {
  return apiFetch<LearningPathOut>("/api/v1/learning/learning-paths", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function listLearningPaths(
  token: string
): Promise<LearningPathOut[]> {
  return apiFetch<LearningPathOut[]>("/api/v1/learning/learning-paths", {
    token,
  });
}

export async function updateLearningPathItemStatus(
  token: string,
  itemId: string,
  status: "pending" | "in_progress" | "completed" | "skipped"
): Promise<LearningPathItemOut> {
  return apiFetch<LearningPathItemOut>(
    `/api/v1/learning/learning-paths/items/${itemId}`,
    { method: "PATCH", token, body: JSON.stringify({ status }) }
  );
}

export async function listFlashcards(
  token: string,
  cardType?: FlashcardType
): Promise<FlashcardOut[]> {
  const qs = cardType ? `?card_type=${encodeURIComponent(cardType)}` : "";
  return apiFetch<FlashcardOut[]>(`/api/v1/revision/flashcards${qs}`, {
    token,
  });
}

export async function listDueFlashcards(token: string): Promise<FlashcardOut[]> {
  return apiFetch<FlashcardOut[]>("/api/v1/revision/flashcards/due", {
    token,
  });
}

export async function createFlashcard(
  token: string,
  payload: {
    card_type: FlashcardType;
    concept_id?: string | null;
    language_code?: string;
    front_markdown: string;
    back_markdown: string;
    hint_markdown?: string | null;
    tags?: string[];
  }
): Promise<FlashcardOut> {
  return apiFetch<FlashcardOut>("/api/v1/revision/flashcards", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function syncMissedFlashcards(
  token: string
): Promise<SyncMissedResponse> {
  return apiFetch<SyncMissedResponse>("/api/v1/revision/flashcards/sync-missed", {
    method: "POST",
    token,
  });
}

export async function reviewFlashcard(
  token: string,
  flashcardId: string,
  payload: { quality: number; response_ms?: number }
): Promise<FlashcardReviewResponse> {
  return apiFetch<FlashcardReviewResponse>(
    `/api/v1/revision/flashcards/${flashcardId}/review`,
    { method: "POST", token, body: JSON.stringify(payload) }
  );
}

export async function listStudyPlans(token: string): Promise<StudyPlanOut[]> {
  return apiFetch<StudyPlanOut[]>("/api/v1/revision/study-plans", { token });
}

export async function generateStudyPlan(
  token: string,
  payload: { title: string; daily_minutes_budget: number; target_date?: string }
): Promise<StudyPlanOut> {
  return apiFetch<StudyPlanOut>("/api/v1/revision/study-plans", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function updateStudyPlanItemStatus(
  token: string,
  itemId: string,
  status: "pending" | "completed" | "skipped"
): Promise<StudyPlanItemOut> {
  return apiFetch<StudyPlanItemOut>(
    `/api/v1/revision/study-plans/items/${itemId}`,
    { method: "PATCH", token, body: JSON.stringify({ status }) }
  );
}

export async function fetchRevisionAnalytics(
  token: string
): Promise<RevisionAnalyticsOut> {
  return apiFetch<RevisionAnalyticsOut>("/api/v1/revision/analytics", {
    token,
  });
}

export async function listNotifications(
  token: string
): Promise<NotificationOut[]> {
  return apiFetch<NotificationOut[]>("/api/v1/notifications", { token });
}

export async function markNotificationRead(
  token: string,
  notificationId: string
): Promise<NotificationOut> {
  return apiFetch<NotificationOut>(
    `/api/v1/notifications/${notificationId}/read`,
    { method: "POST", token }
  );
}

// --- Phase 6: Homework AI ---

export async function uploadHomeworkSubmission(
  token: string,
  payload: {
    files: File[];
    title: string;
    selected_subject?: HomeworkSubjectSelection;
    language_code?: string;
    manual_transcript?: string;
  }
): Promise<HomeworkSubmissionDetailOut> {
  const form = new FormData();
  for (const file of payload.files) {
    form.append("files", file, file.name);
  }
  form.append("title", payload.title);
  form.append("selected_subject", payload.selected_subject ?? "auto");
  form.append("language_code", payload.language_code ?? "en");
  if (payload.manual_transcript && payload.manual_transcript.trim()) {
    form.append("manual_transcript", payload.manual_transcript.trim());
  }
  return apiFetch<HomeworkSubmissionDetailOut>("/api/v1/homework/submissions", {
    method: "POST",
    token,
    body: form,
  });
}

export async function listHomeworkSubmissions(
  token: string,
  limit = 30
): Promise<HomeworkSubmissionSummaryOut[]> {
  return apiFetch<HomeworkSubmissionSummaryOut[]>(
    `/api/v1/homework/submissions?limit=${encodeURIComponent(String(limit))}`,
    { token }
  );
}

export async function getHomeworkSubmission(
  token: string,
  submissionId: string
): Promise<HomeworkSubmissionDetailOut> {
  return apiFetch<HomeworkSubmissionDetailOut>(
    `/api/v1/homework/submissions/${submissionId}`,
    { token }
  );
}

export async function correctHomeworkOcr(
  token: string,
  submissionId: string,
  payload: {
    pages: { page_no: number; corrected_text: string }[];
    subject_override?: HomeworkSubjectSelection | null;
    re_evaluate?: boolean;
  }
): Promise<HomeworkSubmissionDetailOut> {
  return apiFetch<HomeworkSubmissionDetailOut>(
    `/api/v1/homework/submissions/${submissionId}/ocr`,
    {
      method: "PATCH",
      token,
      body: JSON.stringify(payload),
    }
  );
}

export async function submitHomeworkRetry(
  token: string,
  submissionId: string,
  payload: {
    revised_work_text: string;
    student_reflection?: string;
  }
): Promise<HomeworkSubmissionDetailOut> {
  return apiFetch<HomeworkSubmissionDetailOut>(
    `/api/v1/homework/submissions/${submissionId}/retry`,
    {
      method: "POST",
      token,
      body: JSON.stringify(payload),
    }
  );
}

export async function unlockHomeworkHint(
  token: string,
  submissionId: string,
  targetLevel?: 1 | 2 | 3
): Promise<HomeworkEvaluationOut> {
  return apiFetch<HomeworkEvaluationOut>(
    `/api/v1/homework/submissions/${submissionId}/hints/unlock`,
    {
      method: "POST",
      token,
      body: JSON.stringify(targetLevel ? { target_level: targetLevel } : {}),
    }
  );
}

export async function revealHomeworkSolution(
  token: string,
  submissionId: string
): Promise<HomeworkEvaluationOut> {
  return apiFetch<HomeworkEvaluationOut>(
    `/api/v1/homework/submissions/${submissionId}/solution/reveal`,
    {
      method: "POST",
      token,
      body: JSON.stringify({ confirm_reveal: true }),
    }
  );
}

// ------------------------------------------------------------------
// Phase 7: Teacher, Mentor & Parent Ecosystem
// ------------------------------------------------------------------
export async function fetchTeacherDashboard(
  token: string
): Promise<TeacherDashboardOut> {
  return apiFetch<TeacherDashboardOut>("/api/v1/teacher/dashboard", { token });
}

export async function createTeacherClass(
  token: string,
  payload: { name: string; grade_label: string; subject_name: string }
): Promise<TeacherClassOut> {
  return apiFetch<TeacherClassOut>("/api/v1/teacher/classes", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function listTeacherSections(
  token: string,
  classId: string
): Promise<TeacherSectionOut[]> {
  return apiFetch<TeacherSectionOut[]>(
    `/api/v1/teacher/classes/${classId}/sections`,
    { token }
  );
}

export async function createTeacherSection(
  token: string,
  classId: string,
  payload: { name: string; code: string; capacity?: number }
): Promise<TeacherSectionOut> {
  return apiFetch<TeacherSectionOut>(
    `/api/v1/teacher/classes/${classId}/sections`,
    {
      method: "POST",
      token,
      body: JSON.stringify(payload),
    }
  );
}

export async function listTeacherClassStudents(
  token: string,
  classId: string
): Promise<ClassEnrollmentOut[]> {
  return apiFetch<ClassEnrollmentOut[]>(
    `/api/v1/teacher/classes/${classId}/students`,
    { token }
  );
}

export async function enrollTeacherClassStudent(
  token: string,
  classId: string,
  payload: { student_email: string; section_id?: string | null; roll_no?: string | null }
): Promise<ClassEnrollmentOut> {
  return apiFetch<ClassEnrollmentOut>(
    `/api/v1/teacher/classes/${classId}/students`,
    {
      method: "POST",
      token,
      body: JSON.stringify(payload),
    }
  );
}

export async function listTeacherQuestionBankOptions(
  token: string,
  limit = 30
): Promise<QuestionBankOptionOut[]> {
  return apiFetch<QuestionBankOptionOut[]>(
    `/api/v1/teacher/question-bank?limit=${encodeURIComponent(String(limit))}`,
    { token }
  );
}

export async function listTeacherAssignments(
  token: string,
  classId?: string
): Promise<TeacherAssignmentOut[]> {
  const qs = classId ? `?class_id=${encodeURIComponent(classId)}` : "";
  return apiFetch<TeacherAssignmentOut[]>(`/api/v1/teacher/assignments${qs}`, {
    token,
  });
}

export async function createTeacherAssignment(
  token: string,
  payload: {
    class_id: string;
    section_id?: string | null;
    title: string;
    instructions?: string;
    assignment_type: "assignment" | "quiz" | "test";
    question_ids?: string[];
    max_marks: number;
    due_at?: string | null;
  }
): Promise<TeacherAssignmentOut> {
  return apiFetch<TeacherAssignmentOut>("/api/v1/teacher/assignments", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function listAssignmentSubmissions(
  token: string,
  assignmentId: string
): Promise<AssignmentSubmissionOut[]> {
  return apiFetch<AssignmentSubmissionOut[]>(
    `/api/v1/teacher/assignments/${assignmentId}/submissions`,
    { token }
  );
}

export async function aiGradeSubmission(
  token: string,
  submissionId: string
): Promise<AssignmentSubmissionOut> {
  return apiFetch<AssignmentSubmissionOut>(
    `/api/v1/teacher/submissions/${submissionId}/ai-grade`,
    { method: "POST", token }
  );
}

export async function overrideSubmissionGrade(
  token: string,
  submissionId: string,
  payload: {
    teacher_score: number;
    teacher_feedback?: string;
    teacher_override_reason?: string;
    status?: "teacher_reviewed" | "returned";
  }
): Promise<AssignmentSubmissionOut> {
  return apiFetch<AssignmentSubmissionOut>(
    `/api/v1/teacher/submissions/${submissionId}/override`,
    {
      method: "PATCH",
      token,
      body: JSON.stringify(payload),
    }
  );
}

export async function fetchTeacherClassAnalytics(
  token: string,
  classId: string
): Promise<TeacherClassAnalyticsOut> {
  return apiFetch<TeacherClassAnalyticsOut>(
    `/api/v1/teacher/classes/${classId}/analytics`,
    { token }
  );
}

export async function fetchTeacherStudentAnalytics(
  token: string,
  studentId: string
): Promise<TeacherStudentAnalyticsOut> {
  return apiFetch<TeacherStudentAnalyticsOut>(
    `/api/v1/teacher/students/${studentId}/analytics`,
    { token }
  );
}

export async function fetchTeacherClassReportCsv(
  token: string,
  classId: string
): Promise<string> {
  const response = await fetch(
    `${publicEnv.apiBaseUrl}/api/v1/teacher/classes/${classId}/report.csv`,
    {
      headers: { Authorization: `Bearer ${token}` },
      credentials: "include",
    }
  );
  if (!response.ok) {
    await parseErrorOrThrow(response);
  }
  return response.text();
}

export async function fetchMentorDashboard(
  token: string
): Promise<MentorDashboardOut> {
  return apiFetch<MentorDashboardOut>("/api/v1/mentor/dashboard", { token });
}

export async function assignMentorStudent(
  token: string,
  payload: { student_email: string; notes?: string }
): Promise<MentorStudentRosterOut> {
  return apiFetch<MentorStudentRosterOut>("/api/v1/mentor/students", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function fetchMentorStudentReview(
  token: string,
  studentId: string
): Promise<MentorStudentReviewOut> {
  return apiFetch<MentorStudentReviewOut>(
    `/api/v1/mentor/students/${studentId}/review`,
    { token }
  );
}

export async function createMentorGoal(
  token: string,
  payload: {
    student_id: string;
    title: string;
    description?: string;
    target_date?: string | null;
  }
): Promise<MentorGoalOut> {
  return apiFetch<MentorGoalOut>("/api/v1/mentor/goals", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function updateMentorGoal(
  token: string,
  goalId: string,
  payload: { progress_pct?: number; status?: "active" | "completed" | "paused" }
): Promise<MentorGoalOut> {
  return apiFetch<MentorGoalOut>(`/api/v1/mentor/goals/${goalId}`, {
    method: "PATCH",
    token,
    body: JSON.stringify(payload),
  });
}

export async function createMentorSession(
  token: string,
  payload: {
    student_id: string;
    scheduled_at: string;
    duration_minutes?: number;
    summary_notes?: string;
    recommendations?: string[];
    status?: "scheduled" | "completed" | "cancelled";
  }
): Promise<MentorSessionOut> {
  return apiFetch<MentorSessionOut>("/api/v1/mentor/sessions", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function createMentorFollowUp(
  token: string,
  payload: {
    student_id: string;
    session_id?: string | null;
    title: string;
    due_date?: string | null;
  }
): Promise<MentorFollowUpOut> {
  return apiFetch<MentorFollowUpOut>("/api/v1/mentor/follow-ups", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function updateMentorFollowUp(
  token: string,
  followUpId: string,
  payload: { status: "open" | "in_progress" | "completed" }
): Promise<MentorFollowUpOut> {
  return apiFetch<MentorFollowUpOut>(`/api/v1/mentor/follow-ups/${followUpId}`, {
    method: "PATCH",
    token,
    body: JSON.stringify(payload),
  });
}

export async function fetchParentDashboard(
  token: string
): Promise<ParentDashboardOut> {
  return apiFetch<ParentDashboardOut>("/api/v1/parent/dashboard", { token });
}

export async function requestGuardianLink(
  token: string,
  payload: { student_email: string; relationship_type: "parent" | "guardian" }
): Promise<GuardianLinkOut> {
  return apiFetch<GuardianLinkOut>("/api/v1/parent/links", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function verifyGuardianLink(
  token: string,
  linkId: string,
  verificationCode: string
): Promise<GuardianLinkOut> {
  return apiFetch<GuardianLinkOut>(`/api/v1/parent/links/${linkId}/verify`, {
    method: "POST",
    token,
    body: JSON.stringify({ verification_code: verificationCode }),
  });
}

export async function revokeGuardianLink(
  token: string,
  linkId: string
): Promise<GuardianLinkOut> {
  return apiFetch<GuardianLinkOut>(`/api/v1/parent/links/${linkId}/revoke`, {
    method: "POST",
    token,
  });
}

export async function updateGuardianPrivacy(
  token: string,
  linkId: string,
  payload: {
    share_learning_summary?: boolean;
    share_weak_topics?: boolean;
    share_upcoming_tests?: boolean;
  }
): Promise<GuardianLinkOut> {
  return apiFetch<GuardianLinkOut>(`/api/v1/parent/links/${linkId}/privacy`, {
    method: "PATCH",
    token,
    body: JSON.stringify(payload),
  });
}

export async function fetchParentStudentSummary(
  token: string,
  studentUserId: string
): Promise<ParentLearningSummaryOut> {
  return apiFetch<ParentLearningSummaryOut>(
    `/api/v1/parent/students/${studentUserId}/summary`,
    { token }
  );
}

export async function createParentGoal(
  token: string,
  payload: {
    student_user_id: string;
    title: string;
    target_date?: string | null;
    target_minutes_per_day?: number;
  }
): Promise<ParentGoalOut> {
  return apiFetch<ParentGoalOut>("/api/v1/parent/goals", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function updateParentGoal(
  token: string,
  goalId: string,
  payload: { status?: "active" | "achieved" | "archived" }
): Promise<ParentGoalOut> {
  return apiFetch<ParentGoalOut>(`/api/v1/parent/goals/${goalId}`, {
    method: "PATCH",
    token,
    body: JSON.stringify(payload),
  });
}

// ------------------------------------------------------------------
// Phase 8: Institutional Multi-Tenant Platform & Subscriptions
// ------------------------------------------------------------------
export async function listOrganizations(
  token: string
): Promise<OrganizationOut[]> {
  return apiFetch<OrganizationOut[]>("/api/v1/org/organizations", { token });
}

export async function createOrganization(
  token: string,
  payload: {
    slug: string;
    name: string;
    organization_type: "school_group" | "coaching_institute" | "standalone_school";
    contact_email: string;
    plan_code?: string;
  }
): Promise<OrganizationOut> {
  return apiFetch<OrganizationOut>("/api/v1/org/organizations", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function updateOrganizationConfig(
  token: string,
  orgId: string,
  payload: {
    default_language?: string;
    allow_ai_tutor?: boolean;
    allow_homework_ai?: boolean;
    require_mfa_for_admins?: boolean;
    allow_parent_portal?: boolean;
  }
): Promise<OrganizationOut> {
  return apiFetch<OrganizationOut>(`/api/v1/org/organizations/${orgId}/config`, {
    method: "PATCH",
    token,
    body: JSON.stringify(payload),
  });
}

export async function listOrgSchools(
  token: string,
  orgId: string
): Promise<SchoolOut[]> {
  return apiFetch<SchoolOut[]>(`/api/v1/org/organizations/${orgId}/schools`, {
    token,
  });
}

export async function createOrgSchool(
  token: string,
  orgId: string,
  payload: { code: string; name: string; board_code?: string; city?: string }
): Promise<SchoolOut> {
  return apiFetch<SchoolOut>(`/api/v1/org/organizations/${orgId}/schools`, {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function listOrgBranches(
  token: string,
  orgId: string
): Promise<BranchOut[]> {
  return apiFetch<BranchOut[]>(`/api/v1/org/organizations/${orgId}/branches`, {
    token,
  });
}

export async function createOrgBranch(
  token: string,
  orgId: string,
  payload: { school_id: string; code: string; name: string; address?: string }
): Promise<BranchOut> {
  return apiFetch<BranchOut>(`/api/v1/org/organizations/${orgId}/branches`, {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function listOrgAcademicYears(
  token: string,
  orgId: string
): Promise<AcademicYearOut[]> {
  return apiFetch<AcademicYearOut[]>(
    `/api/v1/org/organizations/${orgId}/academic-years`,
    { token }
  );
}

export async function createOrgAcademicYear(
  token: string,
  orgId: string,
  payload: {
    school_id: string;
    label: string;
    starts_on: string;
    ends_on: string;
    is_current?: boolean;
  }
): Promise<AcademicYearOut> {
  return apiFetch<AcademicYearOut>(
    `/api/v1/org/organizations/${orgId}/academic-years`,
    {
      method: "POST",
      token,
      body: JSON.stringify(payload),
    }
  );
}

export async function listOrgBatches(
  token: string,
  orgId: string
): Promise<InstitutionBatchOut[]> {
  return apiFetch<InstitutionBatchOut[]>(
    `/api/v1/org/organizations/${orgId}/batches`,
    { token }
  );
}

export async function createOrgBatch(
  token: string,
  orgId: string,
  payload: {
    school_id: string;
    branch_id?: string | null;
    academic_year_id?: string | null;
    name: string;
    grade_label: string;
    section_name?: string;
    exam_track?: string;
    capacity?: number;
  }
): Promise<InstitutionBatchOut> {
  return apiFetch<InstitutionBatchOut>(
    `/api/v1/org/organizations/${orgId}/batches`,
    {
      method: "POST",
      token,
      body: JSON.stringify(payload),
    }
  );
}

export async function listOrgMembers(
  token: string,
  orgId: string
): Promise<InstitutionMemberOut[]> {
  return apiFetch<InstitutionMemberOut[]>(
    `/api/v1/org/organizations/${orgId}/members`,
    { token }
  );
}

export async function addOrgMember(
  token: string,
  orgId: string,
  payload: {
    user_email: string;
    member_role: "school_admin" | "teacher" | "mentor" | "student";
    school_id?: string | null;
    branch_id?: string | null;
  }
): Promise<InstitutionMemberOut> {
  return apiFetch<InstitutionMemberOut>(
    `/api/v1/org/organizations/${orgId}/members`,
    {
      method: "POST",
      token,
      body: JSON.stringify(payload),
    }
  );
}

export async function enrollOrgBatchStudent(
  token: string,
  orgId: string,
  batchId: string,
  payload: { student_email: string; roll_no?: string | null }
): Promise<BatchEnrollmentOut> {
  return apiFetch<BatchEnrollmentOut>(
    `/api/v1/org/organizations/${orgId}/batches/${batchId}/enrollments`,
    {
      method: "POST",
      token,
      body: JSON.stringify(payload),
    }
  );
}

export async function listOrgAssessments(
  token: string,
  orgId: string
): Promise<InstitutionAssessmentOut[]> {
  return apiFetch<InstitutionAssessmentOut[]>(
    `/api/v1/org/organizations/${orgId}/assessments`,
    { token }
  );
}

export async function createOrgAssessment(
  token: string,
  orgId: string,
  payload: {
    school_id: string;
    batch_id?: string | null;
    title: string;
    kind: "assignment" | "test";
    due_at?: string | null;
    max_marks?: number;
  }
): Promise<InstitutionAssessmentOut> {
  return apiFetch<InstitutionAssessmentOut>(
    `/api/v1/org/organizations/${orgId}/assessments`,
    {
      method: "POST",
      token,
      body: JSON.stringify(payload),
    }
  );
}

export async function fetchOrgReport(
  token: string,
  orgId: string
): Promise<InstitutionReportOut> {
  return apiFetch<InstitutionReportOut>(
    `/api/v1/org/organizations/${orgId}/reports`,
    { token }
  );
}

export async function fetchOrgReportCsv(
  token: string,
  orgId: string
): Promise<string> {
  const response = await fetch(
    `${publicEnv.apiBaseUrl}/api/v1/org/organizations/${orgId}/reports.csv`,
    {
      headers: { Authorization: `Bearer ${token}` },
      credentials: "include",
    }
  );
  if (!response.ok) {
    await parseErrorOrThrow(response);
  }
  return response.text();
}

export async function listSubscriptionPlans(
  token: string
): Promise<SubscriptionPlanOut[]> {
  return apiFetch<SubscriptionPlanOut[]>("/api/v1/billing/plans", { token });
}

export async function fetchTenantSubscription(
  token: string,
  tenantId: string
): Promise<TenantSubscriptionOut> {
  return apiFetch<TenantSubscriptionOut>(
    `/api/v1/billing/tenants/${tenantId}/subscription`,
    { token }
  );
}

export async function updateTenantSubscription(
  token: string,
  tenantId: string,
  payload: {
    plan_code: string;
    status?: "trial" | "active" | "past_due" | "cancelled";
    seat_limit?: number | null;
  }
): Promise<TenantSubscriptionOut> {
  return apiFetch<TenantSubscriptionOut>(
    `/api/v1/billing/tenants/${tenantId}/subscription`,
    {
      method: "PUT",
      token,
      body: JSON.stringify(payload),
    }
  );
}

// ------------------------------------------------------------------
// Phase 9: Examination Preparation Ecosystem (CBSE, JEE Main, JEE Adv, NEET)
// ------------------------------------------------------------------

export async function listExamPrepTracks(
  token: string
): Promise<ExamTrackOverviewOut[]> {
  return apiFetch<ExamTrackOverviewOut[]>("/api/v1/exam-prep/tracks", {
    token,
  });
}

export async function fetchExamSyllabus(
  token: string,
  examCode: string,
  patternVersionLabel?: string
): Promise<ExamSyllabusResponse> {
  const qs = patternVersionLabel
    ? `?pattern_version_label=${encodeURIComponent(patternVersionLabel)}`
    : "";
  return apiFetch<ExamSyllabusResponse>(
    `/api/v1/exam-prep/${encodeURIComponent(examCode)}/syllabus${qs}`,
    { token }
  );
}

export async function upsertExamSyllabusChapter(
  token: string,
  examCode: string,
  payload: {
    pattern_version_label: string;
    subject_id: string;
    chapter_id: string;
    weightage_pct: number;
    expected_questions: number;
    priority_tier: "high_yield" | "core" | "optional";
    syllabus_status: "included" | "reduced" | "excluded";
    notes?: string | null;
    audit_verified?: boolean;
  }
): Promise<ExamSyllabusChapterOut> {
  return apiFetch<ExamSyllabusChapterOut>(
    `/api/v1/exam-prep/${encodeURIComponent(examCode)}/syllabus`,
    {
      method: "POST",
      token,
      body: JSON.stringify(payload),
    }
  );
}

export async function exploreExamQuestions(
  token: string,
  examCode: string,
  params: {
    verified_pyq_only?: boolean;
    exam_year?: number | null;
    exam_session?: string | null;
    difficulty?: string | null;
    question_type?: string | null;
    subject_id?: string | null;
    chapter_id?: string | null;
    topic_id?: string | null;
    limit?: number;
  } = {}
): Promise<ExamQuestionsExplorerResponse> {
  const sp = new URLSearchParams();
  if (params.verified_pyq_only) sp.set("verified_pyq_only", "true");
  if (params.exam_year) sp.set("exam_year", String(params.exam_year));
  if (params.exam_session) sp.set("exam_session", params.exam_session);
  if (params.difficulty) sp.set("difficulty", params.difficulty);
  if (params.question_type) sp.set("question_type", params.question_type);
  if (params.subject_id) sp.set("subject_id", params.subject_id);
  if (params.chapter_id) sp.set("chapter_id", params.chapter_id);
  if (params.topic_id) sp.set("topic_id", params.topic_id);
  if (params.limit) sp.set("limit", String(params.limit));
  const qs = sp.toString() ? `?${sp.toString()}` : "";
  return apiFetch<ExamQuestionsExplorerResponse>(
    `/api/v1/exam-prep/${encodeURIComponent(examCode)}/questions${qs}`,
    { token }
  );
}

export async function launchExamPractice(
  token: string,
  examCode: string,
  payload: {
    mode: "chapter_practice" | "topic_practice" | "verified_pyq_drill";
    title?: string;
    exam_pattern_id?: string | null;
    subject_id?: string | null;
    chapter_id?: string | null;
    topic_id?: string | null;
    difficulty?: "easy" | "medium" | "hard" | null;
    question_type?: string | null;
    exam_year?: number | null;
    exam_session?: string | null;
    verified_pyq_only?: boolean;
    question_count?: number;
    duration_seconds?: number | null;
  }
): Promise<LaunchedExamAttemptOut> {
  return apiFetch<LaunchedExamAttemptOut>(
    `/api/v1/exam-prep/${encodeURIComponent(examCode)}/practice`,
    {
      method: "POST",
      token,
      body: JSON.stringify(payload),
    }
  );
}

export async function generateExamMockTest(
  token: string,
  examCode: string,
  payload: {
    title?: string;
    exam_pattern_id?: string | null;
    mock_scope?: "full_mock" | "timed_section_mock";
    subject_id?: string | null;
    chapter_id?: string | null;
    verified_pyq_only?: boolean;
    seed?: number;
  }
): Promise<LaunchedExamAttemptOut> {
  return apiFetch<LaunchedExamAttemptOut>(
    `/api/v1/exam-prep/${encodeURIComponent(examCode)}/mocks/generate`,
    {
      method: "POST",
      token,
      body: JSON.stringify(payload),
    }
  );
}

export async function fetchExamAnalytics(
  token: string,
  examCode: string
): Promise<ExamAnalyticsResponse> {
  return apiFetch<ExamAnalyticsResponse>(
    `/api/v1/exam-prep/${encodeURIComponent(examCode)}/analytics`,
    { token }
  );
}

export async function listExamFormulas(
  token: string,
  examCode: string,
  params: { subject_id?: string; chapter_id?: string; high_yield_only?: boolean } = {}
): Promise<ExamFormulaOut[]> {
  const sp = new URLSearchParams();
  if (params.subject_id) sp.set("subject_id", params.subject_id);
  if (params.chapter_id) sp.set("chapter_id", params.chapter_id);
  if (params.high_yield_only) sp.set("high_yield_only", "true");
  const qs = sp.toString() ? `?${sp.toString()}` : "";
  return apiFetch<ExamFormulaOut[]>(
    `/api/v1/exam-prep/${encodeURIComponent(examCode)}/formulas${qs}`,
    { token }
  );
}

export async function createExamFormula(
  token: string,
  examCode: string,
  payload: {
    subject_id: string;
    chapter_id: string;
    topic_id?: string | null;
    title: string;
    formula_latex: string;
    variables?: FormulaVariableItem[];
    when_to_use: string;
    common_pitfall?: string | null;
    difficulty?: "easy" | "medium" | "hard";
    is_high_yield?: boolean;
  }
): Promise<ExamFormulaOut> {
  return apiFetch<ExamFormulaOut>(
    `/api/v1/exam-prep/${encodeURIComponent(examCode)}/formulas`,
    {
      method: "POST",
      token,
      body: JSON.stringify(payload),
    }
  );
}

export async function listExamRevisionPlans(
  token: string,
  examCode: string
): Promise<ExamRevisionPlanOut[]> {
  return apiFetch<ExamRevisionPlanOut[]>(
    `/api/v1/exam-prep/${encodeURIComponent(examCode)}/revision-plans`,
    { token }
  );
}

export async function createExamRevisionPlan(
  token: string,
  examCode: string,
  payload: {
    title?: string;
    exam_pattern_id?: string | null;
    target_exam_date: string;
    daily_minutes: number;
    focus_chapter_ids?: string[];
  }
): Promise<ExamRevisionPlanOut> {
  return apiFetch<ExamRevisionPlanOut>(
    `/api/v1/exam-prep/${encodeURIComponent(examCode)}/revision-plans`,
    {
      method: "POST",
      token,
      body: JSON.stringify(payload),
    }
  );
}

export async function fetchAttemptDetailedSolutions(
  token: string,
  attemptId: string
): Promise<AttemptDetailedSolutionsResponse> {
  return apiFetch<AttemptDetailedSolutionsResponse>(
    `/api/v1/exam-prep/attempts/${encodeURIComponent(attemptId)}/solutions`,
    { token }
  );
}

// ------------------------------------------------------------------
// Phase 10: Multilingual Learning Expansion
// ------------------------------------------------------------------
export async function fetchLanguagePreferences(
  token: string
): Promise<UserLanguagePreferencesOut> {
  return apiFetch<UserLanguagePreferencesOut>("/api/v1/languages/preferences", {
    token,
  });
}

export async function updateLanguagePreferences(
  token: string,
  payload: {
    ui_language?: string;
    preferred_explanation_language?: string;
    preferred_voice_language?: string;
    preferred_subtitle_language?: string;
    preferred_question_language?: string;
    preferred_answer_language?: string;
    bilingual_explanation_mode?: BilingualMode;
  }
): Promise<UserLanguagePreferencesOut> {
  return apiFetch<UserLanguagePreferencesOut>("/api/v1/languages/preferences", {
    method: "PUT",
    token,
    body: JSON.stringify(payload),
  });
}

export async function patchLanguageCapability(
  token: string,
  languageCode: string,
  payload: Record<string, unknown>
): Promise<LanguageCapabilityOut> {
  return apiFetch<LanguageCapabilityOut>(
    `/api/v1/languages/capabilities/${encodeURIComponent(languageCode)}`,
    {
      method: "PATCH",
      token,
      body: JSON.stringify(payload),
    }
  );
}

export async function fetchUiLocalizationBundle(
  languageCode: string
): Promise<UiLocalizationBundleOut> {
  return apiFetch<UiLocalizationBundleOut>(
    `/api/v1/languages/ui-bundle/${encodeURIComponent(languageCode)}`
  );
}

export async function listMultilingualGlossary(params?: {
  language_code?: string;
  subject_area?: string;
  query?: string;
}): Promise<GlossaryTermOut[]> {
  const sp = new URLSearchParams();
  if (params?.language_code) sp.set("language_code", params.language_code);
  if (params?.subject_area) sp.set("subject_area", params.subject_area);
  if (params?.query) sp.set("query", params.query);
  const qs = sp.toString() ? `?${sp.toString()}` : "";
  return apiFetch<GlossaryTermOut[]>(`/api/v1/languages/glossary${qs}`);
}

export async function upsertMultilingualGlossaryTerm(
  token: string,
  payload: {
    concept_key: string;
    subject_area: string;
    english_term: string;
    language_code: string;
    localized_term: string;
    transliteration?: string | null;
    preserve_english_in_bilingual?: boolean;
    latex_symbol?: string | null;
    notes?: string | null;
  }
): Promise<GlossaryTermOut> {
  return apiFetch<GlossaryTermOut>("/api/v1/languages/glossary", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function previewBilingualExplanation(payload: {
  source_text: string;
  explanation_language: string;
  subtitle_language: string;
  voice_language: string;
  bilingual_mode: BilingualMode;
}): Promise<BilingualPreviewResponse> {
  return apiFetch<BilingualPreviewResponse>("/api/v1/languages/bilingual-preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listTranslationEntries(
  token: string,
  params?: {
    target_language_code?: string;
    status_filter?: string;
    resource_type?: string;
  }
): Promise<TranslationEntryOut[]> {
  const sp = new URLSearchParams();
  if (params?.target_language_code) {
    sp.set("target_language_code", params.target_language_code);
  }
  if (params?.status_filter) sp.set("status_filter", params.status_filter);
  if (params?.resource_type) sp.set("resource_type", params.resource_type);
  const qs = sp.toString() ? `?${sp.toString()}` : "";
  return apiFetch<TranslationEntryOut[]>(`/api/v1/languages/translations${qs}`, {
    token,
  });
}

export async function submitTranslationEntry(
  token: string,
  payload: {
    resource_type:
      | "ui_string"
      | "question"
      | "lesson_segment"
      | "formula_note"
      | "concept_summary";
    resource_key: string;
    source_language_code?: string;
    target_language_code: string;
    source_text: string;
    translated_text: string;
    bilingual_text?: string | null;
  }
): Promise<TranslationEntryOut> {
  return apiFetch<TranslationEntryOut>("/api/v1/languages/translations", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function reviewTranslationEntry(
  token: string,
  entryId: string,
  payload: {
    decision: "approved" | "rejected" | "needs_revision";
    reviewer_notes?: string;
  }
): Promise<TranslationEntryOut> {
  return apiFetch<TranslationEntryOut>(
    `/api/v1/languages/translations/${encodeURIComponent(entryId)}/review`,
    {
      method: "POST",
      token,
      body: JSON.stringify(payload),
    }
  );
}

export async function listLanguageQualityEvaluations(
  languageCode?: string
): Promise<LanguageQualityEvaluationOut[]> {
  const qs = languageCode
    ? `?language_code=${encodeURIComponent(languageCode)}`
    : "";
  return apiFetch<LanguageQualityEvaluationOut[]>(
    `/api/v1/languages/evaluations${qs}`
  );
}

export async function runLanguageQualityEvaluation(
  token: string,
  payload: {
    language_code: string;
    modality:
      | "ui"
      | "explanation"
      | "bilingual"
      | "voice"
      | "stt"
      | "subtitle"
      | "question"
      | "answer";
    provider_name?: string;
    samples?: Array<{
      sample_id: string;
      source_text: string;
      candidate_text: string;
    }>;
  }
): Promise<LanguageQualityEvaluationOut> {
  return apiFetch<LanguageQualityEvaluationOut>(
    "/api/v1/languages/evaluations/run",
    {
      method: "POST",
      token,
      body: JSON.stringify(payload),
    }
  );
}

export async function fetchVoiceProviderCapabilities(): Promise<VoiceProviderStatusOut> {
  return apiFetch<VoiceProviderStatusOut>("/api/v1/voice/capabilities");
}

export async function transcribeVoiceStt(
  token: string,
  payload: {
    language_code: string;
    audio_base64?: string | null;
    mime_type?: string;
    browser_transcript_hint?: string | null;
    classroom_session_id?: string | null;
  }
): Promise<STTResponseOut> {
  return apiFetch<STTResponseOut>("/api/v1/voice/stt", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}
