import { NextResponse } from "next/server";
import { getBookTextNodes } from "@/lib/corpus";

export const dynamic = "force-dynamic";

// Only real core Jaimini sources (the actual sutra texts)
const REAL_SOURCES = [
  "Jaimini_Sutras.md",
  "rath_s_jaimini_maharishis_upadesa_sutra.md",
];

export async function GET() {
  for (const file of REAL_SOURCES) {
    try {
      const data = await getBookTextNodes(file, "newbooks-v1");
      if (data && data.length > 0) {
        const real = data.filter((n: any) => n.label && n.label.trim().length > 5);
        if (real.length > 0) {
          return NextResponse.json({
            nodes: real,
            source: file,
            version: "newbooks-v1",
          });
        }
      }
    } catch {
      // try next source
    }
  }

  return NextResponse.json({
    nodes: [],
    source: "no real Jaimini nodes in graph",
    version: "newbooks-v1",
  });
}
