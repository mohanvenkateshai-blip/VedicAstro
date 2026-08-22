import { NextRequest, NextResponse } from "next/server";
import { cvceServiceHeaders } from "@/lib/cvce-auth";
import { consumeCvceQuota } from "@/lib/cvce-rate-limit";
import { GUEST_COOKIE, GUEST_COOKIE_OPTS, resolveChartOwnerForWrite } from "@/lib/chart-owner";
import { timelineSubjectBelongsToOwner, timelineSubjectId } from "@/lib/timeline-subject";
import type { BirthInput } from "@/lib/types";

// Allow up to 60s — CVCE cold start + heavy endpoints (positions × 12, dasha-deep)
export const maxDuration = 60;

const CVCE_BASE_URL =
  process.env.CVCE_BASE_URL ?? "https://vedicastro-cvce.fly.dev";

function authConfigurationError() {
  return NextResponse.json(
    { error: "Engine service authentication is not configured" },
    { status: 503 },
  );
}

function timelineBodyForOwner(
  body: unknown,
  cvcePath: string,
  owner: string,
): Record<string, unknown> | null {
  if (!body || typeof body !== "object" || Array.isArray(body)) return null;
  const input = body as Record<string, unknown>;
  const needsBirthIdentity = cvcePath === "timeline/query" || cvcePath.endsWith("/detail");
  if (needsBirthIdentity) {
    if (typeof input.birth_datetime !== "string" || typeof input.birth_lat !== "number" ||
        typeof input.birth_lon !== "number" || typeof input.birth_tz !== "number") return null;
    const birth = input as unknown as BirthInput;
    return { ...input, subject_id: timelineSubjectId(birth, owner) };
  }
  return typeof input.subject_id === "string" && timelineSubjectBelongsToOwner(input.subject_id, owner)
    ? input
    : null;
}

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
  "timeline/query",
  "timeline/events",
]);

const ALLOWED_GET = new Set(["places", "timezone", "version", "report/facts"]);

// KnowledgeEngine structured endpoints for server-side graph consumers.
const KNOWLEDGE_PREFIX = "knowledge/";

// Must stay comfortably under `maxDuration` (60s) — Vercel kills the function
// outright (raw 502, bypassing our catch block) if we let fetch run past that.
const SERVER_TIMEOUT_MS = 50_000;
const GUEST_RATE_WINDOW_MS = 60_000;
const GUEST_POST_LIMIT = 60;
const GUEST_GET_LIMIT = 120;

function guestClientKey(req: NextRequest): string {
  const forwarded =
    req.headers.get("x-vercel-forwarded-for") ?? req.headers.get("x-forwarded-for");
  return forwarded?.split(",")[0]?.trim() || req.headers.get("x-real-ip") || "unknown";
}

function enforceGuestQuota(req: NextRequest, method: "GET" | "POST") {
  const limit = method === "POST" ? GUEST_POST_LIMIT : GUEST_GET_LIMIT;
  const quota = consumeCvceQuota(
    `${method}:${guestClientKey(req)}`,
    limit,
    GUEST_RATE_WINDOW_MS,
  );
  if (quota.allowed) return null;
  return NextResponse.json(
    { error: "Too many engine requests. Please retry shortly." },
    { status: 429, headers: { "retry-after": String(quota.retryAfterSeconds) } },
  );
}

// Module-level cache for KE version (populated from remote /version or payloads)
let cachedKeVersion: string | null = null;

function extractKeVersion(payload: unknown): string | null {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return null;
  const data = payload as Record<string, unknown>;
  const value = data.ke_version ?? data.knowledge_version ?? data.version;
  return value == null ? null : String(value);
}

async function getRemoteKeVersion(): Promise<string | null> {
  if (cachedKeVersion) return cachedKeVersion;
  try {
    const headers = cvceServiceHeaders();
    if (!headers) return null;
    const controller = new AbortController();
    const t = setTimeout(() => controller.abort(), 8000);
    const r = await fetch(`${CVCE_BASE_URL}/version`, {
      headers,
      signal: controller.signal,
      cache: "no-store",
    });
    clearTimeout(t);
    if (r.ok) {
      const j: unknown = await r.json().catch(() => null);
      const v = extractKeVersion(j);
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
  const isTimelineMilestone = /^timeline\/milestones\/[^/]+\/(detail|resolutions)$/.test(cvcePath);
  if (!ALLOWED.has(cvcePath) && !isKnowledge && !isTimelineMilestone) {
    return NextResponse.json({ error: `Unknown endpoint: ${cvcePath}` }, { status: 404 });
  }

  const limited = enforceGuestQuota(req, "POST");
  if (limited) return limited;

  const headers = cvceServiceHeaders(true);
  if (!headers) return authConfigurationError();

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }


  let mintedGuestId: string | null = null;
  if (cvcePath.startsWith("timeline/")) {
    const resolved = await resolveChartOwnerForWrite();
    mintedGuestId = resolved.mintedGuestId;
    const scoped = timelineBodyForOwner(body, cvcePath, resolved.owner);
    if (!scoped) {
      return NextResponse.json({ error: "Timeline subject does not belong to this owner" }, { status: 403 });
    }
    body = scoped;
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), SERVER_TIMEOUT_MS);

  try {
    const res = await fetch(`${CVCE_BASE_URL}/${cvcePath}`, {
      method: "POST",
      headers,
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
    const response = NextResponse.json(enriched, { status: res.status });
    if (mintedGuestId) response.cookies.set(GUEST_COOKIE, mintedGuestId, GUEST_COOKIE_OPTS);
    return response;
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
  const limited = enforceGuestQuota(req, "GET");
  if (limited) return limited;
  const headers = cvceServiceHeaders();
  if (!headers) return authConfigurationError();

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10_000);

  try {
    const qs = req.nextUrl.search ? req.nextUrl.search : "";
    const url = `${CVCE_BASE_URL}/${cvcePath}${qs}`;
    const res = await fetch(url, { headers, signal: controller.signal, cache: "no-store" });
    const payload = await res.json();
    const enriched = ensureKeVersion(payload);
    if (cvcePath === "version") {
      // ensure the version endpoint itself populates cache
      const v = extractKeVersion(payload);
      if (v) cachedKeVersion = v;
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
