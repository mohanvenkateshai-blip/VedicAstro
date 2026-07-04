import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth/session";
import { updateDisplayName } from "@/lib/auth/index";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const { name } = (await req.json().catch(() => ({}))) as { name?: string };
  const clean = (name ?? "").trim();
  if (!clean) return NextResponse.json({ error: "name required" }, { status: 400 });

  await updateDisplayName(session.userId, clean);
  return NextResponse.json({ ok: true, name: clean.slice(0, 80) });
}
