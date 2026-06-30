import Link from "next/link";
import { notFound } from "next/navigation";
import { BookOpen } from "lucide-react";
import { loadBook, getChapterContent } from "@/lib/books";

interface BookReaderProps {
  bookId: string;
}

async function BookReader({ bookId }: BookReaderProps) {
  let book;
  try {
    book = await loadBook(bookId);
  } catch (e) {
    notFound();
  }

  // Load content for the first chapter by default (or we can make it interactive client-side later)
  let chapterContent = null;
  if (book.chapters.length > 0) {
    try {
      chapterContent = await getChapterContent(bookId, book.chapters[0].id);
    } catch {}
  }

  const nodesToShow = chapterContent?.nodes ?? [];

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <div className="mb-8">
        <Link href="/learn" className="text-sm text-text-muted hover:text-text-main">← Back to library</Link>
        <div className="mt-3 flex items-center gap-3">
          <BookOpen className="h-6 w-6 text-accent" />
          <h1 className="font-display text-4xl tracking-tight">{book.metadata.canonicalName}</h1>
        </div>
        {book.metadata.bookFamily && (
          <p className="text-sm text-accent mt-1">{book.metadata.bookFamily}</p>
        )}
        <p className="text-xs text-text-muted mt-1">
          {book.metadata.nodeCount} nodes • Source: {book.metadata.storagePath?.split("/").pop() || "Knowledge Graph"} • newbooks-v1
        </p>
      </div>

      <div className="grid lg:grid-cols-5 gap-6">
        {/* Chapters sidebar (from graph node grouping) */}
        <div className="lg:col-span-2">
          <div className="sticky top-6 rounded-2xl border border-hairline bg-surface p-4">
            <div className="text-xs uppercase tracking-widest text-text-muted mb-3">Chapters (from graph)</div>
            <div className="space-y-1 text-sm max-h-[60vh] overflow-auto">
              {book.chapters.length > 0 ? (
                book.chapters.map((ch, idx) => (
                  <div key={ch.id} className="px-3 py-2 rounded-lg border border-hairline/60">
                    <div className="font-medium">{ch.title}</div>
                    <div className="text-[10px] text-text-muted">{ch.nodeIds.length} nodes • {ch.sourceLocation}</div>
                  </div>
                ))
              ) : (
                <div className="text-text-muted text-sm">No chapter grouping found. All content in main section.</div>
              )}
            </div>
          </div>
        </div>

        {/* Main content area: show nodes from first chapter (or all if none) */}
        <div className="lg:col-span-3">
          <div className="rounded-3xl border border-hairline bg-surface p-8 min-h-[420px]">
            {nodesToShow.length > 0 ? (
              <div className="space-y-8">
                {nodesToShow.map((node: any, i: number) => (
                  <div key={node.id || i} className="border-l-2 border-accent/40 pl-4">
                    {node.source_location && (
                      <div className="text-[10px] uppercase tracking-[3px] text-text-muted mb-1">{node.source_location}</div>
                    )}
                    <div className="font-serif text-2xl leading-tight tracking-[-0.4px] text-text-main">
                      {node.label || "(no label)"}
                    </div>
                    {node.properties && Object.keys(node.properties).length > 0 && (
                      <div className="mt-3 text-sm text-text-muted">
                        {Object.entries(node.properties).slice(0, 5).map(([k, v]: [string, any]) => (
                          <div key={k} className="mb-1">
                            <span className="font-mono text-xs text-accent">{k}:</span> {typeof v === "string" ? v : JSON.stringify(v)}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div>
                <div className="font-serif text-2xl mb-4">No detailed nodes extracted for this section yet.</div>
                <p className="text-text-muted">
                  The Knowledge Graph has {book.metadata.nodeCount} nodes for this text in total.
                  Content here is exactly what was extracted during ingest (headings, concepts, references).
                  Full original prose lives in the source file synced to the corpus vault.
                </p>
              </div>
            )}
          </div>

          <div className="mt-4 text-[10px] text-text-muted">
            All content shown is pulled live from the Knowledge Graph (graph_nodes) for this source. 
            It reflects the current state of extraction — some texts are rich, others are chapter/page oriented.
          </div>
        </div>
      </div>
    </div>
  );
}

export default async function BookPage({ params }: { params: Promise<{ bookId: string }> }) {
  const { bookId } = await params;
  // Decode in case of URL encoding
  const decodedId = decodeURIComponent(bookId);
  return <BookReader bookId={decodedId} />;
}
