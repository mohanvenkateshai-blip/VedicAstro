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
  nodes: GraphNodeRow[]; // all nodes for this book (used for per-chapter rendering)
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

  // Compute accurate node counts.
  // IMPORTANT: graph_nodes.source_file is usually the raw md filename (without .md),
  // while corpus_sources.canonical_name may be similar or slightly different.
  // We prefer the filename-derived key because that's how nodes were tagged during ingest.
  const results = await Promise.all(
    sources.map(async (src) => {
      const canonical = src.canonical_name;
      const fileKey = src.storage_path?.split("/").pop()?.replace(/\.md$/, "") ?? null;

      const candidates = [
        fileKey,                    // most likely for source_file in nodes (e.g. "Brihat_Parashara_Hora_Sastra_Vol_2")
        canonical,
        canonical?.replace(/\s+/g, "_"),
        canonical?.replace(/ /g, "_"),
      ].filter((k, i, arr) => k && arr.indexOf(k) === i) as string[];

      let count = 0;
      for (const key of candidates) {
        // Use ilike to be robust to minor differences in how source_file was recorded during extraction
        const { count: c } = await supabase
          .from("graph_nodes")
          .select("*", { count: "exact", head: true })
          .eq("graph_version", graphVersion)
          .ilike("source_file", `%${key}%`);
        if (c && c > 0) {
          count = c;
          break;
        }
      }

      return {
        id: fileKey ?? canonical,
        canonicalName: canonical,
        bookFamily: src.book_family,
        storagePath: src.storage_path,
        sha256: src.sha256,
        bytes: src.bytes,
        nodeCount: count || 0,
      };
    })
  );

  return results;
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

  const fileKey = source.storage_path?.split("/").pop()?.replace(/\.md$/, "") ?? null;

  // Try the most likely source_file values. Nodes are usually tagged with the md filename stem.
  const candidates = [
    fileKey,
    source.canonical_name,
    bookId,
    source.canonical_name?.replace(/\s+/g, "_"),
  ].filter((k, i, arr) => k && arr.indexOf(k) === i) as string[];

  let nodes: GraphNodeRow[] = [];
  for (const key of candidates) {
    // Use ilike for robustness against small differences in recorded source_file values
    const { data, error } = await supabase
      .from("graph_nodes")
      .select("id, graph_version, label, file_type, source_file, source_location, community, properties")
      .eq("graph_version", graphVersion)
      .ilike("source_file", `%${key}%`)
      .order("source_location")
      .limit(500);
    if (!error && data && data.length > 0) {
      nodes = data as GraphNodeRow[];
      break;
    }
  }

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

  // Sort chapters into logical book order.
  // Previous behavior used Map insertion order after lexical .order("source_location"),
  // which put "Chapter 12" / "Chapter 14" before "Chapter 3" (string sort).
  // Now we sort by the first number we can find in the title or sourceLocation.
  const getChapterNum = (c: Chapter): number => {
    const t = `${c.title} ${c.sourceLocation || ''}`;
    const m = t.match(/\b(\d+)\b/);
    if (m) return parseInt(m[1], 10);
    if (/frontmatter|preface|intro|dedication|main|h1/i.test(t)) return -100;
    return 100000;
  };

  chapters.sort((a, b) => {
    const na = getChapterNum(a);
    const nb = getChapterNum(b);
    if (na !== nb) return na - nb;
    return a.title.localeCompare(b.title, undefined, { numeric: true });
  });

  // Re-assign order indices after numeric sort so UI and consumers have a clean sequence
  chapters.forEach((c, i) => { c.order = i; });

  // Drop pure junk labels that the graph extractor sometimes emits for handbooks
  // (e.g. "Frontmatter", "H1") when there are other real sections.
  const junkExact = /^(frontmatter|h1|main|untitled|unknown)$/i;
  const cleaned = chapters.filter((c) => {
    const t = (c.title || '').trim();
    if (junkExact.test(t)) return false;
    return true;
  });
  if (cleaned.length > 0) {
    chapters.splice(0, chapters.length, ...cleaned);
    chapters.forEach((c, i) => { c.order = i; });
  }

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

  return { metadata, chapters, nodes };
}

/**
 * Load full content + nodes for a specific chapter.
 * Uses the nodes already loaded in loadBook (robust source_file matching) and filters by chapter.
 */
export async function getChapterContent(
  bookId: string,
  chapterId: string,
  graphVersion = DEFAULT_GRAPH_VERSION,
): Promise<ChapterContent> {
  const book = await loadBook(bookId, graphVersion);
  const chapter = book.chapters.find((c) => c.id === chapterId);
  if (!chapter) throw new Error(`Chapter not found: ${chapterId}`);

  const chapterNodes = book.nodes.filter((n) => chapter.nodeIds.includes(n.id));

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

export type MarkdownSection = {
  id: string;
  title: string;
  content: string;
};

/**
 * Parse a full markdown document into a usable table of contents + section blocks.
 * This is used to drive a real reader experience (nice headings, reliable jumps)
 * instead of whatever the graph node source_location decided to call "frontmatter".
 */
export function parseMarkdownToSections(md: string): { chapters: Chapter[]; sections: MarkdownSection[] } {
  if (!md || typeof md !== "string") return { chapters: [], sections: [] };

  const lines = md.split(/\r?\n/);
  const raw: Array<{ title: string; lines: string[] }> = [];

  let currTitle = "Start";
  let curr: string[] = [];

  const flush = () => {
    if (curr.length > 0 || raw.length === 0) {
      raw.push({ title: currTitle, lines: [...curr] });
    }
    curr = [];
  };

  for (const line of lines) {
    const h = line.match(/^(#{1,6})\s+(.+?)\s*$/);
    const num = !h && /^\s*(\d+[\.\)])\s+(.+?)\s*$/.exec(line);

    if (h || num) {
      flush();
      const headingText = h ? h[2] : (num ? num[2] : "");
      currTitle = (headingText || "").trim();
      curr = [line]; // keep the heading line inside the section
      continue;
    }
    curr.push(line);
  }
  flush();

  const sections: MarkdownSection[] = raw
    .map((r, i) => ({
      id: `sec-${i}`,
      title: r.title || `Section ${i + 1}`,
      content: r.lines.join("\n"),
    }))
    .filter((s) => s.content.trim().length > 0);

  let chapters: Chapter[] = sections.map((s, i) => ({
    id: s.id,
    title: s.title,
    order: i,
    sourceLocation: undefined,
    nodeIds: [],
  }));

  // Remove junky single-token titles that sometimes get parsed from bad first lines
  const junk = /^(frontmatter|h1|main|start|untitled|unknown|page\s*\d*)$/i;
  let filtered = chapters.filter((c) => !junk.test(c.title.trim()));

  // If the first remaining item looks like an overall book title (very long), drop it from the clickable TOC
  // so the first clickable is the first real section (e.g. "1. Foundations...")
  if (filtered.length > 1 && filtered[0].title.length > 55) {
    filtered = filtered.slice(1).map((c, i) => ({ ...c, order: i }));
  }

  if (filtered.length === 0) filtered = chapters;

  chapters = filtered.map((c, i) => ({ ...c, order: i }));

  return { chapters, sections };
}
