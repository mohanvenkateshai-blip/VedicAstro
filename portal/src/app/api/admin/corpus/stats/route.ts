import { NextResponse } from "next/server";
import { requireAdminApi, adminErrorResponse } from "@/lib/admin-auth";
import { corpusStats } from "@/lib/corpus";

export async function GET() {
  const gate = await requireAdminApi();
  if (gate.error) return gate.error;
  try {
    const stats = await corpusStats();
    return NextResponse.json(stats);
  } catch (e) {
    return adminErrorResponse(e);
  }
}
