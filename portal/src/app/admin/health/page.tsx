import { requireSession } from "@/lib/auth/index";
import { getDeepHealth, type DeepHealthCheck } from "@/lib/service-health";
import { HealthAutoRefresh } from "@/components/admin/HealthAutoRefresh";

export const dynamic = "force-dynamic";

const STATUS_STYLE: Record<string, { dot: string; text: string; label: string }> = {
  healthy: { dot: "bg-emerald-500", text: "text-emerald-500", label: "All systems operational" },
  degraded: { dot: "bg-amber-500", text: "text-amber-500", label: "Degraded — non-core issue" },
  down: { dot: "bg-red-500", text: "text-red-500", label: "DOWN — core failure" },
  unreachable: { dot: "bg-red-600", text: "text-red-600", label: "CVCE unreachable" },
};

function TierLabel({ tier }: { tier: number }) {
  const map: Record<number, string> = { 0: "core", 1: "supporting", 2: "peripheral" };
  return <span className="text-[10px] font-mono uppercase text-text-muted">{map[tier] ?? `t${tier}`}</span>;
}

function CheckRow({ c }: { c: DeepHealthCheck }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-hairline px-3 py-2.5">
      <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${c.ok ? "bg-emerald-500" : "bg-red-500"}`} />
      <span className="font-mono text-sm font-medium min-w-[150px]">{c.name}</span>
      <TierLabel tier={c.tier} />
      <span className="text-xs text-text-muted flex-1 truncate">{c.detail}</span>
      <span className="text-[11px] font-mono text-text-muted shrink-0">{c.ms.toFixed(0)}ms</span>
    </div>
  );
}

export default async function AdminHealthPage() {
  await requireSession("admin");
  const health = await getDeepHealth();
  const s = STATUS_STYLE[health.status] ?? STATUS_STYLE.unreachable;
  const mem = health.memory;

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight font-serif">System health</h1>
        <p className="mt-2 text-sm text-text-muted max-w-xl">
          Deep per-subsystem probes from CVCE <code className="font-mono text-xs">/health/deep</code> —
          actively exercises each engine, not just a port check.
        </p>
      </div>

      {/* Overall status banner */}
      <div className="rounded-2xl border border-hairline bg-card p-5 mb-4">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-3">
            <span className={`h-3.5 w-3.5 rounded-full ${s.dot} ${health.status !== "healthy" ? "animate-pulse" : ""}`} />
            <span className={`text-lg font-semibold ${s.text}`}>{s.label}</span>
          </div>
          <HealthAutoRefresh seconds={30} />
        </div>
        {health.error && <p className="mt-2 text-sm text-red-500 font-mono">{health.error}</p>}
        <p className="mt-2 text-[11px] font-mono text-text-muted">
          probed {health.timestamp} · round-trip {health.latencyMs}ms
        </p>
      </div>

      {/* Memory gauge (OOM early-warning — this machine has OOM'd before) */}
      {mem.rss_mb != null && (
        <div className="rounded-2xl border border-hairline bg-card p-5 mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Memory</span>
            <span className="text-xs font-mono text-text-muted">
              {mem.rss_mb}MB{mem.limit_mb ? ` / ${mem.limit_mb}MB` : ""}
              {mem.headroom_pct != null ? ` · ${mem.headroom_pct}% free` : ""}
            </span>
          </div>
          {mem.limit_mb && (
            <div className="h-2.5 rounded-full bg-hairline/40 overflow-hidden">
              <div
                className={`h-full rounded-full ${
                  (mem.headroom_pct ?? 100) < 12 ? "bg-red-500" : (mem.headroom_pct ?? 100) < 25 ? "bg-amber-500" : "bg-emerald-500"
                }`}
                style={{ width: `${Math.min(100, (mem.rss_mb / mem.limit_mb) * 100)}%` }}
              />
            </div>
          )}
        </div>
      )}

      {/* Per-check detail */}
      <div className="space-y-2">
        {health.checks.length === 0 ? (
          <p className="text-sm text-text-muted">No checks returned{health.error ? " (CVCE unreachable)" : ""}.</p>
        ) : (
          health.checks.map((c) => <CheckRow key={c.name} c={c} />)
        )}
      </div>

      <p className="mt-6 text-[11px] font-mono text-text-muted">
        core (tier 0) failing → product down · supporting (tier 1) failing → degraded but usable.
        An external synthetic monitor pings this endpoint on a schedule and alerts on degradation.
      </p>
    </div>
  );
}
