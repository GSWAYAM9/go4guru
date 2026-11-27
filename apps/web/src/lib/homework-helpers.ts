import type {
  HomeworkConfidenceBand,
  HomeworkEvaluationOut,
  HomeworkEvaluationOverallStatus,
  HomeworkSubjectArea,
  HomeworkSubjectSelection,
} from "@go4guru/contracts";

export const HOMEWORK_MAX_FILE_BYTES = 10 * 1024 * 1024;
export const HOMEWORK_MAX_TOTAL_BYTES = 25 * 1024 * 1024;
export const HOMEWORK_MAX_PAGES = 10;

export const ALLOWED_UPLOAD_MIME_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
  "application/pdf",
]);

export const ALLOWED_UPLOAD_EXTENSIONS = new Set([
  ".jpg",
  ".jpeg",
  ".png",
  ".webp",
  ".pdf",
]);

export interface UploadCandidateLike {
  name: string;
  size: number;
  type: string;
}

export interface FileQueueValidationResult {
  valid: boolean;
  errors: string[];
  totalBytes: number;
}

export function getFileExtension(filename: string): string {
  const idx = filename.lastIndexOf(".");
  return idx >= 0 ? filename.slice(idx).toLowerCase() : "";
}

export function validateHomeworkFileQueue(
  files: UploadCandidateLike[],
  opts: {
    maxFileBytes?: number;
    maxTotalBytes?: number;
    maxPages?: number;
  } = {}
): FileQueueValidationResult {
  const maxFileBytes = opts.maxFileBytes ?? HOMEWORK_MAX_FILE_BYTES;
  const maxTotalBytes = opts.maxTotalBytes ?? HOMEWORK_MAX_TOTAL_BYTES;
  const maxPages = opts.maxPages ?? HOMEWORK_MAX_PAGES;
  const errors: string[] = [];

  if (files.length === 0) {
    return {
      valid: false,
      errors: ["Attach at least one homework image (JPG, PNG, WebP) or PDF page."],
      totalBytes: 0,
    };
  }

  if (files.length > maxPages) {
    errors.push(`Maximum ${maxPages} files can be queued per submission.`);
  }

  let totalBytes = 0;
  for (const file of files) {
    const ext = getFileExtension(file.name);
    const mimeOk = file.type ? ALLOWED_UPLOAD_MIME_TYPES.has(file.type.toLowerCase()) : false;
    const extOk = ALLOWED_UPLOAD_EXTENSIONS.has(ext);

    if (!mimeOk && !extOk) {
      errors.push(
        `'${file.name}' is not a supported format. Upload JPEG, PNG, WebP, or PDF files only.`
      );
    }
    if (file.size <= 0) {
      errors.push(`'${file.name}' is empty (0 bytes).`);
    } else if (file.size > maxFileBytes) {
      const limitMb = (maxFileBytes / (1024 * 1024)).toFixed(0);
      errors.push(`'${file.name}' exceeds the ${limitMb} MB per-file limit.`);
    }
    totalBytes += Math.max(0, file.size);
  }

  if (totalBytes > maxTotalBytes) {
    const limitMb = (maxTotalBytes / (1024 * 1024)).toFixed(0);
    errors.push(`Combined upload size exceeds the ${limitMb} MB submission limit.`);
  }

  return {
    valid: errors.length === 0,
    errors,
    totalBytes,
  };
}

export function reorderPageQueue<T>(items: readonly T[], fromIndex: number, toIndex: number): T[] {
  if (
    fromIndex < 0 ||
    toIndex < 0 ||
    fromIndex >= items.length ||
    toIndex >= items.length ||
    fromIndex === toIndex
  ) {
    return [...items];
  }
  const next = [...items];
  const [moved] = next.splice(fromIndex, 1);
  if (moved !== undefined) {
    next.splice(toIndex, 0, moved);
  }
  return next;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export const SUBJECT_OPTIONS: readonly {
  value: HomeworkSubjectSelection;
  label: string;
}[] = [
  { value: "auto", label: "Auto-detect subject" },
  { value: "mathematics", label: "Mathematics" },
  { value: "physics", label: "Physics" },
  { value: "chemistry", label: "Chemistry" },
  { value: "english", label: "English" },
  { value: "social_science", label: "Social Science" },
];

export const SUBJECT_LABELS: Record<HomeworkSubjectArea, string> = {
  mathematics: "Mathematics",
  physics: "Physics",
  chemistry: "Chemistry",
  english: "English",
  social_science: "Social Science",
};

export const SUBJECT_ERROR_TAXONOMY: Record<HomeworkSubjectArea, readonly string[]> = {
  mathematics: ["algebra", "formula", "arithmetic", "sign", "logic", "missing_steps"],
  physics: ["concept", "formula", "units", "calculation", "diagram", "reasoning"],
  chemistry: ["equation", "reaction", "formula", "concept", "calculation", "units"],
  english: ["grammar", "spelling", "vocabulary", "sentence_structure", "comprehension", "writing"],
  social_science: [
    "factual_accuracy",
    "concept",
    "structure",
    "missing_points",
    "explanation",
    "map_timeline",
  ],
};

export function formatErrorCategoryLabel(category: string): string {
  return category
    .split("_")
    .filter(Boolean)
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
}

export function formatOverallStatus(
  status: HomeworkEvaluationOverallStatus
): { label: string; tone: "healthy" | "degraded" | "neutral" } {
  switch (status) {
    case "correct":
      return { label: "Verified Correct", tone: "healthy" };
    case "partially_correct":
      return { label: "Partially Correct", tone: "degraded" };
    case "needs_correction":
      return { label: "Needs Correction", tone: "degraded" };
    case "unreadable_or_uncertain":
      return { label: "Needs OCR Review", tone: "neutral" };
  }
}

export function describeConfidenceBand(band: HomeworkConfidenceBand): string {
  switch (band) {
    case "high":
      return "High verification confidence";
    case "medium":
      return "Moderate confidence — check highlighted steps";
    case "low":
      return "Low confidence — verify OCR text carefully";
    case "uncertain":
      return "Uncertain extraction — edit transcription to re-evaluate";
  }
}

export interface RetryProgressSummary {
  attemptCount: number;
  initialErrors: number;
  latestErrors: number;
  errorsResolved: number;
  improved: boolean;
}

export function computeRetryProgress(
  evaluationHistory: readonly HomeworkEvaluationOut[]
): RetryProgressSummary | null {
  if (evaluationHistory.length < 2) {
    return null;
  }
  const ordered = [...evaluationHistory].sort((a, b) => a.attempt_no - b.attempt_no);
  const first = ordered[0];
  const latest = ordered[ordered.length - 1];
  const initialErrors = first.error_classifications.length;
  const latestErrors = latest.error_classifications.length;
  const errorsResolved = Math.max(0, initialErrors - latestErrors);
  const improved =
    latest.overall_status === "correct" ||
    latestErrors < initialErrors ||
    (first.overall_status === "needs_correction" &&
      latest.overall_status === "partially_correct");

  return {
    attemptCount: ordered.length,
    initialErrors,
    latestErrors,
    errorsResolved,
    improved,
  };
}
