import { NextResponse } from "next/server";
import { requireAdminApi, adminErrorResponse } from "@/lib/admin-auth";
import { listCorpusSources } from "@/lib/corpus";

export async function GET() {
  const gate = await requireAdminApi();
  if (gate.error) return gate.error;
  try {
    const sources = await listCorpusSources();
    return NextResponse.json(sources);
  } catch (e) {
    return adminErrorResponse(e);
  }
}
