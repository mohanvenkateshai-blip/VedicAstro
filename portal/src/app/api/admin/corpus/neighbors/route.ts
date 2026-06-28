import { NextRequest, NextResponse } from "next/server";
import { requireAdminApi, adminErrorResponse } from "@/lib/admin-auth";
import { graphNeighbors } from "@/lib/corpus";

export async function GET(req: NextRequest) {
  const gate = await requireAdminApi();
  if (gate.error) return gate.error;

  const id = req.nextUrl.searchParams.get("id");
  if (!id) {
    return NextResponse.json({ error: "id required" }, { status: 400 });
  }

  try {
    const version = req.nextUrl.searchParams.get("version") ?? undefined;
    const graph = await graphNeighbors(id, version);
    return NextResponse.json(graph);
  } catch (e) {
    return adminErrorResponse(e);
  }
}
