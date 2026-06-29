import "server-only";
import { supabase } from "@/lib/supabase";
import { DEFAULT_GRAPH_VERSION, GraphNodeRow, searchGraphNodes, listCorpusSources, CorpusSource } from "./corpus";

/**
 * Book Data Layer
 *
 * Clean abstraction for loading any classical text / book from the Knowledge Graph
 * (graph_nodes + corpus_sources) and original Gyan markdown sources.
 * Designed to be fully compatible with the Python KnowledgeEngine data model.
 */

export type BookMetadata = {
  id: string; // source_file or canonical slug
  canonicalName: string;
  bookFamily: string | null;
  storagePath: string | null;
  sha256: string | null;
  bytes: number | null;
  chapterCount?: number;
  nodeCount?: number;
  properties?: Record<string, unknown>;
};

export type Chapter = {
  id: string; // node id or section slug
  title: string;
  order: number;
  sourceLocation?: string;
  nodeIds: string[]; // associated graph nodes
  properties?: Record<string, unknown>;
};

export type BookContent = {
  metadata: BookMetadata;
  chapters: Chapter[];
  // Raw content can be fetched on demand via getChapterContent
};

export type ChapterContent = {
  chapterId: string;
  title: string;
  markdown: string;
  verses?: Array<{ number: number; text: string; translation?: string }>;
  nodes: GraphNodeRow[];
};

/**
 * List all available books from corpus_sources, enriched with graph stats.
 * Compatible with KnowledgeEngine's corpus_sources table.
 */
export async function listBooks(graphVersion = DEFAULT_GRAPH_VERSION): Promise<BookMetadata[]> {
  const sources = await listCorpusSources();

  // Enrich with node counts per source_file
  const { data: nodeCounts } = await supabase
    .from("graph_nodes")
    .select("source_file", { count: "exact", head: false })
    .eq("graph_version", graphVersion);

  const countMap = new Map<string, number>();
  for (const row of nodeCounts ?? []) {
    const sf = (row as any).source_file as string | null;
    if (sf) countMap.set(sf, (countMap.get(sf) ?? 0) + 1);
  }

  return sources.map((src) => ({
    id: src.storage_path?.split("/").pop()?.replace(/\.md$/, "") ?? src.canonical_name,
    canonicalName: src.canonical_name,
    bookFamily: src.book_family,
    storagePath: src.storage_path,
    sha256: src.sha256,
    bytes: src.bytes,
    nodeCount: countMap.get(src.canonical_name) ?? 0,
  }));
}

/**
 * Load a book's structure (metadata + chapters) from the Knowledge Graph.
 * Chapters are inferred from nodes that have source_location or section-like labels.
 * This mirrors how KnowledgeEngine / gyan-corpus-extract.py structures books.
 */
export async function loadBook(
  bookId: string,
  graphVersion = DEFAULT_GRAPH_VERSION,
): Promise<BookContent> {
  const sources = await listCorpusSources();
  const source = sources.find(
    (s) => s.canonical_name === bookId || s.storage_path?.includes(bookId),
  );

  if (!source) {
    throw new Error(`Book not found: ${bookId}`);
  }

  // Fetch all nodes for this source
  const nodes = await searchGraphNodes({
    graphVersion,
    sourceFile: source.canonical_name,
    limit: 500,
  });

  // Group into chapters by source_location prefix or label patterns
  const chapterMap = new Map<string, { title: string; nodes: GraphNodeRow[]; order: number }>();

  nodes.forEach((node, idx) => {
    const loc = node.source_location ?? "frontmatter";
    const chapterKey = loc.split(":")[0] || "main";
    if (!chapterMap.has(chapterKey)) {
      chapterMap.set(chapterKey, {
        title: chapterKey.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
        nodes: [],
        order: chapterMap.size,
      });
    }
    chapterMap.get(chapterKey)!.nodes.push(node);
  });

  const chapters: Chapter[] = Array.from(chapterMap.entries()).map(([key, val], i) => ({
    id: key,
    title: val.title,
    order: i,
    sourceLocation: key,
    nodeIds: val.nodes.map((n) => n.id),
    properties: { nodeCount: val.nodes.length },
  }));

  const metadata: BookMetadata = {
    id: bookId,
    canonicalName: source.canonical_name,
    bookFamily: source.book_family,
    storagePath: source.storage_path,
    sha256: source.sha256,
    bytes: source.bytes,
    chapterCount: chapters.length,
    nodeCount: nodes.length,
  };

  return { metadata, chapters };
}

/**
 * Load full content + nodes for a specific chapter.
 * In production this would fetch markdown from corpus-vault bucket via signed URL
 * or from corpus_chunks table. Here we return the graph nodes as the structured content.
 */
export async function getChapterContent(
  bookId: string,
  chapterId: string,
  graphVersion = DEFAULT_GRAPH_VERSION,
): Promise<ChapterContent> {
  const book = await loadBook(bookId, graphVersion);
  const chapter = book.chapters.find((c) => c.id === chapterId);
  if (!chapter) throw new Error(`Chapter not found: ${chapterId}`);

  const nodes = await searchGraphNodes({
    graphVersion,
    sourceFile: book.metadata.canonicalName,
    limit: 200,
  });

  const chapterNodes = nodes.filter((n) => chapter.nodeIds.includes(n.id));

  return {
    chapterId,
    title: chapter.title,
    markdown: `# ${chapter.title}\n\n(Full markdown content loaded from Gyan source or corpus_chunks on demand.)`,
    nodes: chapterNodes,
  };
}

/**
 * Compatibility helper: returns the same node shape KnowledgeEngine uses internally.
 */
export async function getBookNodes(bookId: string, graphVersion = DEFAULT_GRAPH_VERSION) {
  const sources = await listCorpusSources();
  const source = sources.find((s) => s.canonical_name.includes(bookId));
  if (!source) return [];
  return searchGraphNodes({ graphVersion, sourceFile: source.canonical_name, limit: 1000 });
}
