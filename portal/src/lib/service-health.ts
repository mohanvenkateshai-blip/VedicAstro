import "server-only";

import { healthCheck } from "@/lib/db";
import { isAuthConfigured, isDatabaseConfigured } from "@/lib/auth-config";

export interface ServiceProbe {
  name: string;
  url: string;
  role: string;
  ok: boolean;
  httpStatus: number;
  latencyMs: number;
  detail?: string;
  notes?: string;
}

const CVCE = process.env.CVCE_BASE_URL ?? "https://vedicastro-cvce.fly.dev";

async function probe(
  url: string,
  label: string,
  timeoutMs = 15_000,
): Promise<Omit<ServiceProbe, "name" | "url" | "role">> {
  const start = Date.now();
  try {
    const res = await fetch(url, {
      cache: "no-store",
      signal: AbortSignal.timeout(timeoutMs),
    });
    const latencyMs = Date.now() - start;
    let detail: string | undefined;
    if (res.ok) {
      try {
        const json = await res.json();
        if (json.status === "ok") detail = `engine ${json.engine ?? "ok"}`;
        else if (json.graph_rag?.rules_source)
          detail = `rules: ${json.graph_rag.rules_source}`;
        else if (json.available != null)
          detail = json.available ? "available" : "unavailable";
      } catch {
        detail = "OK";
      }
    } else {
      detail = await res.text().catch(() => `HTTP ${res.status}`);
    }
    return {
      ok: res.ok,
      httpStatus: res.status,
      latencyMs,
      detail: detail?.slice(0, 120),
    };
  } catch (e) {
    return {
      ok: false,
      httpStatus: 0,
      latencyMs: Date.now() - start,
      detail: e instanceof Error ? e.message : "unreachable",
    };
  }
}

/** Live health probes — used by /status page. */
export async function getLiveServiceHealth(): Promise<ServiceProbe[]> {
  const [cvce, predict, muhurta, portal, dbOk] = await Promise.all([
    probe(`${CVCE}/health`, "CVCE"),
    probe(`${CVCE}/predict/health`, "predict"),
    probe("https://muhurtha.uvwx.me/", "Muhurta"),
    probe(
      process.env.VERCEL_URL
        ? `https://${process.env.VERCEL_URL}/`
        : "https://portal-omega-two-10.vercel.app/",
      "Portal",
    ),
    healthCheck(),
  ]);

  let cvceNotes = cvce.detail;
  if (predict.ok && predict.detail) {
    cvceNotes = [cvce.detail, predict.detail].filter(Boolean).join(" · ");
  }

  return [
    {
      name: "Portal",
      url: "https://portal-omega-two-10.vercel.app",
      role: "Next.js UI (Vercel)",
      ...portal,
      notes: "/status",
    },
    {
      name: "CVCE",
      url: CVCE,
      role: "Calculation engine (Fly LHR)",
      ...cvce,
      notes: cvceNotes,
    },
    {
      name: "Muhūrta",
      url: "https://muhurtha.uvwx.me",
      role: "Frozen standalone (Fly IAD)",
      ...muhurta,
      notes: "iframe embed only",
    },
    {
      name: "Neon Postgres",
      url: "https://neon.tech",
      role: "Saved charts + user roles",
      ok: dbOk,
      httpStatus: dbOk ? 200 : 0,
      latencyMs: 0,
      detail: isDatabaseConfigured()
        ? dbOk
          ? "connected"
          : "DATABASE_URL set but unreachable"
        : "DATABASE_URL not set",
      notes: isAuthConfigured() ? "auth configured" : "auth env missing",
    },
  ];
}
