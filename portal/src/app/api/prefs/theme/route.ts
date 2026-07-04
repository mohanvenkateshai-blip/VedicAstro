import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth/session";
import { updateUserTheme, type ThemePref } from "@/lib/auth/index";

export const runtime = "nodejs";

const VALID: ThemePref[] = ["light", "dark", "system"];

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const { theme } = (await req.json().catch(() => ({}))) as { theme?: string };
  if (!theme || !VALID.includes(theme as ThemePref)) {
    return NextResponse.json({ error: "invalid theme" }, { status: 400 });
  }

  await updateUserTheme(session.userId, theme as ThemePref);
  return NextResponse.json({ ok: true, theme });
}
