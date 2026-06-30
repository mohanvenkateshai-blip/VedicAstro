import { NextResponse } from "next/server";
import { getBookTextNodes, getJaiminiNodes, DEFAULT_GRAPH_VERSION } from "@/lib/corpus";

export const dynamic = "force-dynamic";

const REAL_JAIMINI_SOURCES = [
  "Jaimini_Sutras",
  "rath_s_jaimini_maharishis_upadesa_sutra",
];

function usableNodes(nodes: Array<{ label?: string | null; properties?: Record<string, unknown> }>) {
  return nodes.filter((n) => {
    const label = (n.label ?? "").trim();
    if (label.length >= 1) return true;
    return String(n.properties?.description ?? "").trim().length > 0;
  });
}

export async function GET() {
  for (const stem of REAL_JAIMINI_SOURCES) {
    try {
      const data = await getBookTextNodes(stem, DEFAULT_GRAPH_VERSION);
      const real = usableNodes(data ?? []);
      if (real.length > 0) {
        return NextResponse.json({
          nodes: real,
          source: stem,
          version: DEFAULT_GRAPH_VERSION,
        });
      }
    } catch {
      // try next source
    }
  }

  try {
    const fuzzy = await getJaiminiNodes(DEFAULT_GRAPH_VERSION);
    const real = usableNodes(fuzzy ?? []);
    if (real.length > 0) {
      return NextResponse.json({
        nodes: real,
        source: "fuzzy:jaimini",
        version: DEFAULT_GRAPH_VERSION,
      });
    }
  } catch {
    // fall through
  }

  return NextResponse.json({
    nodes: [],
    source: "no real Jaimini nodes in graph",
    version: DEFAULT_GRAPH_VERSION,
    hint: "Use /learn/Jaimini_Sutras for structured chapter reader with full source text.",
  });
}
