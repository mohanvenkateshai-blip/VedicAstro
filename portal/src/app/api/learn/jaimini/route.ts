import { NextResponse } from "next/server";
import { getBookTextNodes, getJaiminiNodes, DEFAULT_GRAPH_VERSION } from "@/lib/corpus";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    // Try fuzzy first
    const fuzzy = await getJaiminiNodes();
    if (fuzzy && fuzzy.length > 0) {
      return NextResponse.json({
        nodes: fuzzy,
        source: fuzzy[0]?.source_file || "fuzzy:jaimini*",
        version: DEFAULT_GRAPH_VERSION,
      });
    }

    const candidates = [
      "Jaimini_Sutras.md",
      "rath_s_jaimini_maharishis_upadesa_sutra.md",
      "jaimini_astrology_calculation_of_mandook_dasha_with_a_case_study_compress.md",
      "Predicting_Through_Jaimini_Astrology.md",
    ];

    for (const candidate of candidates) {
      try {
        const data = await getBookTextNodes(candidate);
        if (data && data.length > 0) {
          return NextResponse.json({
            nodes: data,
            source: candidate,
            version: DEFAULT_GRAPH_VERSION,
          });
        }
      } catch {
        // try next
      }
    }

    // No real data found — signal to client to use fallback
    return NextResponse.json({
      nodes: [],
      source: "Jaimini_Sutras.md (corpus excerpt)",
      version: DEFAULT_GRAPH_VERSION,
    });
  } catch (e) {
    return NextResponse.json({
      nodes: [],
      source: "Jaimini_Sutras.md (corpus excerpt)",
      version: DEFAULT_GRAPH_VERSION,
      error: "lookup failed",
    }, { status: 200 }); // still 200 so client shows nice fallback
  }
}
