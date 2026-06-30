"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { Search, X, ArrowRight } from "lucide-react";

export type SearchHit = {
  bookId: string;
  bookTitle: string;
  chapterId?: string;
  chapterTitle?: string;
  sectionId?: string;
  sectionTitle?: string;
  kind: "book" | "chapter" | "section";
  score: number;
  slug: string;
};

function buildLink(hit: SearchHit, query: string) {
  const params = new URLSearchParams();
  if (hit.chapterId) params.set("chapter", hit.chapterId);
  if (hit.sectionId) params.set("section", hit.sectionId);
  if (query) params.set("q", query); // so the book page can show "back to results"

  const qs = params.toString();
  return `/learn/${hit.slug}${qs ? "?" + qs : ""}`;
}

function hitLabel(hit: SearchHit) {
  if (hit.kind === "section" && hit.sectionTitle) {
    return (
      <>
        <span className="text-text-main font-medium">{hit.sectionTitle}</span>
        <span className="text-text-muted mx-1.5">in</span>
        <span className="text-accent">{hit.chapterTitle || hit.bookTitle}</span>
      </>
    );
  }
  if (hit.kind === "chapter" && hit.chapterTitle) {
    return (
      <>
        <span className="text-text-main font-medium">{hit.chapterTitle}</span>
        <span className="text-text-muted mx-1.5">in</span>
        <span className="text-accent">{hit.bookTitle}</span>
      </>
    );
  }
  return <span className="text-text-main font-medium">{hit.bookTitle}</span>;
}

export function LearnGlobalSearch({ initialQuery = "" }: { initialQuery?: string }) {
  const [query, setQuery] = useState(initialQuery);
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Debounced search
  useEffect(() => {
    const q = query.trim();
    if (!q || q.length < 2) {
      setHits([]);
      setOpen(false);
      return;
    }

    const t = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/learn/search?q=${encodeURIComponent(q)}&limit=35`);
        const data = await res.json();
        setHits(data.hits || []);
        setOpen(true);
      } catch {
        setHits([]);
      } finally {
        setLoading(false);
      }
    }, 180);

    return () => clearTimeout(t);
  }, [query]);

  // Close on outside click
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  // If initialQuery changes (e.g. coming back from a book with ?q=), trigger search
  useEffect(() => {
    if (initialQuery && initialQuery !== query) {
      setQuery(initialQuery);
    }
  }, [initialQuery]); // eslint-disable-line react-hooks/exhaustive-deps

  const hasResults = hits.length > 0;

  return (
    <div ref={containerRef} className="relative w-full max-w-2xl">
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => { if (hits.length > 0) setOpen(true); }}
          placeholder="Search across all texts — chapters, sections, topics..."
          className="w-full rounded-2xl border border-hairline bg-card pl-11 pr-10 py-3 text-[15px] placeholder:text-text-muted/70 focus:outline-none focus:border-accent/60"
        />
        <Search className="absolute left-4 top-4 h-4 w-4 text-text-muted" />
        {query && (
          <button
            onClick={() => {
              setQuery("");
              setHits([]);
              setOpen(false);
              inputRef.current?.focus();
            }}
            className="absolute right-3 top-3.5 rounded p-1 text-text-muted hover:text-text-main"
            aria-label="Clear search"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Results dropdown / panel */}
      {open && (query.trim().length >= 2) && (
        <div className="absolute z-50 mt-2 w-full rounded-2xl border border-hairline bg-card shadow-lg overflow-hidden">
          {loading && (
            <div className="px-4 py-3 text-sm text-text-muted">Searching…</div>
          )}

          {!loading && !hasResults && (
            <div className="px-4 py-4 text-sm text-text-muted">
              No matches for “{query}”. Try a topic, chapter name, or book title.
            </div>
          )}

          {!loading && hasResults && (
            <>
              <div className="px-4 pt-3 pb-1 text-[10px] uppercase tracking-[2px] text-text-muted border-b border-hairline">
                {hits.length} results across the library
              </div>
              <ul className="max-h-[420px] overflow-auto divide-y divide-hairline text-sm">
                {hits.map((hit, idx) => (
                  <li key={`${hit.bookId}-${hit.chapterId || "b"}-${hit.sectionId || idx}`}>
                    <Link
                      href={buildLink(hit, query)}
                      className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-accent/5 group"
                      onClick={() => setOpen(false)}
                    >
                      <div className="min-w-0 pr-2">
                        <div className="flex items-center gap-2">
                          <span className="inline-block rounded border border-hairline px-1.5 py-px text-[10px] text-text-muted tracking-wide">
                            {hit.kind}
                          </span>
                          <span className="truncate">{hitLabel(hit)}</span>
                        </div>
                        <div className="mt-0.5 text-xs text-text-muted truncate">
                          {hit.bookTitle}
                          {hit.chapterTitle ? ` • ${hit.chapterTitle}` : ""}
                        </div>
                      </div>
                      <ArrowRight className="h-4 w-4 text-accent opacity-70 group-hover:translate-x-0.5 transition" />
                    </Link>
                  </li>
                ))}
              </ul>
              <div className="border-t border-hairline px-4 py-2 text-[11px] text-text-muted bg-background/60">
                Click any result to open the text and jump to the match. Use your browser’s back button or the “Back to search” link on the book page.
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
