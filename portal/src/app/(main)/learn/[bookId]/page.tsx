import Link from "next/link";
import { notFound } from "next/navigation";
import { BookOpen } from "lucide-react";
import {
  loadBook,
  resolveStructuredBook,
  chaptersFromStructured,
  parseMarkdownToSections,
  sectionsFromStructured,
  loadNodeChapterPatch,
  enrichChaptersWithNodeIds,
  buildNodeProvenanceMap,
} from "@/lib/books";
import { supabase } from "@/lib/supabase";
import { BookReaderClient } from "@/components/BookReaderClient";

type SP = Record<string, string | string[] | undefined>;

interface BookReaderProps {
  bookId: string;
  searchParams?: SP;
}

async function BookReader({ bookId, searchParams = {} }: BookReaderProps) {
  let book;
  try {
    book = await loadBook(bookId);
  } catch {
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

  // Default nodes view (rare) — will be replaced after provenance is known for richer cards.
  let allNodesView: React.ReactNode = (
    <div>
      <div className="font-serif text-2xl mb-4">No detailed nodes extracted yet.</div>
      <p className="text-text-muted">
        The Knowledge Graph has {book.metadata.nodeCount} nodes for this text in total.
        Content here is exactly what was extracted during ingest.
      </p>
    </div>
  );

  const fileKey = book.metadata.storagePath?.split("/").pop()?.replace(/\.md$/, "") ?? null;

  // === USE THE STRUCTURED BOOK AS THE PRIMARY AUTHORITATIVE TOC ===
  let chaptersForReader = book.chapters;
  let mdSections: { id: string; title: string; content: string }[] | null = null;
  let usingStructured = book.chapters.some((c) => c.properties?.structured === true);

  const structured =
    (await resolveStructuredBook(bookId, book.metadata.canonicalName, fileKey, book.metadata.id)) ??
    null;

  if (structured?.chapters?.length) {
    usingStructured = true;
    chaptersForReader = chaptersFromStructured(structured);
    // Wire KE-owned mapping: attach the nodes that belong to each clean chapter.
    // Load patch for the specific book (per-book patch-*.json if present, else global).
    const patchForEnrich = loadNodeChapterPatch(bookId) || loadNodeChapterPatch(book.metadata.canonicalName) || loadNodeChapterPatch();
    chaptersForReader = enrichChaptersWithNodeIds(chaptersForReader, bookId, patchForEnrich);
    if (book.metadata.canonicalName && chaptersForReader.every((c) => (c.nodeIds || []).length === 0)) {
      chaptersForReader = enrichChaptersWithNodeIds(chaptersForReader, book.metadata.canonicalName, patchForEnrich);
    }
    // Always prefer slicing the real source using the line ranges from structured data.
    // This powers clean chapter/section blocks on the right + reliable id-based jumps.
    if (fullMarkdown) {
      const sliced = sectionsFromStructured(structured, fullMarkdown);
      if (sliced.length > 0) mdSections = sliced;
    }
  } else if (fullMarkdown) {
    // Fallback to parsing the markdown itself (no authoritative structured file)
    const parsed = parseMarkdownToSections(fullMarkdown);
    if (parsed.chapters.length > 0) {
      chaptersForReader = parsed.chapters;
      mdSections = parsed.sections;
    }
  }

  // Load the full patch for provenance display ("Sourced from: ...") and build nodeId → details map.
  // Prefer the patch specific to this book (supports per-book patches like patch-Ashtakavarga_*.json).
  const patch = loadNodeChapterPatch(bookId) || loadNodeChapterPatch(book.metadata.canonicalName) || loadNodeChapterPatch();
  const nodeProvMap = buildNodeProvenanceMap(patch, bookId) || buildNodeProvenanceMap(patch, book.metadata.canonicalName);

  const attachProvenance = (n: any) => { // eslint-disable-line @typescript-eslint/no-explicit-any
    const prov = nodeProvMap[n.id];
    return prov ? { ...n, _provenance: prov } : n;
  };

  // Build the per-chapter node map from the final (enriched) chaptersForReader + attach provenance.
  const chapterNodesMap: Record<string, any[]> = {}; // eslint-disable-line @typescript-eslint/no-explicit-any
  book.chapters.forEach((ch) => {
    chapterNodesMap[ch.id] = book.nodes.filter((n: any) => ch.nodeIds.includes(n.id)).map(attachProvenance); // eslint-disable-line @typescript-eslint/no-explicit-any
  });
  chaptersForReader.forEach((ch) => {
    const matched = book.nodes.filter((n: any) => (ch.nodeIds || []).includes(n.id)).map(attachProvenance); // eslint-disable-line @typescript-eslint/no-explicit-any
    if (matched.length > 0) chapterNodesMap[ch.id] = matched;
  });

  // Deep link targets (e.g. /learn/<bookId>?chapter=ch-3&section=ch-3-sec-foo)
  const initialChapter = typeof searchParams?.chapter === "string" ? searchParams.chapter : null;
  const initialSection = typeof searchParams?.section === "string" ? searchParams.section : null;

  // Rebuild a provenance-aware default nodes view (used when no full text or explicit node mode).
  const enrichedDefaultNodes = book.nodes.map(attachProvenance);
  allNodesView = enrichedDefaultNodes.length > 0 ? (
    <div className="space-y-8">
      {enrichedDefaultNodes.map((node: any, i: number) => { // eslint-disable-line @typescript-eslint/no-explicit-any
        const prov = (node as any)._provenance as { hierarchy_path?: string; method?: string; confidence?: number } | undefined; // eslint-disable-line @typescript-eslint/no-explicit-any
        return (
          <div key={node.id || i} className="border-l-2 border-accent/40 pl-4">
            {node.source_location && (
              <div className="text-[10px] uppercase tracking-[3px] text-text-muted mb-1">{node.source_location}</div>
            )}
            <div className="font-serif text-2xl leading-tight tracking-[-0.4px] text-text-main">
              {node.label || "(no label)"}
            </div>
            {prov?.hierarchy_path && (
              <div className="mt-1 text-[11px] text-accent/90">
                From: <span className="font-medium">{prov.hierarchy_path}</span>
                {prov.method ? ` (mapped via ${prov.method}` : ""}
                {typeof prov.confidence === "number" ? ` conf ${prov.confidence})` : prov.method ? ")" : ""}
              </div>
            )}
            {node.properties && Object.keys(node.properties).length > 0 && (
              <div className="mt-3 text-sm text-text-muted">
                {Object.entries(node.properties).slice(0, 5).map(([k, v]: [string, any]) => ( // eslint-disable-line @typescript-eslint/no-explicit-any
                  <div key={k} className="mb-1">
                    <span className="font-mono text-xs text-accent">{k}:</span> {typeof v === "string" ? v : JSON.stringify(v)}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
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
          {usingStructured
            ? `${chaptersForReader.filter((c) => ((c.properties?.level as number) || 1) === 1).length} chapters (structured) • ${book.metadata.nodeCount} nodes`
            : `${book.metadata.nodeCount} nodes`} • Source: {book.metadata.storagePath?.split("/").pop() || "Knowledge Graph"} • newbooks-v1
          {usingStructured && <span className="ml-2 rounded border border-hairline px-1.5 py-0.5 text-[10px] tracking-[0.5px]">chapter-precise</span>}
        </p>
      </div>

      <BookReaderClient
        chapters={chaptersForReader}
        fullMarkdown={fullMarkdown}
        defaultNodesContent={allNodesView}
        chapterNodes={chapterNodesMap}
        sections={mdSections}
        initialChapter={initialChapter}
        initialSection={initialSection}
        nodeProvenance={nodeProvMap}
      />

      <div className="mt-4 text-[10px] text-text-muted max-w-3xl">
        Left nav = structured chapters/sections (stable ids, deep links). Right side = full chapter content (chapter ranges) or section slices + embedded images (corpus-vault / local refs with fallbacks). Nodes carry patch provenance.
      </div>
    </div>
  );
}

export default async function BookPage({
  params,
  searchParams,
}: {
  params: Promise<{ bookId: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { bookId } = await params;
  const sp = await searchParams;
  const decodedId = decodeURIComponent(bookId);
  return <BookReader bookId={decodedId} searchParams={sp} />;
}
