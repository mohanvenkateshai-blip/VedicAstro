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

/** Live GraphRAG status from CVCE /predict/health (graphify output at runtime). */
export interface GraphRagStatus {
  ok: boolean;
  latencyMs: number;
  available: boolean;
  rulesSource: "graph" | "hardcoded" | "unknown";
  graphAsRulesEnv: boolean;
  nodes?: number;
  links?: number;
  hyperedges?: number;
  communities?: number;
  engineVersion?: string;
  error?: string;
}

const CVCE = process.env.CVCE_BASE_URL ?? "https://vedicastro-cvce.fly.dev";

interface PredictHealthJson {
  engine?: string;
  version?: string;
  available?: boolean;
  graph_rag?: {
    available?: boolean;
    rules_source?: string;
    graph_as_rules_env?: boolean;
    stats?: {
      nodes?: number;
      links?: number;
      hyperedges?: number;
      communities?: number;
      loaded?: boolean;
    };
  };
}

async function probePredictHealth(timeoutMs = 15_000): Promise<{
  ok: boolean;
  latencyMs: number;
  json: PredictHealthJson | null;
  error?: string;
}> {
  const start = Date.now();
  try {
    const res = await fetch(`${CVCE}/predict/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(timeoutMs),
    });
    const latencyMs = Date.now() - start;
    if (!res.ok) {
      return {
        ok: false,
        latencyMs,
        json: null,
        error: `HTTP ${res.status}`,
      };
    }
    const json = (await res.json()) as PredictHealthJson;
    return { ok: true, latencyMs, json };
  } catch (e) {
    return {
      ok: false,
      latencyMs: Date.now() - start,
      json: null,
      error: e instanceof Error ? e.message : "unreachable",
    };
  }
}

/** Probe CVCE GraphRAG — graph node count, rules source, env gate. */
export async function getGraphRagStatus(): Promise<GraphRagStatus> {
  const { ok, latencyMs, json, error } = await probePredictHealth();
  if (!ok || !json?.graph_rag) {
    return {
      ok: false,
      latencyMs,
      available: false,
      rulesSource: "unknown",
      graphAsRulesEnv: false,
      error: error ?? "predict/health unavailable",
    };
  }

  const gr = json.graph_rag;
  const stats = gr.stats;
  const rules = gr.rules_source === "graph" ? "graph" : gr.rules_source === "hardcoded" ? "hardcoded" : "unknown";

  return {
    ok: gr.available === true && stats?.loaded === true,
    latencyMs,
    available: gr.available === true,
    rulesSource: rules,
    graphAsRulesEnv: gr.graph_as_rules_env === true,
    nodes: stats?.nodes,
    links: stats?.links,
    hyperedges: stats?.hyperedges,
    communities: stats?.communities,
    engineVersion: json.version,
  };
}

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
  const [cvce, graphRag, muhurta, portal, dbOk] = await Promise.all([
    probe(`${CVCE}/health`, "CVCE"),
    getGraphRagStatus(),
    probe("https://muhurtha.uvwx.me/", "Muhurta"),
    probe(
      process.env.VERCEL_URL
        ? `https://${process.env.VERCEL_URL}/`
        : "https://portal-omega-two-10.vercel.app/",
      "Portal",
    ),
    healthCheck(),
  ]);

  const graphDetail = graphRag.ok
    ? `${graphRag.nodes ?? "?"} nodes · ${graphRag.links ?? "?"} links · rules: ${graphRag.rulesSource}`
    : graphRag.error ?? "graph unavailable";

  const cvceNotes = [cvce.detail, graphDetail].filter(Boolean).join(" · ");

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
