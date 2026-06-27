import { getLiveServiceHealth, getGraphRagStatus } from "@/lib/service-health";
import { Card } from "@/components/ui/Card";
import featureProgress from "../../../docs/feature-progress.json";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Live Status — VedicShastra AI",
  description: "Real-time service health for Portal, CVCE, and Muhūrta.",
};

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block h-2.5 w-2.5 rounded-full ${ok ? "bg-success" : "bg-danger"}`}
      aria-hidden
    />
  );
}

export default async function LiveStatusPage() {
  const checkedAt = new Date().toISOString();
  const [services, graphRag] = await Promise.all([
    getLiveServiceHealth(),
    getGraphRagStatus(),
  ]);
  const features = featureProgress.features ?? [];
  const done = features.filter((f) => f.status === "Done").length;
  const partial = features.filter((f) => f.status === "Partial").length;

  const phases = [
    { name: "0–1", label: "Consolidation & monorepo", status: "complete" },
    { name: "2", label: "CVCE recovery", status: "complete" },
    { name: "3", label: "Gap analysis", status: "complete" },
    { name: "4", label: "GraphRAG rules source", status: "complete" },
    { name: "5+", label: "Feature build-out", status: "in progress" },
  ];

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <div className="mb-8">
        <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight">
          Live status
        </h1>
        <p className="mt-2 text-sm text-text-muted">
          Probed at{" "}
          <time className="font-mono text-text-main" dateTime={checkedAt}>
            {new Date(checkedAt).toLocaleString()}
          </time>
          . Refreshes on each visit.
        </p>
      </div>

      <section className="mb-8">
        <h2 className="text-xs font-mono uppercase tracking-wider text-text-muted mb-3">
          Services
        </h2>
        <div className="space-y-3">
          {services.map((s) => (
            <Card key={s.name} className="p-4 flex flex-wrap items-center gap-x-4 gap-y-2">
              <StatusDot ok={s.ok} />
              <div className="flex-1 min-w-[200px]">
                <div className="font-medium">{s.name}</div>
                <div className="text-xs text-text-muted">{s.role}</div>
              </div>
              <div className="font-mono text-sm tabular-nums">
                {s.ok ? (
                  <span className="text-success">HTTP {s.httpStatus}</span>
                ) : (
                  <span className="text-danger">
                    {s.httpStatus ? `HTTP ${s.httpStatus}` : "offline"}
                  </span>
                )}
                <span className="text-text-muted ml-2">{s.latencyMs}ms</span>
              </div>
              {s.detail ? (
                <div className="w-full text-xs font-mono text-text-muted truncate">
                  {s.detail}
                  {s.notes ? ` · ${s.notes}` : ""}
                </div>
              ) : null}
              <a
                href={s.url}
                className="text-xs text-accent hover:underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                {s.url.replace(/^https:\/\//, "")}
              </a>
            </Card>
          ))}
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-xs font-mono uppercase tracking-wider text-text-muted mb-3">
          Knowledge graph (GraphRAG)
        </h2>
        <Card className="p-4 space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <StatusDot ok={graphRag.ok} />
            <div className="flex-1 min-w-[200px]">
              <div className="font-medium">
                {graphRag.ok ? "Graph loaded on CVCE" : "Graph unavailable"}
              </div>
              <div className="text-xs text-text-muted">
                Offline graphify → <code className="font-mono">graph.json</code> → runtime GraphRAG
              </div>
            </div>
            <span className="font-mono text-xs text-text-muted tabular-nums">
              {graphRag.latencyMs}ms
            </span>
          </div>
          {graphRag.ok ? (
            <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
              <div>
                <dt className="text-text-muted text-xs">Nodes</dt>
                <dd className="font-mono font-medium">{graphRag.nodes ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-text-muted text-xs">Links</dt>
                <dd className="font-mono font-medium">{graphRag.links ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-text-muted text-xs">Communities</dt>
                <dd className="font-mono font-medium">{graphRag.communities ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-text-muted text-xs">Rules source</dt>
                <dd className="font-mono font-medium">{graphRag.rulesSource}</dd>
              </div>
            </dl>
          ) : (
            <p className="text-sm text-danger">{graphRag.error}</p>
          )}
          <p className="text-xs text-text-muted border-t border-hairline pt-3">
            After <code className="font-mono">/graphify raw --update</code>, sync deploy copy:{" "}
            <code className="font-mono">./scripts/sync-graph.sh</code>
            {" · "}
            optional <code className="font-mono">--deploy</code> to push CVCE.
            Env <code className="font-mono">CVCE_GRAPH_AS_RULES=1</code>{" "}
            {graphRag.graphAsRulesEnv ? "is on" : "is off"} on Fly.
          </p>
        </Card>
      </section>

      <section className="mb-8">
        <h2 className="text-xs font-mono uppercase tracking-wider text-text-muted mb-3">
          Roadmap phases
        </h2>
        <Card className="p-4">
          <ul className="space-y-2 text-sm">
            {phases.map((p) => (
              <li key={p.name} className="flex items-center gap-3">
                <span
                  className={`font-mono text-xs px-2 py-0.5 rounded-md ${
                    p.status === "complete"
                      ? "bg-success/10 text-success"
                      : "bg-warning/10 text-warning"
                  }`}
                >
                  {p.status === "complete" ? "done" : "active"}
                </span>
                <span className="font-mono text-text-muted">Phase {p.name}</span>
                <span>{p.label}</span>
              </li>
            ))}
          </ul>
        </Card>
      </section>

      <section>
        <h2 className="text-xs font-mono uppercase tracking-wider text-text-muted mb-3">
          Feature tracker
        </h2>
        <Card className="p-4">
          <p className="text-sm text-text-muted mb-3">
            <span className="font-mono text-success">{done}</span> done ·{" "}
            <span className="font-mono text-warning">{partial}</span> partial ·{" "}
            <span className="font-mono">{features.length}</span> total
            {featureProgress.updated ? (
              <>
                {" "}
                · updated{" "}
                <time dateTime={featureProgress.updated}>
                  {new Date(featureProgress.updated).toLocaleDateString()}
                </time>
              </>
            ) : null}
          </p>
          <p className="text-xs text-text-muted">
            Full matrix:{" "}
            <code className="font-mono bg-card px-1 rounded">portal/docs/feature-progress.json</code>
            {" · "}
            Architecture notes:{" "}
            <code className="font-mono bg-card px-1 rounded">STATUS.md</code> in the repo root.
          </p>
        </Card>
      </section>

      <p className="mt-8 text-xs text-text-muted text-center">
        Legacy agent dashboard (static):{" "}
        <code className="font-mono">portal/docs/dashboard.html</code> — open locally with{" "}
        <code className="font-mono">npx serve portal/docs</code>
      </p>
    </div>
  );
}
