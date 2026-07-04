import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth/session";
import { updateLastPath } from "@/lib/auth/index";

export const runtime = "nodejs";

// Never resume onto these — auth flow, API, or the resume redirector itself.
const SKIP = ["/auth", "/api", "/resume"];

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const { path } = (await req.json().catch(() => ({}))) as { path?: string };
  if (!path || !path.startsWith("/") || SKIP.some((p) => path.startsWith(p))) {
    return NextResponse.json({ ok: false, skipped: true });
  }

  await updateLastPath(session.userId, path.slice(0, 512));
  return NextResponse.json({ ok: true });
}
