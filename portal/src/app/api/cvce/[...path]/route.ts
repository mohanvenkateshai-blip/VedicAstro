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
  "dashas",
  "gochar",
  "kp-system",
  "varshaphala",
  "koota-match",
  "positions",
  "yogas",
  "special-points",
]);

const ALLOWED_GET = new Set(["places"]);

const SERVER_TIMEOUT_MS = 120_000;

export async function POST(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const cvcePath = path.join("/");

  if (!ALLOWED.has(cvcePath)) {
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

    return NextResponse.json(payload, { status: res.status });
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

  if (!ALLOWED_GET.has(cvcePath)) {
    return NextResponse.json({ error: `Unknown endpoint: ${cvcePath}` }, { status: 404 });
  }

  const q = req.nextUrl.searchParams.get("q") ?? "";
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10_000);

  try {
    const res = await fetch(
      `${CVCE_BASE_URL}/${cvcePath}?q=${encodeURIComponent(q)}`,
      { signal: controller.signal, cache: "no-store" },
    );
    const payload = await res.json();
    return NextResponse.json(payload, { status: res.status });
  } catch (e) {
    const message =
      e instanceof DOMException && e.name === "AbortError"
        ? "Places search timed out"
        : "Engine unreachable";
    return NextResponse.json({ error: message }, { status: 504 });
  } finally {
    clearTimeout(timer);
  }
}
