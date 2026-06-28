import { NextRequest, NextResponse } from "next/server";
import { requireAdminApi, adminErrorResponse } from "@/lib/admin-auth";
import { searchGraphNodes, listCommunities } from "@/lib/corpus";

export async function GET(req: NextRequest) {
  const gate = await requireAdminApi();
  if (gate.error) return gate.error;

  const sp = req.nextUrl.searchParams;
  const mode = sp.get("mode");

  try {
    if (mode === "communities") {
      const communities = await listCommunities(sp.get("version") ?? undefined);
      return NextResponse.json(communities);
    }

    const nodes = await searchGraphNodes({
      q: sp.get("q") ?? undefined,
      sourceFile: sp.get("source") ?? undefined,
      community: sp.has("community") ? Number(sp.get("community")) : undefined,
      limit: sp.has("limit") ? Number(sp.get("limit")) : undefined,
      graphVersion: sp.get("version") ?? undefined,
    });
    return NextResponse.json(nodes);
  } catch (e) {
    return adminErrorResponse(e);
  }
}
