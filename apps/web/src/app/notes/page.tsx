"use client";

import type { BookmarkOut, StudentNoteOut } from "@go4guru/contracts";
import { EmptyState, ErrorBanner, LoadingCard } from "@go4guru/ui";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { MathText } from "@/components/math-text";
import {
  ApiClientError,
  createStudentNote,
  deleteBookmark,
  deleteStudentNote,
  listBookmarks,
  listStudentNotes,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

export default function NotesAndBookmarksPage() {
  const router = useRouter();
  const { token, initializing } = useAuth();
  const [notes, setNotes] = useState<StudentNoteOut[]>([]);
  const [bookmarks, setBookmarks] = useState<BookmarkOut[]>([]);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initializing) return;
    if (!token) {
      router.push("/login");
      return;
    }
    const authToken = token;
    async function load() {
      setLoading(true);
      try {
        const [n, b] = await Promise.all([
          listStudentNotes(authToken),
          listBookmarks(authToken),
        ]);
        setNotes(n);
        setBookmarks(b);
      } catch (err) {
        setError(err instanceof ApiClientError ? err.message : "Failed to load notes.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [initializing, token, router]);

  async function handleCreateNote(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setError(null);
    try {
      const created = await createStudentNote(token, {
        title,
        body_markdown: body,
      });
      setNotes((prev) => [created, ...prev]);
      setTitle("");
      setBody("");
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Could not save note.");
    }
  }

  return (
    <main id="main-content" className="mx-auto max-w-5xl space-y-8 px-4 py-8 sm:px-6">
      <header className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-bold text-slate-900">
          Personal Notes &amp; Saved Questions
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Private Markdown &amp; KaTeX notes and bookmarked practice questions.
        </p>
      </header>

      {error ? <ErrorBanner title="Error" message={error} /> : null}
      {loading ? <LoadingCard message="Loading personal study notes..." /> : null}

      {!loading ? (
        <div className="grid gap-8 lg:grid-cols-2">
          <section className="space-y-4">
            <form
              onSubmit={(e) => void handleCreateNote(e)}
              className="space-y-3 rounded-lg border border-slate-200 bg-white p-4"
            >
              <h2 className="text-base font-semibold text-slate-900">New Study Note</h2>
              <input
                type="text"
                required
                placeholder="Note title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
              <textarea
                required
                rows={3}
                placeholder="Write formula or summary using $...$ for KaTeX..."
                value={body}
                onChange={(e) => setBody(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
              <button
                type="submit"
                className="rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-800"
              >
                Save Note
              </button>
            </form>

            {notes.length === 0 ? (
              <EmptyState
                title="No Notes Yet"
                description="Create your first concept note above or save one directly while solving a practice question."
              />
            ) : (
              <ul className="space-y-3">
                {notes.map((n) => (
                  <li
                    key={n.id}
                    className="rounded-lg border border-slate-200 bg-white p-4"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-semibold text-slate-900">{n.title}</h3>
                      <button
                        type="button"
                        onClick={async () => {
                          if (!token) return;
                          await deleteStudentNote(token, n.id);
                          setNotes((prev) => prev.filter((item) => item.id !== n.id));
                        }}
                        className="text-xs font-medium text-red-700 hover:underline"
                      >
                        Delete
                      </button>
                    </div>
                    <div className="mt-2 text-sm text-slate-700">
                      <MathText text={n.body_markdown} />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="space-y-4">
            <h2 className="text-base font-semibold text-slate-900">
              Bookmarked Questions ({bookmarks.length})
            </h2>
            {bookmarks.length === 0 ? (
              <EmptyState
                title="No Bookmarks Yet"
                description="Save tricky practice questions during study sessions for quick revision."
              />
            ) : (
              <ul className="space-y-2">
                {bookmarks.map((b) => (
                  <li
                    key={b.question_id}
                    className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-3 text-sm"
                  >
                    <div>
                      <p className="font-medium text-slate-900">{b.folder_name}</p>
                      <p className="font-mono text-xs text-slate-500">
                        Question ID: {b.question_id}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={async () => {
                        if (!token) return;
                        await deleteBookmark(token, b.question_id);
                        setBookmarks((prev) =>
                          prev.filter((item) => item.question_id !== b.question_id)
                        );
                      }}
                      className="text-xs font-medium text-red-700 hover:underline"
                    >
                      Remove
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      ) : null}
    </main>
  );
}
