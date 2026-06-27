import { NextResponse } from "next/server";
import { ensureSchema, schemaTablesPresent } from "@/lib/auth/migrate";

function unauthorized() {
  return NextResponse.json({ error: "unauthorized" }, { status: 401 });
}

function checkSecret(req: Request): boolean {
  const expected = process.env.AUTH_SECRET?.trim();
  if (!expected) return false;
  const header = req.headers.get("authorization")?.replace(/^Bearer\s+/i, "").trim();
  const query = new URL(req.url).searchParams.get("secret")?.trim();
  return header === expected || query === expected;
}

/** GET — schema status (tables present?). No auth required. */
export async function GET() {
  const configured = !!process.env.DATABASE_URL?.trim();
  if (!configured) {
    return NextResponse.json({
      configured: false,
      tablesPresent: false,
      message: "DATABASE_URL not set on this deployment",
    });
  }
  const tablesPresent = await schemaTablesPresent();
  return NextResponse.json({
    configured: true,
    tablesPresent,
    message: tablesPresent
      ? "Schema tables exist"
      : "Tables missing — POST with AUTH_SECRET to apply schema",
  });
}

/** POST — apply schema.sql on the server (uses production DATABASE_URL). */
export async function POST(req: Request) {
  if (!checkSecret(req)) return unauthorized();
  if (!process.env.DATABASE_URL?.trim()) {
    return NextResponse.json({ error: "DATABASE_URL not configured" }, { status: 503 });
  }
  try {
    const force = new URL(req.url).searchParams.get("force") === "1";
    const result = await ensureSchema(force);
    const tablesPresent = await schemaTablesPresent();
    return NextResponse.json({ ok: true, tablesPresent, ...result });
  } catch (e) {
    const message = e instanceof Error ? e.message : "migration failed";
    console.error("Schema migration failed:", e);
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
