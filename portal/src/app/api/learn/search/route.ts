import { NextRequest, NextResponse } from "next/server";
import { getAllStructuredBooksSync, StructuredBook } from "@/lib/books";

export const runtime = "nodejs";

export type SearchHit = {
  bookId: string;
  bookTitle: string;
  chapterId?: string;
  chapterTitle?: string;
  sectionId?: string;
  sectionTitle?: string;
  kind: "book" | "chapter" | "section";
  score: number;
  // For navigation
  slug: string;
};

function scoreMatch(query: string, text: string): number {
  if (!text) return 0;
  const q = query.toLowerCase().trim();
  const t = text.toLowerCase();
  if (!q) return 0;
  if (t === q) return 100;
  if (t.startsWith(q)) return 85;
  if (t.includes(q)) return 70;
  // word boundary-ish
  const words = q.split(/\s+/);
  let bonus = 0;
  for (const w of words) {
    if (w.length > 2 && t.includes(w)) bonus += 8;
  }
  return Math.max(0, 40 + bonus);
}

function makeSlug(id: string, canonical?: string) {
  const base = id || canonical || "";
  return base.replace(/\s+/g, "_");
}

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const q = (searchParams.get("q") || "").trim();
  const limit = Math.min(parseInt(searchParams.get("limit") || "40", 10), 100);

  if (!q || q.length < 2) {
    return NextResponse.json({ hits: [] });
  }

  const books: StructuredBook[] = getAllStructuredBooksSync();

  const hits: SearchHit[] = [];

  for (const b of books) {
    const bookTitle = b.canonical_name || b.book_id;
    const slug = makeSlug(b.book_id, b.canonical_name);

    // Book title match
    const bookScore = scoreMatch(q, bookTitle);
    if (bookScore > 30) {
      hits.push({
        bookId: b.book_id,
        bookTitle,
        kind: "book",
        score: bookScore,
        slug,
      });
    }

    for (const ch of b.chapters || []) {
      const chScore = scoreMatch(q, ch.title);
      if (chScore > 25) {
        hits.push({
          bookId: b.book_id,
          bookTitle,
          chapterId: ch.id,
          chapterTitle: ch.title,
          kind: "chapter",
          score: chScore + 5, // chapters slightly preferred over book
          slug,
        });
      }

      for (const sec of ch.sections || []) {
        const secScore = scoreMatch(q, sec.title);
        if (secScore > 20) {
          hits.push({
            bookId: b.book_id,
            bookTitle,
            chapterId: ch.id,
            chapterTitle: ch.title,
            sectionId: sec.id,
            sectionTitle: sec.title,
            kind: "section",
            score: secScore + 10, // sections are very specific
            slug,
          });
        }
      }
    }
  }

  // Dedup + sort
  const seen = new Set<string>();
  const deduped: SearchHit[] = [];
  for (const h of hits.sort((a, b) => b.score - a.score)) {
    const key = `${h.bookId}|${h.chapterId || ""}|${h.sectionId || ""}`;
    if (seen.has(key)) continue;
    seen.add(key);
    deduped.push(h);
    if (deduped.length >= limit) break;
  }

  return NextResponse.json({ hits: deduped, query: q });
}
