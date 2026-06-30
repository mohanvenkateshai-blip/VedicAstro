import fs from "fs";
import path from "path";

/** Local Graphify loader (no Supabase). Loads the big graph.json once and provides book-scoped queries. */

let _graphCache: any = null;

function getGraphPath(): string {
  // Try bundled data first (if we ever snapshot a subset), then monorepo source.
  const bundled = path.join(process.cwd(), "data", "graph.json");
  if (fs.existsSync(bundled)) return bundled;
  return path.join(process.cwd(), "..", "knowledge-graph", "graphify-out", "graph.json");
}

export function loadGraphifyGraph() {
  if (_graphCache) return _graphCache;
  const p = getGraphPath();
  if (!fs.existsSync(p)) {
    throw new Error(`Graphify graph not found at ${p}`);
  }
  const raw = fs.readFileSync(p, "utf8");
  _graphCache = JSON.parse(raw);
  return _graphCache;
}

export type GraphifyNode = {
  id: string;
  label?: string;
  source_file?: string;
  source_location?: string;
  properties?: Record<string, any>;
  community?: number;
  [key: string]: any;
};

export function getNodesForBook(bookId: string): GraphifyNode[] {
  const g = loadGraphifyGraph();
  const nodes: GraphifyNode[] = g.nodes || [];
  const variants = [
    bookId,
    bookId.replace(/\s+/g, "_"),
    bookId.replace(/-/g, "_"),
    bookId.toLowerCase(),
  ].filter(Boolean);

  return nodes.filter((n) => {
    const sf = (n.source_file || "").toLowerCase();
    return variants.some((v) => sf.includes(v.toLowerCase()) || sf.includes(v.replace(/_/g, " ").toLowerCase()));
  });
}

export function getNodesForChapter(bookId: string, chapterId: string, patch: any): GraphifyNode[] {
  if (!patch?.patches) return [];
  const norm = (s: string) => (s || "").toLowerCase().replace(/\s+/g, "_");
  const bookKey = norm(bookId);
  const nodeIds = new Set<string>();

  for (const p of patch.patches) {
    const bid = norm(p.book_id || "");
    if (!bid || (!bid.includes(bookKey) && bookKey !== bid)) continue;
    if (p.chapter_id === chapterId && p.node_id) {
      nodeIds.add(p.node_id);
    }
  }

  const allBookNodes = getNodesForBook(bookId);
  return allBookNodes.filter((n) => nodeIds.has(n.id));
}
