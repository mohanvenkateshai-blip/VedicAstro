import "server-only";
import { supabase } from "@/lib/supabase";
import { DEFAULT_GRAPH_VERSION, GraphNodeRow, searchGraphNodes, listCorpusSources, CorpusSource } from "./corpus";
import fs from "fs";
import path from "path";

/** Resolve data dirs: bundled portal/data/ (Vercel) then monorepo knowledge-graph/ (local dev). */
function resolveDataDir(name: "structured" | "patches"): string {
  const bundled = path.join(process.cwd(), "data", name);
  if (fs.existsSync(bundled)) return bundled;
  return path.join(process.cwd(), "..", "knowledge-graph", name);
}

function getStructuredDir(): string {
  return resolveDataDir("structured");
}

function getPatchesDir(): string {
  return resolveDataDir("patches");
}

function getRawDir(): string {
  // Bundled copy (portal/data/raw) wins when present. This is populated by
  //   node scripts/sync-structured-data.mjs  (run via predev/prebuild)
  // and/or committed into the repo for production Vercel bundles.
  //
  // For local dev WITHOUT a prior copy, we fall back to the monorepo sibling:
  //   ../knowledge-graph/raw
  // This is the preferred path during active development — no copy step needed,
  // changes to source markdown are immediately visible, and it works even if
  // portal/data/raw/ is absent.
  //
  // Cost note: copying ~61 files / ~21 MB is cheap; we still prefer sibling
  // for dev to avoid staleness and unnecessary I/O on every `npm run dev`.
  const candidates = [
    path.join(process.cwd(), "data", "raw"),
    path.join(process.cwd(), "..", "knowledge-graph", "raw"),
    path.join(process.cwd(), "knowledge-graph", "raw"),
    path.resolve(process.cwd(), "../../knowledge-graph/raw"),
  ];
  for (const d of candidates) {
    if (fs.existsSync(d)) return d;
  }
  return candidates[1];
}

/**
 * Load raw markdown from local filesystem (knowledge-graph/raw sources).
 *
 * DISCOVERY ORDER:
 *   1) Exact: <rawDir>/<fileKey>.md
 *   2) Bare:  <rawDir>/<fileKey>
 *   3) Fuzzy scan (all *.md): normalize both sides (lower, strip spaces/underscores/dashes)
 *      and match if one contains the other or they are equal after normalization.
 *      This ensures oddly-named or historically-mismatched stems still resolve
 *      (e.g. "FireShot Capture ...", names with en-dashes, "Tithi–Vāra", etc.).
 *
 * This function is what makes all 61+ raw .md files discoverable by the Learn
 * reader without requiring an exact storage_path match.
 */
export function loadLocalRawMarkdown(fileKey: string | null | undefined, ...extraHints: (string | null | undefined)[]): string | null {
  if (!fileKey && extraHints.length === 0) return null;
  const rawDir = getRawDir();
  if (!fs.existsSync(rawDir)) return null;

  const allKeys = [fileKey, ...extraHints].filter((k): k is string => !!k);
  const candidates: string[] = [];
  for (const k of allKeys) {
    candidates.push(k, `${k}.md`);
    for (const v of bookIdVariants(k)) {
      candidates.push(v, `${v}.md`);
    }
  }
  // dedup while preserving order
  const seen = new Set<string>();
  const uniqCands = candidates.filter((c) => (seen.has(c) ? false : (seen.add(c), true)));
  for (const c of uniqCands) {
    const p = path.join(rawDir, c);
    if (fs.existsSync(p)) {
      try {
        return fs.readFileSync(p, "utf8");
      } catch {}
    }
  }

  // Fuzzy discovery so that any of the 61+ raw files can be found even when
  // the recorded storage_path stem doesn't exactly match the filename on disk.
  // This is intentionally broad but cheap (single readdir + small string work).
  try {
    const files = fs.readdirSync(rawDir).filter((f) => f.toLowerCase().endsWith(".md"));
    const norm = (s: string) =>
      (s || "")
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "") // strip diacritics (ā, etc)
        .replace(/[-_\s–—\.·•[\](){}'"`~!@#$%^&*=+\\|;:<>,/?]+/g, "");
    const wantNorms = allKeys.flatMap((k) => bookIdVariants(k).map(norm));
    for (const f of files) {
      const have = norm(f.replace(/\.md$/i, ""));
      if (!have) continue;
      if (wantNorms.some((w) => w === have || have.includes(w) || w.includes(have))) {
        try {
          return fs.readFileSync(path.join(rawDir, f), "utf8");
        } catch {}
      }
    }
  } catch {}
  return null;
}

/** Normalize URL slugs / canonical names into lookup keys (underscore stem is canonical on disk). */
export function bookIdVariants(bookId: string): string[] {
  const trimmed = (bookId || "").trim();
  if (!trimmed) return [];
  const spaced = trimmed.replace(/[-_]+/g, " ");
  const underscored = trimmed.replace(/-/g, "_").replace(/\s+/g, "_");
  return [...new Set([trimmed, spaced, underscored, trimmed.replace(/_/g, "-")].filter(Boolean))];
}

/** All id strings to try when locating a structured JSON on disk or via fuzzy scan. */
function structuredLookupIds(...hints: (string | null | undefined)[]): string[] {
  const out: string[] = [];
  for (const hint of hints) {
    if (!hint) continue;
    for (const v of bookIdVariants(hint)) out.push(v);
  }
  return [...new Set(out)];
}

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
  // Nice display fields for cards
  displayTitle?: string;
  author?: string | null;
  year?: string | null;
};

export type Chapter = {
  id: string; // node id or section slug
  title: string;
  order: number;
  sourceLocation?: string;
  nodeIds: string[]; // associated graph nodes
  properties?: Record<string, unknown>;
};

/** Turn ugly slugs/filenames into reasonable titles. */
function humanizeTitle(input: string): string {
  let t = (input || "")
    .replace(/[_-]/g, " ")
    .replace(/\s+/g, " ")
    .replace(/\.(md|txt|pdf)$/i, "")
    .trim();

  // Remove common scan/ocr junk
  t = t.replace(/\b(compress|compressed|scan|ocr|text|full|vol\s*\d+|edition)\b/gi, "");
  t = t.replace(/\s{2,}/g, " ").trim();

  // Basic title casing
  t = t.replace(/\b\w/g, (c) => c.toUpperCase());

  // Special known cleanups
  const known: Record<string, string> = {
    "Gochar Phaladeepika Pulippani": "Gochar Phaladeepika",
    "Jaimini Sutras": "Jaimini Sutras",
    "Brihat Parasara Hora Sastra": "Brihat Parashara Hora Shastra",
  };
  if (known[t]) return known[t];

  return t || input;
}

/** Best effort extraction of title / author / year from raw markdown front-matter. */
export function extractDisplayMeta(raw: string | null, fallback: string): { displayTitle: string; author: string | null; year: string | null } {
  const fallbackTitle = humanizeTitle(fallback);

  if (!raw) {
    return { displayTitle: fallbackTitle, author: null, year: null };
  }

  const head = raw.slice(0, 6000);
  const lines = head.split(/\r?\n/).map(l => l.trim()).filter(Boolean);

  let title = fallbackTitle;
  let author: string | null = null;
  let year: string | null = null;

  // 1) Try to find a good title from first real heading
  for (const line of lines.slice(0, 25)) {
    if (/^#{1,3}\s+/.test(line)) {
      let t = line.replace(/^#{1,3}\s+/, "").trim();
      if (/^page\s*\d+$/i.test(t)) continue;
      if (t.length > 3 && t.length < 90 && !/^[0-9\s.,;:!?]+$/.test(t)) {
        t = humanizeTitle(t);
        if (t.length > 3) {
          title = t;
          break;
        }
      }
    }
  }

  // 2) Look for author patterns in the head
  const authorPatterns = [
    /(?:by|author|dr\.|prof\.|pandit|shri|sh\.|sri)\s+([A-Z][A-Za-z.\s\-']{3,50})/i,
    /([A-Z][A-Za-z.\s\-']{3,40})\s*(?:\(|\s*-\s*|$)/,  // loose name
  ];
  for (const line of lines.slice(0, 30)) {
    if (/foreword|introduction|contents|copyright|price|edition/i.test(line)) continue;
    for (const re of authorPatterns) {
      const m = line.match(re);
      if (m && m[1]) {
        let cand = m[1].replace(/[\s,.;:]+$/,'').trim();
        if (cand.length > 3 && !/^(the|and|with|from|by)$/i.test(cand)) {
          author = cand;
          break;
        }
      }
    }
    if (author) break;
  }

  // 3) Year: look for plausible publication years
  const yearMatch = head.match(/\b(1[89]\d{2}|20[0-2]\d)\b/);
  if (yearMatch) year = yearMatch[1];

  // Special known good titles override for ugly cases
  const overrides: Record<string, {title?: string, author?: string, year?: string}> = {
    "Gochar_Phaladeepika_Pulippani": { title: "Gochar Phaladeepika", author: "Dr. U.S. Pulippani" },
    "Jaimini_Sutras": { title: "Jaimini Sutras", author: "Prof. B. Suryanarain Rao (rev. B.V. Raman)", year: "1949" },
    "Graha_Laghava": { title: "Graha Laghava" },
    "Hora_Sara": { title: "Hora Sara" },
    "Hora_Shastra_Varahamihira": { title: "Hora Shastra", author: "Varahamihira" },
    "Brihat_Parasara_Hora_Sastra_Vol_1": { title: "Brihat Parashara Hora Shastra (Vol 1)" },
    "Saravali": { title: "Saravali", author: "Kalyana Varma" },
  };
  const key = fallback.replace(/\s+/g, "_");
  if (overrides[key]) {
    const o = overrides[key];
    if (o.title) title = o.title;
    if (o.author) author = o.author;
    if (o.year) year = o.year;
  }

  return { displayTitle: title || fallbackTitle, author, year };
}


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

      const structured = resolveStructuredBookSync(fileKey, canonical);
      let chapterCount = structured?.chapters?.length || structured?.total_chapters || 0;

      // Load a small preview for better titles + author/year (local first)
      let rawPreview: string | null = null;
      try {
        rawPreview = loadLocalRawMarkdown(fileKey, canonical) || null;
        if (!rawPreview && fileKey) {
          // try a quick prefix load if full loader available
          const full = getFullBookMarkdown(fileKey ?? canonical ?? "");
          if (full) rawPreview = full.slice(0, 8000);
        }
      } catch {}

      if (!chapterCount) {
        // Fallback: for books without structured JSON, count chapters from improved parse of raw markdown
        if (rawPreview) {
          const p = parseMarkdownToSections(rawPreview);
          chapterCount = p.chapters.length;
        } else {
          const raw = getFullBookMarkdown(fileKey ?? canonical ?? "");
          if (raw) {
            const p = parseMarkdownToSections(raw);
            chapterCount = p.chapters.length;
          }
        }
      }

      const meta = extractDisplayMeta(rawPreview, canonical || fileKey || "");

      return {
        id: fileKey ?? canonical,
        canonicalName: canonical,
        bookFamily: src.book_family,
        storagePath: src.storage_path,
        sha256: src.sha256,
        bytes: src.bytes,
        nodeCount: count || 0,
        chapterCount: chapterCount || undefined,
        displayTitle: meta.displayTitle,
        author: meta.author,
        year: meta.year,
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
export function findCorpusSource(sources: CorpusSource[], bookId: string): CorpusSource | undefined {
  const variants = bookIdVariants(bookId);
  return sources.find((s) => {
    const stem = s.storage_path?.split("/").pop()?.replace(/\.md$/, "") ?? "";
    return variants.some(
      (v) =>
        s.canonical_name === v ||
        stem === v ||
        stem.replace(/_/g, "-") === v.replace(/_/g, "-") ||
        (s.storage_path && s.storage_path.includes(v.replace(/\s+/g, "_"))),
    );
  });
}

export async function loadBook(
  bookId: string,
  graphVersion = DEFAULT_GRAPH_VERSION,
): Promise<BookContent> {
  const sources = await listCorpusSources();
  const source = findCorpusSource(sources, bookId);

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

  // === AUTHORITATIVE STRUCTURED CHAPTERS (from build_structured_library.py) ===
  // Always prefer structured JSON when present — never fall back to graph node source_location buckets
  // (frontmatter / H1 / H2) if a structured file exists for any alias of this book.
  const structured = resolveStructuredBookSync(bookId, source.canonical_name, fileKey);
  let chapters: Chapter[] = [];

  if (structured?.chapters?.length) {
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
  return resolveStructuredBookSync(bookId);
}

/**
 * Try every alias (URL slug, canonical name, md stem) until a structured book with chapters is found.
 * This is the single entry point — loadBook and the Learn reader must both use it.
 */
export function resolveStructuredBookSync(...hints: (string | null | undefined)[]): StructuredBook | null {
  const ids = structuredLookupIds(...hints);
  if (!ids.length) return null;

  try {
    const structuredDir = getStructuredDir();
    if (!fs.existsSync(structuredDir)) return null;

    // Exact filename matches first (fast path)
    for (const id of ids) {
      for (const stem of [id, id.replace(/\s+/g, "_")]) {
        const p = path.join(structuredDir, `${stem}.json`);
        if (fs.existsSync(p)) {
          const data = JSON.parse(fs.readFileSync(p, "utf8")) as StructuredBook;
          if (data?.chapters?.length) return data;
        }
      }
    }

    // Fuzzy scan: book_id, canonical_name, source_file stem
    const norm = (s: string) => (s || "").toLowerCase().replace(/[-_\s]+/g, "");
    const idNorms = new Set(ids.map(norm).filter(Boolean));

    for (const f of fs.readdirSync(structuredDir).filter((fn) => fn.endsWith(".json"))) {
      const full = path.join(structuredDir, f);
      const data = JSON.parse(fs.readFileSync(full, "utf8")) as StructuredBook;
      if (!data?.chapters?.length) continue;
      const keys = [
        data.book_id,
        data.canonical_name,
        data.source_file?.replace(/\.md$/i, ""),
        f.replace(/\.json$/i, ""),
      ];
      if (keys.some((k) => k && idNorms.has(norm(k)))) return data;
      if (keys.some((k) => k && ids.some((id) => k.toLowerCase().includes(id.toLowerCase())))) return data;
    }
  } catch {}
  return null;
}

/** Remote fallback when bundled/monorepo JSON is unavailable (e.g. portal-only deploy before prebuild). */
export async function resolveStructuredBook(...hints: (string | null | undefined)[]): Promise<StructuredBook | null> {
  const local = resolveStructuredBookSync(...hints);
  if (local) return local;

  const ids = structuredLookupIds(...hints);
  const base = process.env.CVCE_BASE_URL ?? "https://vedicastro-cvce.fly.dev";
  for (const id of ids) {
    try {
      const res = await fetch(`${base}/knowledge/structured/${encodeURIComponent(id)}`, {
        cache: "force-cache",
        next: { revalidate: 3600 },
      });
      if (!res.ok) continue;
      const data = (await res.json()) as StructuredBook;
      if (data?.chapters?.length) return data;
    } catch {}
  }
  return null;
}

/**
 * Load ALL structured books (for global search / indexing).
 * Returns only those that have chapters.
 */
export function getAllStructuredBooksSync(): StructuredBook[] {
  try {
    const structuredDir = getStructuredDir();
    if (!fs.existsSync(structuredDir)) return [];
    const files = fs.readdirSync(structuredDir).filter((f) => f.endsWith(".json"));
    const out: StructuredBook[] = [];
    for (const f of files) {
      try {
        const data = JSON.parse(fs.readFileSync(path.join(structuredDir, f), "utf8")) as StructuredBook;
        if (data && Array.isArray(data.chapters) && data.chapters.length > 0) {
          out.push(data);
        }
      } catch {}
    }
    return out;
  } catch {
    return [];
  }
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
    const patchesDir = getPatchesDir();
    const patchPath = path.join(patchesDir, "node-chapter-map.json");
    if (bookId) {
      const variants = [
        bookId,
        bookId.replace(/\s+/g, "_"),
        bookId.replace(/ /g, "_"),
      ].filter((v, i, a) => v && a.indexOf(v) === i);
      for (const v of variants) {
        const perBookPath = path.join(patchesDir, `patch-${v}.json`);
        if (fs.existsSync(perBookPath)) {
          const raw = fs.readFileSync(perBookPath, "utf8");
          return JSON.parse(raw);
        }
      }
      // fuzzy scan for per-book patches by content
      if (fs.existsSync(patchesDir)) {
        const files = fs.readdirSync(patchesDir).filter((f) => f.startsWith("patch-") && f.endsWith(".json"));
        for (const f of files) {
          const full = path.join(patchesDir, f);
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
    if (fs.existsSync(patchPath)) {
      const raw = fs.readFileSync(patchPath, "utf8");
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
 * Load the raw source markdown for a book when a storagePath is known.
 * Used to serve full chapter text (not just graph nodes) and image-capable prose.
 * Local filesystem is always preferred; Supabase is only attempted when no local copy exists.
 */
async function loadRawMarkdownForSource(storagePath: string | null | undefined, ...hints: (string | null | undefined)[]): Promise<string | null> {
  const fileKey = storagePath?.split("/").pop()?.replace(/\.md$/, "") ?? null;

  // Local first (for Graphify / no-Supabase development). Perfect for one book at a time.
  // Pass hints so loadLocal can fuzzy/variant match even when fileKey alone is insufficient.
  const local = loadLocalRawMarkdown(fileKey, ...hints);
  if (local) return local;

  if (!storagePath) return null;
  try {
    const { data: blob } = await supabase.storage.from("corpus-vault").download(storagePath);
    if (blob) return await blob.text();
  } catch {}
  return null;
}

/**
 * Resolve a usable fileKey from loose hints (bookId, canonical, storagePath, etc).
 * Used to probe local raw markdown without requiring a full CorpusSource lookup.
 */
function resolveFileKeyFromHints(...hints: (string | null | undefined)[]): string | null {
  for (const h of hints) {
    if (!h) continue;
    // If it looks like a storage path, take the basename without .md
    if (h.includes("/")) {
      const base = h.split("/").pop() || h;
      return base.replace(/\.md$/i, "");
    }
    // Direct stem
    if (/\.md$/i.test(h)) return h.replace(/\.md$/i, "");
    // Otherwise treat the hint itself as a candidate stem (caller will expand variants via loadLocal)
    if (h && h.length > 1) return h;
  }
  return null;
}

/**
 * Load the full original markdown for reader use.
 *
 * Priority:
 *  1. Local raw (knowledge-graph/raw or portal/data/raw) — no network, always preferred.
 *  2. Supabase corpus-vault (only when no local file was found for any alias).
 *
 * Returns a tag so callers can avoid Supabase work entirely when source === 'local'.
 */
export async function loadFullMarkdownForBook(...hints: (string | null | undefined)[]): Promise<{
  markdown: string | null;
  source: "local" | "supabase" | "none";
  fileKey: string | null;
}> {
  // Fast local probe using all hints (and their common variants) without listing corpus sources.
  const directKeys = Array.from(
    new Set(
      hints
        .filter(Boolean)
        .flatMap((h) => {
          const k = resolveFileKeyFromHints(h);
          if (!k) return [] as string[];
          return bookIdVariants(k);
        })
    )
  );

  for (const key of directKeys) {
    const local = loadLocalRawMarkdown(key);
    if (local) {
      return { markdown: local, source: "local", fileKey: key };
    }
  }

  // If we still have no local, resolve via corpus sources to obtain a storagePath for Supabase fallback.
  try {
    const sources = await listCorpusSources();
    for (const hint of hints) {
      if (!hint) continue;
      const src = findCorpusSource(sources, hint);
      if (src?.storage_path) {
        const md = await loadRawMarkdownForSource(src.storage_path, hint, src.canonical_name, src.storage_path);
        if (md) {
          const fk = src.storage_path.split("/").pop()?.replace(/\.md$/i, "") ?? null;
          // If loadRawMarkdownForSource found it locally under the resolved key, tag accordingly.
          // (loadRawMarkdownForSource already prefers local, so if we reach here with md it could be either.)
          // To be precise, re-probe local with the resolved key.
          const reLocal = fk ? loadLocalRawMarkdown(fk, hint) : null;
          return {
            markdown: md,
            source: reLocal ? "local" : "supabase",
            fileKey: fk,
          };
        }
      }
    }
  } catch {
    // ignore; fall through to none
  }

  return { markdown: null, source: "none", fileKey: null };
}

/**
 * Small convenience helper for readers: synchronously return full markdown preferring
 * local raw (knowledge-graph/raw) for any bookId / stem. Does not touch Supabase.
 * For the async version that falls back to remote, use loadFullMarkdownForBook.
 */
export function getFullBookMarkdown(bookId: string): string | null {
  if (!bookId) return null;
  const sb = resolveStructuredBookSync(bookId);
  const hints = [
    bookId,
    sb?.book_id,
    sb?.canonical_name,
    sb?.source_file,
  ].filter(Boolean) as string[];
  const keys = Array.from(
    new Set(
      hints.flatMap((h) => {
        const k = resolveFileKeyFromHints(h);
        return k ? bookIdVariants(k) : [];
      })
    )
  );
  for (const k of keys) {
    const m = loadLocalRawMarkdown(k);
    if (m) return m;
  }
  return loadLocalRawMarkdown(bookId);
}

/**
 * Load full content + nodes for a specific chapter.
 * Prefers structured line ranges over the source markdown (when available) to return
 * the real full chapter text instead of a stub. Falls back to a minimal header if no source.
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

  // Best effort: real chapter body via structured ranges + original Gyan source
  let chapterMarkdown = `# ${chapter.title}\n\n`;
  const fileKey = book.metadata.storagePath?.split("/").pop()?.replace(/\.md$/, "") ?? null;
  const structured = resolveStructuredBookSync(bookId, book.metadata.canonicalName, fileKey, book.metadata.id);
  const full = await loadRawMarkdownForSource(book.metadata.storagePath, bookId, book.metadata.canonicalName, fileKey, book.metadata.id);
  if (structured && full) {
    // Locate the chapter (or section treated as chapter target) in the structured tree
    const chEntry =
      (structured.chapters || []).find((c: any) => c.id === chapterId) ||
      (structured.chapters || []).flatMap((c: any) => c.sections || []).find((s: any) => s.id === chapterId);
    const p = (chapter.properties || {}) as any;
    const start = typeof chEntry?.start_line === "number" ? chEntry.start_line : (typeof p.start_line === "number" ? p.start_line : undefined);
    const end = typeof chEntry?.end_line === "number" ? chEntry.end_line : (typeof p.end_line === "number" ? p.end_line : undefined);
    if (typeof start === "number") {
      const lines = full.split(/\r?\n/);
      const endEx = typeof end === "number" ? end + 1 : lines.length;
      const slice = lines.slice(Math.max(0, start), Math.min(lines.length, endEx)).join("\n").trim();
      if (slice) chapterMarkdown = slice;
    }
  }

  return {
    chapterId,
    title: chapter.title,
    markdown: chapterMarkdown,
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

  // Heavy page-scanned OCR books (hundreds of "## Page N" markers) have no reliable
  // chapter structure. Collapse early to a single clean "Full Text" experience.
  const pageMarkers = (md.match(/##\s*Page\s+\d+/gi) || []).length;
  if (pageMarkers > 30) {
    const full = md.trim();
    return {
      chapters: [{ id: "full", title: "Full Text", order: 0, sourceLocation: undefined, nodeIds: [] }],
      sections: [{ id: "full", title: "Full Text", content: full }],
    };
  }

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
      const headingText = h ? h[2] : (num ? num[2] : "");
      const t = (headingText || "").trim();
      const isPageJunk = /^(frontmatter|front matter|page\s*\d+|p\s*\d+|contents?|index|chapter|introduction|preface)$/i.test(t) || /^\s*[IVXLCDM]+\s*$/i.test(t);
      // Skip spurious headings from OCR (e.g. lone "# and foo..." or very long sentence-like after #, or lowercase fragments).
      const looksSpurious = t.length > 70 || (t.length > 35 && !/^[A-Z0-9]/.test(t)) || /^and |^the |^of |^to /i.test(t) || (h && !/^#{1,2}\s/.test(line) && t.split(/\s+/).length > 6);
      if (isPageJunk || looksSpurious) {
        // Do not split sections on page markers or frontmatter; accumulate under prior real heading.
        // This keeps full prose together while still embedding the page markers in content.
        curr.push(line);
        continue;
      }
      flush();
      currTitle = t;
      curr = [line];
      continue;
    }
    curr.push(line);
  }
  flush();

  let sections: MarkdownSection[] = raw
    .map((r, i) => ({
      id: `sec-${i}`,
      title: r.title || `Section ${i + 1}`,
      content: r.lines.join("\n"),
    }))
    .filter((s) => s.content.trim().length > 0);

  // Remove junk "Frontmatter"/page/codey titles (prefer real headings). Keep content in prior sections.
  const junk = /^(frontmatter|front matter|h1|main|start|untitled|unknown|page\s*\d*|p\s*\d+|contents?|index|chapter|chapters|introduction|preface|appendix)$/i;
  const codey = /^\d{4}\.\S+|[\w.-]{10,}\.md$|^\d+[\._-]\d{3,}/i;
  sections = sections.filter((s) => {
    const t = (s.title || "").trim();
    if (junk.test(t)) return false;
    if (t.length > 55 && codey.test(t)) return false;
    const letters = t.replace(/[^\p{L}]/gu, "");
    if (letters.length < 2) return false; // ocr noise like "^" or "Ri"
    if (t.length < 3) return false;
    // Additional OCR gibberish guard for titles (require vowel + reasonable ascii words; drop fragments).
    if (!/[aeiouy]/i.test(t) || !/[a-zA-Z]{2,}/.test(t)) return false;
    if (/^[a-z]/.test(t) && !/^\d/.test(t)) return false;
    return true;
  });

  // Body-quality filter for raw/OCR fallbacks: drop micro-sections with almost no prose.
  // Keeps only sections that have real content (prevents "Page 123" or lone "I" from becoming chapters).
  sections = sections.filter((s) => {
    const body = s.content.replace(/^\s*#{1,6}\s*.+$/m, "").trim();
    const nonEmpty = body.split(/\r?\n/).filter((l) => l.trim().length > 0).length;
    const chars = body.replace(/[^\p{L}\p{N}]/gu, "").length;
    return nonEmpty >= 2 && chars >= 60;
  });

  let chapters: Chapter[] = sections.map((s, i) => ({
    id: s.id,
    title: s.title,
    order: i,
    sourceLocation: undefined,
    nodeIds: [],
  }));

  // Drop a leading long/code title (e.g. the ocr filename heading) so real content starts the TOC.
  if (chapters.length > 0 && (chapters[0].title.length > 55 || codey.test(chapters[0].title))) {
    chapters = chapters.slice(1).map((c, i) => ({ ...c, order: i }));
    sections = sections.slice(1);
  }

  if (chapters.length === 0) {
    // Fallback for raws without usable headings (e.g. page-scanned only): expose full as one chapter.
    const full = md.trim();
    sections = [{ id: "full", title: "Full Text", content: full }];
    chapters = [{ id: "full", title: "Full Text", order: 0, sourceLocation: undefined, nodeIds: [] }];
  }

  // Final quality gate: if remaining chapters are all gibberish (OCR noise titles with no real words), fall back to single clean "Full Text".
  const isGibberishTitle = (tt: string) => !tt || tt.length < 4 || !/[a-zA-Z]{4,}/.test(tt) || /[*{}|<>]/.test(tt) || tt.replace(/[a-zA-Z0-9\s:.,'-]/g, "").length > 1;
  if (chapters.length > 0 && chapters.every((c) => isGibberishTitle(c.title))) {
    const full = md.trim();
    sections = [{ id: "full", title: "Full Text", content: full }];
    chapters = [{ id: "full", title: "Full Text", order: 0, sourceLocation: undefined, nodeIds: [] }];
  }

  chapters = chapters.map((c, i) => ({ ...c, order: i }));

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
      // Full chapter content (not a slice) so the chapter id renders the complete prose for that chapter.
      // Section entries remain for precise deep links (?section=) and intra-chapter jumps.
      const chapterFull = lines.slice(Math.max(0, chStart), Math.min(lines.length, chEndEx)).join("\n").trim();
      blocks.push({
        id: ch.id,
        title: ch.title || `Chapter ${ch.number || ""}`.trim(),
        content: chapterFull || ch.title,
      });

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
