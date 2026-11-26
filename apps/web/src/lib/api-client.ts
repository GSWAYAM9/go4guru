import type {
  AcademicSessionOut,
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
  AttemptHistoryItem,
  AttemptResultOut,
  AttemptResultResponse,
  AttemptStateResponse,
  AuthTokenResponse,
  AutosaveResponse,
  BoardOut,
  BookmarkOut,
  CheckpointSubmitResponse,
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
  ExamPatternOut,
  FlashcardOut,
  FlashcardReviewResponse,
  FlashcardType,
  GradeOut,
  ImportBatchOut,
  ImportPreviewResponse,
  LanguageCapabilityOut,
  LearningPathItemOut,
  LearningPathOut,
  LessonPlanOut,
  MfaSetupResponse,
  MisconceptionOut,
  NotificationOut,
  PracticeSessionOut,
  QuestionOut,
  QuestionSearchResponse,
  QuizOut,
  ReadinessResponse,
  RevisionAnalyticsOut,
  ScoringRuleContract,
  StudentAnalyticsOverviewResponse,
  StudentDashboardResponse,
  StudentNoteOut,
  StudentProfileResponse,
  StudyPlanItemOut,
  StudyPlanOut,
  SubjectOut,
  SyncMissedResponse,
  TTSResponseOut,
  TeachingMode,
  TestOut,
  UserProfileResponse,
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
export function buildClassroomWsUrl(sessionId: string, token: string): string {
  const base = publicEnv.apiBaseUrl.replace(/^http/i, "ws").replace(/\/+$/, "");
  return `${base}/ws/v1/classroom/${sessionId}?token=${encodeURIComponent(token)}`;
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
