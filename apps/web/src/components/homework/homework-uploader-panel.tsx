"use client";

import type { HomeworkSubjectSelection } from "@go4guru/contracts";
import { ErrorBanner } from "@go4guru/ui";
import { useRef, useState } from "react";
import {
  formatBytes,
  HOMEWORK_MAX_PAGES,
  reorderPageQueue,
  SUBJECT_OPTIONS,
  validateHomeworkFileQueue,
} from "@/lib/homework-helpers";

interface HomeworkUploaderPanelProps {
  submitting: boolean;
  onSubmit: (payload: {
    files: File[];
    title: string;
    selected_subject: HomeworkSubjectSelection;
    manual_transcript: string;
  }) => Promise<boolean>;
}

export function HomeworkUploaderPanel({
  submitting,
  onSubmit,
}: HomeworkUploaderPanelProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [title, setTitle] = useState("");
  const [selectedSubject, setSelectedSubject] =
    useState<HomeworkSubjectSelection>("auto");
  const [files, setFiles] = useState<File[]>([]);
  const [manualTranscript, setManualTranscript] = useState("");
  const [showTranscriptHelper, setShowTranscriptHelper] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  function addFiles(incoming: FileList | File[]) {
    const incomingArr = Array.from(incoming);
    if (incomingArr.length === 0) return;
    const nextQueue = [...files, ...incomingArr];
    const check = validateHomeworkFileQueue(nextQueue);
    setValidationErrors(check.errors);
    if (check.valid) {
      setFiles(nextQueue);
      if (!title.trim() && incomingArr[0]) {
        const stem = incomingArr[0].name.replace(/\.[^/.]+$/, "").replace(/[_-]+/g, " ");
        setTitle(stem.slice(0, 100));
      }
    }
  }

  function handleRemoveFile(index: number) {
    const next = files.filter((_, idx) => idx !== index);
    setFiles(next);
    if (next.length > 0) {
      const check = validateHomeworkFileQueue(next);
      setValidationErrors(check.errors);
    } else {
      setValidationErrors([]);
    }
  }

  function handleMoveFile(fromIndex: number, toIndex: number) {
    setFiles((prev) => reorderPageQueue(prev, fromIndex, toIndex));
  }

  async function handleFormSubmit(e: React.FormEvent) {
    e.preventDefault();
    const check = validateHomeworkFileQueue(files);
    if (!check.valid) {
      setValidationErrors(check.errors);
      return;
    }
    setValidationErrors([]);
    const ok = await onSubmit({
      files,
      title: title.trim() || "Homework Submission",
      selected_subject: selectedSubject,
      manual_transcript: manualTranscript.trim(),
    });
    if (ok) {
      setFiles([]);
      setTitle("");
      setManualTranscript("");
      setShowTranscriptHelper(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  const totalBytes = files.reduce((acc, f) => acc + f.size, 0);

  return (
    <section
      aria-labelledby="homework-upload-heading"
      className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs"
    >
      <div>
        <h2
          id="homework-upload-heading"
          className="text-base font-semibold text-slate-900"
        >
          New Homework Check
        </h2>
        <p className="mt-0.5 text-xs text-slate-500 tabular-nums">
          Up to {HOMEWORK_MAX_PAGES} pages · JPG, PNG, WebP, PDF
        </p>
      </div>
      <p className="mt-1.5 text-xs text-slate-600">
        EXIF metadata is stripped and active PDF scripts are blocked before OCR
        and subject-aware evaluation.
      </p>

      <form onSubmit={(e) => void handleFormSubmit(e)} className="mt-4 space-y-4">
        <div>
          <label
            htmlFor="homework-title"
            className="block text-xs font-medium text-slate-700"
          >
            Homework title
          </label>
          <input
            id="homework-title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={200}
            placeholder="e.g. Linear Equations Worksheet Q4"
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        <div>
          <label
            htmlFor="homework-subject"
            className="block text-xs font-medium text-slate-700"
          >
            Subject
          </label>
          <select
            id="homework-subject"
            value={selectedSubject}
            onChange={(e) =>
              setSelectedSubject(e.target.value as HomeworkSubjectSelection)
            }
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            {SUBJECT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            if (e.dataTransfer.files?.length) {
              addFiles(e.dataTransfer.files);
            }
          }}
          className={`rounded-lg border-2 border-dashed p-4 text-center transition ${
            isDragging
              ? "border-indigo-500 bg-indigo-50/50"
              : "border-slate-300 bg-slate-50/70 hover:border-slate-400"
          }`}
        >
          <input
            ref={fileInputRef}
            id="homework-file-input"
            type="file"
            multiple
            accept=".jpg,.jpeg,.png,.webp,.pdf,image/jpeg,image/png,image/webp,application/pdf"
            onChange={(e) => {
              if (e.target.files) {
                addFiles(e.target.files);
              }
            }}
            className="sr-only"
          />
          <p className="text-sm font-medium text-slate-800">
            Drop notebook photos or PDF pages here
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Max 10 MB per file · 25 MB total · Multi-page order preserved
          </p>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="mt-3 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-800 hover:bg-slate-100"
          >
            Choose Files
          </button>
        </div>

        {validationErrors.length > 0 && (
          <ErrorBanner
            title="Upload validation issue"
            message={validationErrors.join(" ")}
          />
        )}

        {files.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-600">
              <span className="font-medium text-slate-800 tabular-nums">
                Queued pages ({files.length})
              </span>
              <span className="tabular-nums">{formatBytes(totalBytes)}</span>
            </div>
            <ol className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
              {files.map((file, idx) => (
                <li
                  key={`${file.name}-${file.size}-${idx}`}
                  className="flex items-center justify-between gap-2 px-3 py-2 text-xs"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-slate-900">
                      <span className="mr-1.5 text-slate-500 tabular-nums">
                        P{idx + 1}.
                      </span>
                      {file.name}
                    </p>
                    <p className="text-slate-500 tabular-nums">
                      {file.type || "document"} · {formatBytes(file.size)}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    <button
                      type="button"
                      disabled={idx === 0}
                      aria-label={`Move page ${idx + 1} up`}
                      onClick={() => handleMoveFile(idx, idx - 1)}
                      className="rounded border border-slate-200 px-1.5 py-0.5 text-slate-600 hover:bg-slate-100 disabled:opacity-40"
                    >
                      Up
                    </button>
                    <button
                      type="button"
                      disabled={idx === files.length - 1}
                      aria-label={`Move page ${idx + 1} down`}
                      onClick={() => handleMoveFile(idx, idx + 1)}
                      className="rounded border border-slate-200 px-1.5 py-0.5 text-slate-600 hover:bg-slate-100 disabled:opacity-40"
                    >
                      Down
                    </button>
                    <button
                      type="button"
                      aria-label={`Remove ${file.name}`}
                      onClick={() => handleRemoveFile(idx)}
                      className="rounded border border-rose-200 px-1.5 py-0.5 text-rose-700 hover:bg-rose-50"
                    >
                      Remove
                    </button>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        )}

        <div>
          <button
            type="button"
            onClick={() => setShowTranscriptHelper((v) => !v)}
            className="text-xs font-medium text-indigo-700 hover:text-indigo-800"
          >
            {showTranscriptHelper
              ? "Hide optional handwriting transcript"
              : "+ Add optional typed transcript (helpful for faint handwriting)"}
          </button>
          {showTranscriptHelper && (
            <div className="mt-2">
              <label
                htmlFor="homework-manual-transcript"
                className="block text-xs font-medium text-slate-700"
              >
                Optional question & steps transcript
              </label>
              <textarea
                id="homework-manual-transcript"
                rows={4}
                value={manualTranscript}
                onChange={(e) => setManualTranscript(e.target.value)}
                placeholder={"Question: Solve 2x + 4 = 10\nStep 1: 2x = 14\nStep 2: x = 7"}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={submitting || files.length === 0}
          className="w-full rounded-lg bg-indigo-700 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting
            ? "Scanning & Evaluating Homework..."
            : "Upload & Evaluate Step-by-Step"}
        </button>
      </form>
    </section>
  );
}
