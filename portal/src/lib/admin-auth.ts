import "server-only";
import { NextResponse } from "next/server";
import { getSession } from "@/lib/auth/session";
import { hasAtLeast, type Role } from "@/lib/auth/types";

export async function requireAdminApi() {
  const session = await getSession();
  if (!session) {
    return { error: NextResponse.json({ error: "Unauthorized" }, { status: 401 }) };
  }
  if (!hasAtLeast(session.role, "admin" as Role)) {
    return { error: NextResponse.json({ error: "Forbidden" }, { status: 403 }) };
  }
  return { session };
}

export function adminErrorResponse(err: unknown, status = 500) {
  const msg = err instanceof Error ? err.message : String(err);
  return NextResponse.json({ error: msg }, { status });
}
