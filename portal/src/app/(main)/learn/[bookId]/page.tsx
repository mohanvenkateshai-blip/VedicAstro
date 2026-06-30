import Link from "next/link";
import { notFound } from "next/navigation";
import { BookOpen } from "lucide-react";
import { loadBook, parseMarkdownToSections } from "@/lib/books";
import { supabase } from "@/lib/supabase";
import { BookReaderClient } from "@/components/BookReaderClient";

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

  // Always attempt to load the full original markdown from the corpus-vault if we have a storagePath.
  // This ensures useful learning content even when graph_nodes extraction produced 0 rows for the source.
  let fullMarkdown: string | null = null;
  if (book.metadata.storagePath) {
    try {
      const { data: blob } = await supabase.storage
        .from('corpus-vault')
        .download(book.metadata.storagePath);
      if (blob) {
        fullMarkdown = await blob.text();
      }
    } catch {
      // fall back to nodes or message
    }
  }

  // Build per-chapter node content map (for the rare case we want to show raw graph nodes for a section)
  const chapterNodesMap: Record<string, any[]> = {};
  book.chapters.forEach((ch) => {
    chapterNodesMap[ch.id] = book.nodes.filter((n: any) => ch.nodeIds.includes(n.id));
  });

  // Default "all nodes" view (used when no full text at all)
  const allNodesView = book.nodes.length > 0 ? (
    <div className="space-y-8">
      {book.nodes.map((node: any, i: number) => (
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
      <div className="font-serif text-2xl mb-4">No detailed nodes extracted yet.</div>
      <p className="text-text-muted">
        The Knowledge Graph has {book.metadata.nodeCount} nodes for this text in total.
        Content here is exactly what was extracted during ingest.
      </p>
    </div>
  );

  // When we have the original full markdown, parse its headings to produce a real table of contents.
  // This is what fixes "Frontmatter" / "H1" garbage in handbooks like Ashtakavarga.
  // The source document's own structure ( # , ## , "1. Foo" ) becomes the left nav.
  let chaptersForReader = book.chapters;
  let mdSections: { id: string; title: string; content: string }[] | null = null;

  if (fullMarkdown) {
    const parsed = parseMarkdownToSections(fullMarkdown);
    if (parsed.chapters.length > 0) {
      chaptersForReader = parsed.chapters;
      mdSections = parsed.sections;
    }
  }

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

      <BookReaderClient
        chapters={chaptersForReader}
        fullMarkdown={fullMarkdown}
        defaultNodesContent={allNodesView}
        chapterNodes={chapterNodesMap}
        sections={mdSections}
      />

      <div className="mt-4 text-[10px] text-text-muted max-w-3xl">
        Left navigation is a table of contents derived from the source text (or Knowledge Graph groupings when no full text). Click to jump to that part.
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
