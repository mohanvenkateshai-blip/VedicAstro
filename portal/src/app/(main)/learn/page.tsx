import Link from "next/link";
import { BookOpen, ArrowRight } from "lucide-react";
import { listBooks } from "@/lib/books";

export default async function LearnPage() {
  let books: Awaited<ReturnType<typeof listBooks>> = [];
  try {
    books = await listBooks("newbooks-v1");
  } catch {
    books = [];
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 lg:py-14">
      {/* Hero */}
      <div className="max-w-3xl mb-12">
        <div className="inline-flex items-center gap-2 rounded-full border border-hairline px-3 py-1 text-xs tracking-[0.08em] text-text-muted mb-4">
          <BookOpen className="w-3.5 h-3.5" /> ŚĀSTRA SAṄGRAHA
        </div>
        <h1 className="font-display text-5xl lg:text-6xl tracking-[-0.02em] text-balance mb-4">
          The classical library
        </h1>
        <p className="text-lg text-text-muted max-w-2xl">
          All texts loaded directly from the Knowledge Graph (newbooks-v1). Real nodes, real content.
        </p>
      </div>

      {/* Real Book Library from KG */}
      <section aria-labelledby="library-heading" className="mb-16">
        <div className="flex items-end justify-between mb-6">
          <div>
            <h2 id="library-heading" className="font-display text-3xl tracking-[-0.01em]">Book Library</h2>
            <p className="text-sm text-text-muted mt-1 flex items-center gap-2">
              {books.length > 0 ? `${books.length} texts from Knowledge Graph • newbooks-v1` : "Loading texts from Knowledge Graph..."}
              {books.length > 0 && (
                <span className="inline-flex items-center rounded border border-hairline px-1.5 py-0.5 text-[10px] tracking-[0.5px] text-text-muted/80">61 books • chapter-precise</span>
              )}
            </p>
          </div>
        </div>

        {books.length === 0 ? (
          <div className="rounded-2xl border border-hairline bg-card p-8 text-text-muted">
            No books found in the current graph. Ensure corpus_sources and graph_nodes are populated for newbooks-v1.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {books.map((book) => {
              const slug = book.id || book.canonicalName?.toLowerCase().replace(/\s+/g, "-");
              const isJaimini = /jaimini/i.test(book.canonicalName || "");
              return (
                <article
                  key={book.id}
                  className="group flex flex-col rounded-2xl border border-hairline bg-card p-7 transition-colors hover:border-accent/40"
                >
                  <div className="flex-1">
                    <h3 className="font-display text-2xl tracking-[-0.01em] leading-tight pr-2">{book.canonicalName}</h3>
                    {book.bookFamily && <div className="mt-1.5 text-sm text-accent font-medium">{book.bookFamily}</div>}
                    <p className="mt-4 text-[15px] leading-relaxed text-text-muted line-clamp-3">
                      {book.storagePath ? `Source: ${book.storagePath.split("/").pop()}` : "Classical text from the Vedic corpus."}
                    </p>
                  </div>

                  <div className="mt-6 pt-5 border-t border-hairline flex items-center justify-between text-sm">
                    <span className="font-mono text-xs uppercase tracking-[0.08em] text-text-muted">
                      {(book.nodeCount ?? 0) > 0 ? `${book.nodeCount} nodes` : 'Full text available'}
                      {book.chapterCount ? ` • ${book.chapterCount} chapters` : ""}
                    </span>
                    <Link
                      href={isJaimini ? "/learn/jaimini" : `/learn/${slug}`}
                      className="inline-flex items-center gap-1 text-accent hover:text-accent-strong transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded-md px-2 py-0.5 -mr-2"
                    >
                      Open text <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      {/* Note */}
      <div className="text-xs text-text-muted max-w-2xl">
        Structured books use the authoritative chapter/section TOC from the Gyan sources (with KE node provenance via patch).
        Node-only books fall back gracefully. Click chapters to jump; deep links supported (?chapter=...&amp;section=...).
      </div>
    </div>
  );
}
