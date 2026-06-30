import "server-only";
import { supabase } from "@/lib/supabase";
import { DEFAULT_GRAPH_VERSION, GraphNodeRow, searchGraphNodes, listCorpusSources, CorpusSource } from "./corpus";
import fs from "fs";
import path from "path";

const STRUCTURED_DIR = path.join(process.cwd(), "..", "knowledge-graph", "structured"); // from portal/ to root
const PATCHES_DIR = path.join(process.cwd(), "..", "knowledge-graph", "patches");
const PATCH_PATH = path.join(PATCHES_DIR, "node-chapter-map.json");

export type StructuredSection = {
  id: string;
  title: string;
  level: number;
  start_line?: number;
  end_line?: number;
  content_preview?: string;
};

export type StructuredChapter = {
  id: string;
  number?: string | null;
  title: string;
  level: number;
  start_line?: number;
  end_line?: number;
  sections?: StructuredSection[];
  content_preview?: string;
};

export type StructuredBook = {
  book_id: string;
  canonical_name: string;
  source_file: string;
  chapters: StructuredChapter[];
  toc?: any[];
  total_chapters?: number;
};

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
 *
 * WHY THIS CODE LOOKS "HACKY":
 * The Knowledge Graph was built in waves (CoreJyothisha PDFs via OCR + LLM, then loose newbooks MDs).
 * During extraction, nodes were tagged with whatever `source_file` the script saw at the time
 * (often the basename of the file on disk during that run).
 * Later, corpus_sources got "canonical_name" from the nicer titles or storage paths.
 *
 * Result: for many books, source_file != canonical_name.
 * This caused months of "0 nodes" in the Learn library.
 *
 * We now do multi-candidate + ilike fallback here so the UI is reliable.
 * Long-term fix belongs in the ingest pipeline (normalize source_file at promotion time).
 *
 * See also: knowledge-graph/KNOWLEDGE_CATALOG.md for the human view of the library.
 */
export async function listBooks(graphVersion = DEFAULT_GRAPH_VERSION): Promise<BookMetadata[]> {
  const sources = await listCorpusSources();

  // Compute accurate node counts.
  // See the big comment above for why we need this resilience.
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

      const structured = loadStructuredBook(fileKey || "") || loadStructuredBook(canonical || "");
      const chapterCount = structured?.chapters?.length || structured?.total_chapters || 0;

      return {
        id: fileKey ?? canonical,
        canonicalName: canonical,
        bookFamily: src.book_family,
        storagePath: src.storage_path,
        sha256: src.sha256,
        bytes: src.bytes,
        nodeCount: count || 0,
        chapterCount: chapterCount || undefined,
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

  // === AUTHORITATIVE STRUCTURED CHAPTERS (from build_structured_library.py) ===
  // This is the primary, clean, "organised from the beginning" TOC.
  // It comes from parsing the real Gyan source markdown with proper heading/numbered-section logic.
  // We prefer this over the weak graph node source_location (which produced "frontmatter", "H1", bad order).
  const structured = loadStructuredBook(bookId) || loadStructuredBook(source.canonical_name) || loadStructuredBook(fileKey || "");
  let chapters: Chapter[] = [];

  if (structured && structured.chapters && structured.chapters.length > 0) {
    chapters = chaptersFromStructured(structured);
  } else {
    // Legacy fallback: build from nodes (the old bad path)
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

    chapters = Array.from(chapterMap.entries()).map(([key, val], i) => ({
      id: key,
      title: val.title,
      order: i,
      sourceLocation: key,
      nodeIds: val.nodes.map((n) => n.id),
      properties: { nodeCount: val.nodes.length },
    }));

    // (old numeric sort + junk filter code would go here if needed)
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
    chapters.forEach((c, i) => { c.order = i; });

    const junkExact = /^(frontmatter|h1|main|untitled|unknown)$/i;
    const cleaned = chapters.filter((c) => !junkExact.test((c.title || '').trim()));
    if (cleaned.length > 0) {
      chapters.splice(0, chapters.length, ...cleaned);
      chapters.forEach((c, i) => { c.order = i; });
    }
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
 * Load the authoritative structured book (chapters, sections, titles) produced by
 * scripts/build_structured_library.py.
 * This is the "organised from the beginning" representation the user demanded.
 * Falls back to null if not present.
 */
export function loadStructuredBook(bookId: string): StructuredBook | null {
  try {
    const candidates = [
      path.join(STRUCTURED_DIR, `${bookId}.json`),
      path.join(STRUCTURED_DIR, `${bookId.replace(/\s+/g, "_")}.json`),
    ];
    for (const p of candidates) {
      if (fs.existsSync(p)) {
        const raw = fs.readFileSync(p, "utf8");
        return JSON.parse(raw) as StructuredBook;
      }
    }
    // fuzzy scan
    if (fs.existsSync(STRUCTURED_DIR)) {
      const files = fs.readdirSync(STRUCTURED_DIR).filter(f => f.endsWith(".json"));
      for (const f of files) {
        const full = path.join(STRUCTURED_DIR, f);
        const data = JSON.parse(fs.readFileSync(full, "utf8")) as StructuredBook;
        if (
          data.book_id === bookId ||
          data.canonical_name?.toLowerCase().includes(bookId.toLowerCase()) ||
          data.source_file?.includes(bookId)
        ) {
          return data;
        }
      }
    }
  } catch {}
  return null;
}

/**
 * Convert structured chapters into the internal Chapter shape used by the reader.
 * Emits chapters at their level, and appends nested sections as subsequent entries
 * with incremented level so the sidebar can render visual hierarchy (indent) while
 * staying compatible with the flat Chapter[] prop.
 */
export function chaptersFromStructured(sb: StructuredBook): Chapter[] {
  const out: Chapter[] = [];
  (sb.chapters || []).forEach((ch) => {
    out.push({
      id: ch.id,
      title: ch.title,
      order: out.length,
      sourceLocation: ch.number ? `Chapter ${ch.number}` : undefined,
      nodeIds: [],
      properties: { level: ch.level ?? 1, structured: true, hasSections: !!(ch.sections && ch.sections.length), start_line: ch.start_line, end_line: ch.end_line },
    });
    (ch.sections || []).forEach((sec) => {
      out.push({
        id: sec.id,
        title: sec.title,
        order: out.length,
        sourceLocation: undefined,
        nodeIds: [],
        properties: { level: sec.level ?? 2, structured: true, parentChapter: ch.id, start_line: (sec as any).start_line, end_line: (sec as any).end_line },
      });
    });
  });
  return out;
}

export type NodeProvenance = {
  chapter_id?: string;
  section_id?: string | null;
  hierarchy_path?: string;
  method?: string;
  confidence?: number;
  matched_on?: string;
};

/**
 * Load the KE-owned node→chapter mapping patch (non-destructive sidecar produced by map_nodes_to_structured.py).
 * Returns the full patch so callers can both enrich nodeIds and display provenance.
 * If bookId provided, prefers per-book patch-*.json when present (e.g. for Ashtakavarga).
 */
export function loadNodeChapterPatch(bookId?: string): { patches?: Array<{ node_id: string; chapter_id: string; section_id?: string | null; book_id?: string; hierarchy_path?: string; method?: string; confidence?: number; matched_on?: string }> } | null {
  try {
    if (bookId) {
      const variants = [
        bookId,
        bookId.replace(/\s+/g, "_"),
        bookId.replace(/ /g, "_"),
      ].filter((v, i, a) => v && a.indexOf(v) === i);
      for (const v of variants) {
        const perBookPath = path.join(PATCHES_DIR, `patch-${v}.json`);
        if (fs.existsSync(perBookPath)) {
          const raw = fs.readFileSync(perBookPath, "utf8");
          return JSON.parse(raw);
        }
      }
      // fuzzy scan for per-book patches by content
      if (fs.existsSync(PATCHES_DIR)) {
        const files = fs.readdirSync(PATCHES_DIR).filter((f) => f.startsWith("patch-") && f.endsWith(".json"));
        for (const f of files) {
          const full = path.join(PATCHES_DIR, f);
          try {
            const data = JSON.parse(fs.readFileSync(full, "utf8"));
            const bks = (data.books || []) as string[];
            const bid = (data as any).book_id || "";
            if (bks.includes(bookId) || bid === bookId || bks.some((b) => b.toLowerCase().includes(bookId.toLowerCase())) || bid.toLowerCase().includes(bookId.toLowerCase())) {
              return data;
            }
          } catch {}
        }
      }
    }
    if (fs.existsSync(PATCH_PATH)) {
      const raw = fs.readFileSync(PATCH_PATH, "utf8");
      return JSON.parse(raw);
    }
  } catch {}
  return null;
}

/**
 * Build a lookup from node_id → provenance details for a specific book (or all if no bookId).
 * Used to render "Sourced from: <hierarchy_path> (method: X, conf: Y)" on nodes.
 */
export function buildNodeProvenanceMap(
  patch: ReturnType<typeof loadNodeChapterPatch> | null,
  bookId?: string
): Record<string, NodeProvenance> {
  const map: Record<string, NodeProvenance> = {};
  if (!patch?.patches?.length) return map;
  const norm = (s: string) => (s || "").toLowerCase().replace(/\s+/g, "_");
  const bookKey = bookId ? norm(bookId) : null;
  for (const p of patch.patches) {
    if (!p.node_id) continue;
    if (bookKey) {
      const bid = norm(p.book_id || "");
      if (bid && !bid.includes(bookKey) && bookKey !== bid) continue;
    }
    map[p.node_id] = {
      chapter_id: p.chapter_id,
      section_id: p.section_id ?? null,
      hierarchy_path: p.hierarchy_path,
      method: p.method,
      confidence: p.confidence,
      matched_on: p.matched_on,
    };
  }
  return map;
}

/**
 * Given chapters derived from structured + the patch, attach the real nodeIds.
 * This is how the Learn reader receives "clean chapter tree + the KE nodes that belong to each chapter".
 */
export function enrichChaptersWithNodeIds(chapters: Chapter[], bookId: string, patch: ReturnType<typeof loadNodeChapterPatch>): Chapter[] {
  if (!patch || !patch.patches || patch.patches.length === 0) return chapters;
  const byChapter = new Map<string, string[]>();
  const norm = (s: string) => (s || "").toLowerCase().replace(/\s+/g, "_");
  const bookKey = norm(bookId);
  for (const p of patch.patches) {
    const bid = norm(p.book_id || "");
    if (!bid || (!bid.includes(bookKey) && bookKey !== bid)) continue;
    const arr = byChapter.get(p.chapter_id) || [];
    if (p.node_id) arr.push(p.node_id);
    byChapter.set(p.chapter_id, arr);
  }
  return chapters.map((ch) => ({
    ...ch,
    nodeIds: byChapter.get(ch.id) || ch.nodeIds || [],
  }));
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

/**
 * Optional: fetch the KE-owned structured book (chapter tree + per-chapter nodes)
 * via the CVCE proxy. Falls back to null if the endpoint is not reachable.
 * Use this when you want the server component to ask the authoritative KnowledgeEngine
 * instead of (or in addition to) reading the JSON files on disk.
 */
export async function fetchStructuredBookFromKE(bookId: string): Promise<any | null> {
  try {
    const res = await fetch(`/api/cvce/knowledge/structured/${encodeURIComponent(bookId)}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

/**
 * Convert a response from KnowledgeEngine.get_structured_book (or /knowledge/structured/{id})
 * into the (Chapter[], nodesByChapterMap) shape the reader expects.
 */
export function chaptersAndNodesFromKeStructured(keBook: any): { chapters: Chapter[]; nodesByChapter: Record<string, any[]> } {
  const rawChapters = keBook?.chapters || [];
  const chapters: Chapter[] = rawChapters.map((ch: any, i: number) => ({
    id: ch.id,
    title: ch.title,
    order: i,
    sourceLocation: ch.number ? `Chapter ${ch.number}` : undefined,
    nodeIds: (keBook?.chapter_node_ids?.[ch.id] || []) as string[],
    properties: { level: ch.level, structured: true, source: "ke" },
  }));
  const nodesByChapter: Record<string, any[]> = keBook?.nodes_by_chapter || {};
  return { chapters, nodesByChapter };
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

/**
 * Build clean, sliceable content blocks for the reader right pane using the
 * authoritative structured chapters (with start_line/end_line from the build script).
 * Emits chapter-level blocks and, when present, nested section blocks using the
 * precise line ranges. This gives stable ids for deep-link jumps and hierarchical nav.
 */
export function sectionsFromStructured(
  sb: StructuredBook,
  fullMarkdown: string
): { id: string; title: string; content: string }[] {
  if (!sb?.chapters?.length || !fullMarkdown || typeof fullMarkdown !== "string") return [];
  const lines = fullMarkdown.split(/\r?\n/);
  const blocks: { id: string; title: string; content: string }[] = [];

  for (const ch of sb.chapters) {
    const hasSections = !!(ch.sections && ch.sections.length > 0);
    const chStart = typeof ch.start_line === "number" ? ch.start_line : 0;
    const chEndEx = typeof ch.end_line === "number" ? ch.end_line + 1 : lines.length;

    if (hasSections && ch.sections) {
      // Lightweight chapter header block (title + short lead) so the chapter id is targetable.
      const lead = lines.slice(Math.max(0, chStart), Math.min(lines.length, chEndEx)).join("\n").trim();
      // Use a compact header so the main readable content lives in the section slices.
      const headerContent = lead.split("\n").slice(0, 3).join("\n").trim() || ch.title;
      blocks.push({ id: ch.id, title: ch.title || `Chapter ${ch.number || ""}`.trim(), content: headerContent });

      for (const sec of ch.sections) {
        const sStart = typeof sec.start_line === "number" ? sec.start_line : chStart;
        const sEndEx = typeof sec.end_line === "number" ? sec.end_line + 1 : chEndEx;
        const content = lines.slice(Math.max(0, sStart), Math.min(lines.length, sEndEx)).join("\n").trim();
        if (content) {
          blocks.push({ id: sec.id, title: sec.title, content });
        }
      }
    } else {
      const content = lines.slice(Math.max(0, chStart), Math.min(lines.length, chEndEx)).join("\n").trim();
      if (content) {
        blocks.push({
          id: ch.id,
          title: ch.title || `Chapter ${ch.number || ""}`.trim(),
          content,
        });
      }
    }
  }
  return blocks;
}
