import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";
import { DEFAULT_GRAPH_VERSION } from "@/lib/corpus";

export const dynamic = "force-dynamic";

const REAL_SOURCES = [
  "Jaimini_Sutras",
  "Jaimini_Sutras.md",
  "rath_s_jaimini_maharishis_upadesa_sutra",
  "rath_s_jaimini_maharishis_upadesa_sutra.md",
];

export async function GET() {
  for (const key of REAL_SOURCES) {
    try {
      const { data, error } = await supabase
        .from("graph_nodes")
        .select("id, label, source_location, properties, file_type, source_file")
        .eq("graph_version", DEFAULT_GRAPH_VERSION)
        .ilike("source_file", `%${key.replace(/\.md$/, "")}%`)
        .order("source_location", { ascending: true })
        .limit(200);
      if (error || !data?.length) continue;
      const real = data.filter((n) => n.label && n.label.trim().length > 5);
      if (real.length > 0) {
        return NextResponse.json({
          nodes: real,
          source: data[0]?.source_file || key,
          version: DEFAULT_GRAPH_VERSION,
        });
      }
    } catch {
      // try next source
    }
  }

  return NextResponse.json({
    nodes: [],
    source: "no real Jaimini nodes in graph",
    version: DEFAULT_GRAPH_VERSION,
    hint: "Use /learn/Jaimini_Sutras for structured chapter reader with full source text.",
  });
}
