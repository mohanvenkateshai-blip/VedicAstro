import { NextRequest, NextResponse } from "next/server";

// Allow up to 60s — CVCE cold start + heavy endpoints (positions × 12, dasha-deep)
export const maxDuration = 60;

const CVCE_BASE_URL =
  process.env.CVCE_BASE_URL ?? "https://vedicastro-cvce.fly.dev";

/** Endpoints the portal may proxy — keep this list tight. */
  const ALLOWED = new Set([
    "dasha-deep",
    "dasha-deep-yogini",
    "dasha-deep-ashtottari",
    "dasha-series",
    "dasha-predict",
    "dasha-predict-yogini",
    "fructification",
    "dashas",
    "gochar",
    "kp-system",
    "varshaphala",
    "kalachakra-dasha",
    "kalachakra-deep",
    "koota-match",
    "positions",
    "yogas",
    "special-points",
    "report/facts",
  ]);

const ALLOWED_GET = new Set(["places", "version", "report/facts"]);

// KnowledgeEngine structured endpoints (Learn reader owns chapter tree + node linkage)
const KNOWLEDGE_PREFIX = "knowledge/";

const REPORT_FACTS_PREFIX = "report/facts";

// Must stay comfortably under `maxDuration` (60s) — Vercel kills the function
// outright (raw 502, bypassing our catch block) if we let fetch run past that.
const SERVER_TIMEOUT_MS = 50_000;

// Module-level cache for KE version (populated from remote /version or payloads)
let cachedKeVersion: string | null = null;

async function getRemoteKeVersion(): Promise<string | null> {
  if (cachedKeVersion) return cachedKeVersion;
  try {
    const controller = new AbortController();
    const t = setTimeout(() => controller.abort(), 8000);
    const r = await fetch(`${CVCE_BASE_URL}/version`, { signal: controller.signal, cache: "no-store" });
    clearTimeout(t);
    if (r.ok) {
      const j = await r.json().catch(() => ({} as any));
      const v = (j && (j.ke_version || j.knowledge_version || j.version)) || null;
      if (v) {
        cachedKeVersion = v;
        return v;
      }
    }
  } catch {}
  return null;
}

function ensureKeVersion<T>(payload: T): T {
  if (payload && typeof payload === "object" && !Array.isArray(payload)) {
    const p = payload as Record<string, unknown>;
    if (!p.ke_version && !p.knowledge_version) {
      if (cachedKeVersion) {
        p.ke_version = cachedKeVersion;
      }
    } else if (p.ke_version && !cachedKeVersion) {
      cachedKeVersion = String(p.ke_version);
    }
  }
  return payload;
}

export async function POST(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const cvcePath = path.join("/");

  const isKnowledge = cvcePath.startsWith(KNOWLEDGE_PREFIX);
  if (!ALLOWED.has(cvcePath) && !isKnowledge) {
    return NextResponse.json({ error: `Unknown endpoint: ${cvcePath}` }, { status: 404 });
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), SERVER_TIMEOUT_MS);

  try {
    const res = await fetch(`${CVCE_BASE_URL}/${cvcePath}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
      cache: "no-store",
    });

    const text = await res.text();
    let payload: unknown;
    try {
      payload = text ? JSON.parse(text) : null;
    } catch {
      return NextResponse.json(
        { error: "Engine returned non-JSON response" },
        { status: 502 },
      );
    }

    // Best-effort: ensure ke_version is present at top level for portal consumers
    const enriched = ensureKeVersion(payload);
    // Fire a non-blocking probe to warm the version cache for future calls
    void getRemoteKeVersion();
    return NextResponse.json(enriched, { status: res.status });
  } catch (e) {
    const message =
      e instanceof DOMException && e.name === "AbortError"
        ? "Engine request timed out"
        : "Engine unreachable";
    console.error(`CVCE proxy /${cvcePath}:`, e);
    return NextResponse.json({ error: message }, { status: 504 });
  } finally {
    clearTimeout(timer);
  }
}

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const cvcePath = path.join("/");

  const isKnowledge = cvcePath.startsWith(KNOWLEDGE_PREFIX);
  if (!ALLOWED_GET.has(cvcePath) && !isKnowledge) {
    return NextResponse.json({ error: `Unknown endpoint: ${cvcePath}` }, { status: 404 });
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10_000);

  try {
    const qs = req.nextUrl.search ? req.nextUrl.search : "";
    const url = `${CVCE_BASE_URL}/${cvcePath}${qs}`;
    const res = await fetch(url, { signal: controller.signal, cache: "no-store" });
    const payload = await res.json();
    const enriched = ensureKeVersion(payload);
    if (cvcePath === "version") {
      // ensure the version endpoint itself populates cache
      if (payload && typeof payload === "object") {
        const v = (payload as any).ke_version || (payload as any).knowledge_version;
        if (v) cachedKeVersion = String(v);
      }
    }
    return NextResponse.json(enriched, { status: res.status });
  } catch (e) {
    const message =
      e instanceof DOMException && e.name === "AbortError"
        ? "Request timed out"
        : "Engine unreachable";
    return NextResponse.json({ error: message }, { status: 504 });
  } finally {
    clearTimeout(timer);
  }
}
