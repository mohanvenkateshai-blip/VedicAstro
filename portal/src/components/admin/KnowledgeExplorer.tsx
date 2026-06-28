"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Search, Network, BookOpen, Loader2 } from "lucide-react";

type Stats = {
  sources: number;
  nodes: number;
  links: number;
  lastRun: { provider?: string; completed_at?: string; node_count?: number } | null;
};

type Source = { canonical_name: string; bytes: number; book_family: string | null };

type NodeRow = {
  id: string;
  label: string | null;
  file_type: string | null;
  source_file: string | null;
  community: number | null;
  properties: Record<string, unknown>;
};

type LinkRow = { id: string; source_id: string; target_id: string; relation: string | null };

type Community = { community: number; count: number };

function fmtBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function MiniGraph({
  centerId,
  centerLabel,
  neighbors,
  links,
  onSelect,
}: {
  centerId: string;
  centerLabel: string;
  neighbors: NodeRow[];
  links: LinkRow[];
  onSelect: (id: string) => void;
}) {
  const cx = 160;
  const cy = 120;
  const r = 72;
  const positions = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>();
    map.set(centerId, { x: cx, y: cy });
    neighbors.forEach((n, i) => {
      const a = (i / Math.max(neighbors.length, 1)) * Math.PI * 2 - Math.PI / 2;
      map.set(n.id, { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) });
    });
    return map;
  }, [centerId, neighbors, cx, cy, r]);

  return (
    <svg viewBox="0 0 320 240" className="w-full h-48 rounded-xl bg-[color-mix(in_srgb,var(--color-surface)_90%,transparent)] border border-hairline">
      {links.map((l) => {
        const a = positions.get(l.source_id);
        const b = positions.get(l.target_id);
        if (!a || !b) return null;
        return (
          <line
            key={l.id}
            x1={a.x}
            y1={a.y}
            x2={b.x}
            y2={b.y}
            stroke="var(--color-accent)"
            strokeOpacity={0.35}
            strokeWidth={1}
          />
        );
      })}
      {neighbors.map((n) => {
        const p = positions.get(n.id);
        if (!p) return null;
        return (
          <g key={n.id} className="cursor-pointer" onClick={() => onSelect(n.id)}>
            <circle cx={p.x} cy={p.y} r={10} fill="var(--color-surface)" stroke="var(--color-accent)" strokeWidth={1.5} />
            <title>{n.label ?? n.id}</title>
          </g>
        );
      })}
      <circle cx={cx} cy={cy} r={14} fill="var(--color-accent)" />
      <text x={cx} y={cy + 28} textAnchor="middle" className="fill-[var(--color-text-muted)] text-[9px]">
        {(centerLabel || centerId).slice(0, 36)}
      </text>
    </svg>
  );
}

export function KnowledgeExplorer() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [communities, setCommunities] = useState<Community[]>([]);
  const [nodes, setNodes] = useState<NodeRow[]>([]);
  const [selected, setSelected] = useState<NodeRow | null>(null);
  const [links, setLinks] = useState<LinkRow[]>([]);
  const [neighbors, setNeighbors] = useState<NodeRow[]>([]);
  const [q, setQ] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [communityFilter, setCommunityFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadNeighbors = useCallback(async (id: string) => {
    const res = await fetch(`/api/admin/corpus/neighbors?id=${encodeURIComponent(id)}`);
    if (!res.ok) throw new Error((await res.json()).error ?? "neighbor fetch failed");
    const data = await res.json();
    setSelected(data.node);
    setLinks(data.links ?? []);
    setNeighbors(data.neighbors ?? []);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const [sRes, srcRes, cRes] = await Promise.all([
          fetch("/api/admin/corpus/stats"),
          fetch("/api/admin/corpus/sources"),
          fetch("/api/admin/corpus/nodes?mode=communities"),
        ]);
        if (!sRes.ok) throw new Error("Unauthorized or corpus not synced");
        setStats(await sRes.json());
        if (srcRes.ok) setSources(await srcRes.json());
        if (cRes.ok) setCommunities(await cRes.json());
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const runSearch = useCallback(async () => {
    setSearching(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (q.trim()) params.set("q", q.trim());
      if (sourceFilter) params.set("source", sourceFilter);
      if (communityFilter) params.set("community", communityFilter);
      params.set("limit", "100");
      const res = await fetch(`/api/admin/corpus/nodes?${params}`);
      if (!res.ok) throw new Error((await res.json()).error ?? "search failed");
      const data: NodeRow[] = await res.json();
      setNodes(data);
      if (data[0]) await loadNeighbors(data[0].id);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSearching(false);
    }
  }, [q, sourceFilter, communityFilter, loadNeighbors]);

  useEffect(() => {
    if (!loading) runSearch();
  }, [loading]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-text-muted gap-2">
        <Loader2 className="h-5 w-5 animate-spin" />
        Loading corpus vault…
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Sources", value: stats.sources, icon: BookOpen },
            { label: "Nodes", value: stats.nodes, icon: Network },
            { label: "Links", value: stats.links, icon: Network },
            {
              label: "Last sync",
              value: stats.lastRun?.completed_at
                ? new Date(stats.lastRun.completed_at).toLocaleDateString()
                : "—",
              icon: BookOpen,
            },
          ].map(({ label, value, icon: Icon }) => (
            <div key={label} className="rounded-xl border border-hairline bg-surface/50 px-4 py-3">
              <div className="flex items-center gap-2 text-xs text-text-muted">
                <Icon className="h-3.5 w-3.5" />
                {label}
              </div>
              <div className="mt-1 text-lg font-semibold tabular-nums">{value}</div>
            </div>
          ))}
        </div>
      )}

      <div className="flex flex-wrap gap-2 items-end">
        <label className="flex-1 min-w-[200px]">
          <span className="text-xs text-text-muted">Search nodes</span>
          <div className="relative mt-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && runSearch()}
              placeholder="planet, yoga, dasha…"
              className="w-full rounded-xl border border-hairline bg-surface pl-9 pr-3 py-2 text-sm"
            />
          </div>
        </label>
        <label>
          <span className="text-xs text-text-muted">Source</span>
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            className="mt-1 block rounded-xl border border-hairline bg-surface px-3 py-2 text-sm min-w-[160px]"
          >
            <option value="">All sources</option>
            {sources.map((s) => (
              <option key={s.canonical_name} value={`${s.canonical_name}.md`}>
                {s.canonical_name}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="text-xs text-text-muted">Community</span>
          <select
            value={communityFilter}
            onChange={(e) => setCommunityFilter(e.target.value)}
            className="mt-1 block rounded-xl border border-hairline bg-surface px-3 py-2 text-sm min-w-[120px]"
          >
            <option value="">Any</option>
            {communities.slice(0, 24).map((c) => (
              <option key={c.community} value={String(c.community)}>
                #{c.community} ({c.count})
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={runSearch}
          disabled={searching}
          className="rounded-xl bg-accent px-4 py-2 text-sm font-medium text-[#1a1206] hover:bg-accent-strong disabled:opacity-60"
        >
          {searching ? "Searching…" : "Search"}
        </button>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="rounded-xl border border-hairline overflow-hidden">
          <div className="px-4 py-2 border-b border-hairline text-xs text-text-muted uppercase tracking-wide">
            Nodes ({nodes.length})
          </div>
          <ul className="max-h-[420px] overflow-y-auto divide-y divide-hairline">
            {nodes.map((n) => (
              <li key={n.id}>
                <button
                  type="button"
                  onClick={() => loadNeighbors(n.id)}
                  className={`w-full text-left px-4 py-2.5 text-sm hover:bg-surface/80 transition-colors ${
                    selected?.id === n.id ? "bg-accent/10" : ""
                  }`}
                >
                  <div className="font-medium line-clamp-1">{n.label ?? n.id}</div>
                  <div className="text-xs text-text-muted mt-0.5">
                    {n.file_type ?? "node"}
                    {n.community != null ? ` · community ${n.community}` : ""}
                    {n.source_file ? ` · ${n.source_file.replace(/\.md$/, "")}` : ""}
                  </div>
                </button>
              </li>
            ))}
            {!nodes.length && (
              <li className="px-4 py-8 text-center text-sm text-text-muted">
                No nodes — run <code className="text-xs">scripts/supabase-corpus-sync.py</code>
              </li>
            )}
          </ul>
        </div>

        <div className="space-y-4">
          {selected ? (
            <>
              <MiniGraph
                centerId={selected.id}
                centerLabel={selected.label ?? selected.id}
                neighbors={neighbors}
                links={links}
                onSelect={(id) => loadNeighbors(id)}
              />
              <div className="rounded-xl border border-hairline p-4">
                <h3 className="font-semibold">{selected.label ?? selected.id}</h3>
                <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
                  <dt className="text-text-muted">ID</dt>
                  <dd className="font-mono truncate">{selected.id}</dd>
                  <dt className="text-text-muted">Type</dt>
                  <dd>{selected.file_type ?? "—"}</dd>
                  <dt className="text-text-muted">Source</dt>
                  <dd className="truncate">{selected.source_file ?? "—"}</dd>
                  <dt className="text-text-muted">Community</dt>
                  <dd>{selected.community ?? "—"}</dd>
                </dl>
                {Object.keys(selected.properties).length > 0 && (
                  <pre className="mt-3 max-h-32 overflow-auto rounded-lg bg-surface p-2 text-[10px] font-mono text-text-muted">
                    {JSON.stringify(selected.properties, null, 2)}
                  </pre>
                )}
              </div>
              <div className="rounded-xl border border-hairline">
                <div className="px-4 py-2 border-b border-hairline text-xs text-text-muted">
                  Neighbors ({neighbors.length})
                </div>
                <ul className="max-h-48 overflow-y-auto divide-y divide-hairline">
                  {neighbors.map((n) => (
                    <li key={n.id}>
                      <button
                        type="button"
                        onClick={() => loadNeighbors(n.id)}
                        className="w-full text-left px-4 py-2 text-sm hover:bg-surface/80"
                      >
                        {n.label ?? n.id}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          ) : (
            <div className="rounded-xl border border-hairline p-8 text-center text-text-muted text-sm">
              Select a node to explore its neighborhood
            </div>
          )}

          {sources.length > 0 && (
            <div className="rounded-xl border border-hairline">
              <div className="px-4 py-2 border-b border-hairline text-xs text-text-muted">
                Corpus sources ({sources.length})
              </div>
              <ul className="max-h-40 overflow-y-auto divide-y divide-hairline text-xs">
                {sources.map((s) => (
                  <li key={s.canonical_name} className="px-4 py-2 flex justify-between gap-2">
                    <span>{s.canonical_name}</span>
                    <span className="text-text-muted">{fmtBytes(s.bytes)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
