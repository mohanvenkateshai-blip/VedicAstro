"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Search, X } from "lucide-react";

type Hit = {
  bookId: string;
  bookTitle: string;
  chapterId?: string;
  chapterTitle?: string;
  sectionId?: string;
  sectionTitle?: string;
  kind: "book" | "chapter" | "section";
  slug: string;
};

function buildLink(hit: Hit, q: string) {
  const p = new URLSearchParams();
  if (hit.chapterId) p.set("chapter", hit.chapterId);
  if (hit.sectionId) p.set("section", hit.sectionId);
  if (q) p.set("q", q);
  const qs = p.toString();
  return `/learn/${hit.slug}${qs ? "?" + qs : ""}`;
}

/** Compact masthead search. v1 searches the classical library (/api/learn/search);
 *  cross-entity (charts, dashboard) results can be unioned in later. */
export function GlobalSearch() {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const q = query.trim();
    // Short queries clear results on the same debounced path as fetches, so
    // the effect body itself never sets state synchronously.
    if (q.length < 2) {
      const t = setTimeout(() => {
        setHits([]);
        setOpen(false);
      }, 0);
      return () => clearTimeout(t);
    }
    const t = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/learn/search?q=${encodeURIComponent(q)}&limit=8`);
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

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  // Inline input only from lg up — tablet mastheads overflowed the viewport;
  // below lg, search lives on the pages themselves.
  return (
    <div ref={ref} className="relative hidden lg:block">
      <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-text-muted" />
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => hits.length > 0 && setOpen(true)}
        placeholder="Search the library…"
        aria-label="Search"
        className="w-48 rounded-lg border border-hairline bg-card py-2 pl-9 pr-8 text-sm placeholder:text-text-muted/70 transition-[width] focus:w-64 focus:outline-none focus:border-accent/60"
      />
      {query && (
        <button
          onClick={() => {
            setQuery("");
            setOpen(false);
          }}
          aria-label="Clear search"
          className="absolute right-2 top-2 rounded p-0.5 text-text-muted hover:text-text-main"
        >
          <X className="h-4 w-4" />
        </button>
      )}

      {open && query.trim().length >= 2 && (
        <div className="absolute right-0 z-50 mt-2 w-80 rounded-2xl border border-hairline bg-card shadow-lg overflow-hidden">
          {loading && <div className="px-4 py-3 text-sm text-text-muted">Searching…</div>}
          {!loading && hits.length === 0 && (
            <div className="px-4 py-4 text-sm text-text-muted">No matches for “{query}”.</div>
          )}
          {!loading && hits.length > 0 && (
            <ul className="max-h-[360px] divide-y divide-hairline overflow-auto text-sm">
              {hits.map((h, i) => (
                <li key={`${h.bookId}-${h.chapterId || "b"}-${h.sectionId || i}`}>
                  <Link
                    href={buildLink(h, query)}
                    onClick={() => setOpen(false)}
                    className="block px-4 py-2.5 hover:bg-accent/5"
                  >
                    <span className="mr-2 inline-block rounded border border-hairline px-1.5 py-px text-[10px] text-text-muted">
                      {h.kind}
                    </span>
                    <span className="text-text-main">
                      {h.sectionTitle || h.chapterTitle || h.bookTitle}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-text-muted">
                      {h.bookTitle}
                      {h.chapterTitle ? ` • ${h.chapterTitle}` : ""}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
