import "server-only";
import { supabase } from "@/lib/supabase";

export const CORPUS_BUCKET = "corpus-vault";
export const DEFAULT_GRAPH_VERSION = "newbooks-v1";

export type CorpusSource = {
  id: string;
  canonical_name: string;
  storage_path: string;
  sha256: string;
  bytes: number;
  book_family: string | null;
  ingest_method: string | null;
  updated_at: string;
};

export type GraphNodeRow = {
  id: string;
  graph_version: string;
  label: string | null;
  file_type: string | null;
  source_file: string | null;
  source_location: string | null;
  community: number | null;
  properties: Record<string, unknown>;
};

export type GraphLinkRow = {
  id: string;
  source_id: string;
  target_id: string;
  relation: string | null;
};

export async function corpusStats(graphVersion = DEFAULT_GRAPH_VERSION) {
  const [sources, nodes, links, runs] = await Promise.all([
    supabase.from("corpus_sources").select("id", { count: "exact", head: true }),
    supabase
      .from("graph_nodes")
      .select("id", { count: "exact", head: true })
      .eq("graph_version", graphVersion),
    supabase
      .from("graph_links")
      .select("id", { count: "exact", head: true })
      .eq("graph_version", graphVersion),
    supabase
      .from("graph_ingest_runs")
      .select("*")
      .eq("graph_version", graphVersion)
      .order("completed_at", { ascending: false })
      .limit(1),
  ]);

  return {
    sources: sources.count ?? 0,
    nodes: nodes.count ?? 0,
    links: links.count ?? 0,
    lastRun: runs.data?.[0] ?? null,
    errors: [sources.error, nodes.error, links.error, runs.error].filter(Boolean),
  };
}

export async function listCorpusSources(): Promise<CorpusSource[]> {
  const { data, error } = await supabase
    .from("corpus_sources")
    .select("*")
    .order("canonical_name");
  if (error) throw error;
  return (data ?? []) as CorpusSource[];
}

export async function searchGraphNodes(opts: {
  graphVersion?: string;
  sourceFile?: string;
  q?: string;
  community?: number;
  limit?: number;
}): Promise<GraphNodeRow[]> {
  const version = opts.graphVersion ?? DEFAULT_GRAPH_VERSION;
  const limit = Math.min(opts.limit ?? 80, 200);
  let q = supabase
    .from("graph_nodes")
    .select("id, graph_version, label, file_type, source_file, source_location, community, properties")
    .eq("graph_version", version)
    .limit(limit);

  if (opts.sourceFile) q = q.eq("source_file", opts.sourceFile);
  if (opts.community != null) q = q.eq("community", opts.community);
  if (opts.q?.trim()) q = q.ilike("label", `%${opts.q.trim()}%`);

  const { data, error } = await q.order("label");
  if (error) throw error;
  return (data ?? []) as GraphNodeRow[];
}

export async function graphNeighbors(
  nodeId: string,
  graphVersion = DEFAULT_GRAPH_VERSION,
): Promise<{ node: GraphNodeRow | null; links: GraphLinkRow[]; neighbors: GraphNodeRow[] }> {
  const { data: node, error: ne } = await supabase
    .from("graph_nodes")
    .select("id, graph_version, label, file_type, source_file, source_location, community, properties")
    .eq("graph_version", graphVersion)
    .eq("id", nodeId)
    .maybeSingle();
  if (ne) throw ne;

  const { data: outLinks } = await supabase
    .from("graph_links")
    .select("id, source_id, target_id, relation")
    .eq("graph_version", graphVersion)
    .eq("source_id", nodeId)
    .limit(50);

  const { data: inLinks } = await supabase
    .from("graph_links")
    .select("id, source_id, target_id, relation")
    .eq("graph_version", graphVersion)
    .eq("target_id", nodeId)
    .limit(50);

  const links = [...(outLinks ?? []), ...(inLinks ?? [])] as GraphLinkRow[];
  const neighborIds = [...new Set(links.flatMap((l) => [l.source_id, l.target_id]).filter((id) => id !== nodeId))];

  let neighbors: GraphNodeRow[] = [];
  if (neighborIds.length) {
    const { data: nd } = await supabase
      .from("graph_nodes")
      .select("id, graph_version, label, file_type, source_file, source_location, community, properties")
      .eq("graph_version", graphVersion)
      .in("id", neighborIds.slice(0, 40));
    neighbors = (nd ?? []) as GraphNodeRow[];
  }

  return { node: (node as GraphNodeRow) ?? null, links, neighbors };
}

export async function listCommunities(graphVersion = DEFAULT_GRAPH_VERSION) {
  const { data, error } = await supabase
    .from("graph_nodes")
    .select("community")
    .eq("graph_version", graphVersion)
    .not("community", "is", null);
  if (error) throw error;
  const counts = new Map<number, number>();
  for (const row of data ?? []) {
    const c = row.community as number;
    counts.set(c, (counts.get(c) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([community, count]) => ({ community, count }))
    .sort((a, b) => b.count - a.count);
}

export async function getBookTextNodes(
  sourceFile: string,
  graphVersion = DEFAULT_GRAPH_VERSION,
) {
  const { data, error } = await supabase
    .from("graph_nodes")
    .select("id, label, source_location, properties, file_type")
    .eq("graph_version", graphVersion)
    .eq("source_file", sourceFile)
    .order("source_location", { ascending: true })
    .limit(200);
  if (error) throw error;
  return (data ?? []) as Array<{
    id: string;
    label: string | null;
    source_location: string | null;
    properties: Record<string, unknown>;
    file_type: string | null;
  }>;
}
