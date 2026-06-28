"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Trash2, ExternalLink, ChevronUp, ChevronDown, ArrowUpDown } from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ChartRow {
  id: string;
  name: string;
  birth_date: string;
  birth_time: string;
  place: string;
  lat: string;
  lon: string;
  tz: string;
  sort_order: number;
  created_at: string;
}

type SortKey = "name" | "birth_date" | "birth_time" | "place" | "created_at" | "sort_order";
type SortDir = "asc" | "desc";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric", month: "short", year: "numeric",
  });
}

function chartHref(c: ChartRow): string {
  const p = new URLSearchParams({
    name: c.name,
    date: c.birth_date,
    time: c.birth_time,
    place: c.place,
    lat: c.lat,
    lon: c.lon,
    tz: c.tz,
  });
  return `/chart?${p.toString()}`;
}

// ── Sort header ───────────────────────────────────────────────────────────────

function SortTh({ label, sortKey, current, dir, onSort }: {
  label: string; sortKey: SortKey; current: SortKey; dir: SortDir;
  onSort: (k: SortKey) => void;
}) {
  const active = current === sortKey;
  return (
    <th
      className="text-left text-[10px] font-mono uppercase tracking-wider text-text-muted py-2.5 px-3 cursor-pointer select-none hover:text-text-main transition-colors whitespace-nowrap"
      onClick={() => onSort(sortKey)}
    >
      <span className="flex items-center gap-1">
        {label}
        {active
          ? dir === "asc" ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />
          : <ArrowUpDown className="w-3 h-3 opacity-30" />
        }
      </span>
    </th>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function DashboardTable() {
  const router = useRouter();
  const [charts, setCharts] = useState<ChartRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [sortKey, setSortKey] = useState<SortKey>("sort_order");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const reload = useCallback(async () => {
    try {
      const res = await fetch("/api/charts");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setCharts(Array.isArray(data) ? data : []);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load charts");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { reload(); }, [reload]);

  // ── Sorting ───────────────────────────────────────────────────────────────

  function handleSort(key: SortKey) {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(key); setSortDir("asc"); }
  }

  const sorted = [...charts].sort((a, b) => {
    let av: string | number = "", bv: string | number = "";
    switch (sortKey) {
      case "name":       av = a.name.toLowerCase();  bv = b.name.toLowerCase(); break;
      case "birth_date": av = a.birth_date;           bv = b.birth_date; break;
      case "birth_time": av = a.birth_time;           bv = b.birth_time; break;
      case "place":      av = a.place.toLowerCase();  bv = b.place.toLowerCase(); break;
      case "created_at": av = a.created_at;           bv = b.created_at; break;
      case "sort_order": av = a.sort_order;           bv = b.sort_order; break;
    }
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return sortDir === "asc" ? cmp : -cmp;
  });

  // ── Selection ─────────────────────────────────────────────────────────────

  const allSelected = sorted.length > 0 && selected.size === sorted.length;
  function toggleAll() { setSelected(allSelected ? new Set() : new Set(sorted.map((c) => c.id))); }
  function toggleOne(id: string) {
    setSelected((prev) => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });
  }

  // ── Actions ───────────────────────────────────────────────────────────────

  async function handleDeleteSelected() {
    if (!window.confirm(`Delete ${selected.size} chart${selected.size > 1 ? "s" : ""}?`)) return;
    await Promise.all([...selected].map((id) => fetch(`/api/charts/${id}`, { method: "DELETE" })));
    setSelected(new Set());
    reload();
  }

  async function handleDelete(id: string) {
    await fetch(`/api/charts/${id}`, { method: "DELETE" });
    setSelected((prev) => { const n = new Set(prev); n.delete(id); return n; });
    reload();
  }

  async function handleMove(id: string, direction: "up" | "down") {
    setSortKey("sort_order");
    setSortDir("asc");
    await fetch(`/api/charts/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ direction }),
    });
    reload();
  }

  function handleLoad(c: ChartRow) { router.push(chartHref(c)); }

  // ── States ────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="py-16 text-center text-sm text-text-muted animate-pulse">
        Loading charts…
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-danger/30 bg-danger/5 p-5 text-sm text-danger">
        {error.includes("fetch") || error.includes("SUPABASE")
          ? "Database not connected yet — add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to Vercel."
          : error}
      </div>
    );
  }

  if (charts.length === 0) {
    return (
      <div className="py-16 text-center space-y-2">
        <p className="text-sm text-text-muted">No saved charts yet.</p>
        <a href="/chart" className="text-sm text-accent hover:underline">Cast your first chart →</a>
      </div>
    );
  }

  const inOrderMode = sortKey === "sort_order";

  return (
    <div className="space-y-3">
      {/* Bulk action bar */}
      {selected.size > 0 && (
        <div className="flex items-center gap-3 px-3 py-2 rounded-xl border border-danger/30 bg-danger/5">
          <span className="text-sm text-danger font-mono">{selected.size} selected</span>
          <button onClick={handleDeleteSelected}
            className="flex items-center gap-1.5 text-sm text-danger hover:text-danger/80 transition-colors">
            <Trash2 className="w-3.5 h-3.5" /> Delete selected
          </button>
          <button onClick={() => setSelected(new Set())}
            className="ml-auto text-xs text-text-muted hover:text-text-main transition-colors">
            Clear selection
          </button>
        </div>
      )}

      {/* Table */}
      <div className="rounded-xl border border-hairline overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b border-hairline bg-card/60">
              <tr>
                <th className="py-2.5 pl-3 pr-1 w-8">
                  <input type="checkbox" checked={allSelected} onChange={toggleAll}
                    className="rounded accent-[var(--color-accent)] cursor-pointer" title="Select all" />
                </th>
                <SortTh label="Name"    sortKey="name"       current={sortKey} dir={sortDir} onSort={handleSort} />
                <SortTh label="Date"    sortKey="birth_date"  current={sortKey} dir={sortDir} onSort={handleSort} />
                <SortTh label="Time"    sortKey="birth_time"  current={sortKey} dir={sortDir} onSort={handleSort} />
                <SortTh label="Place"   sortKey="place"       current={sortKey} dir={sortDir} onSort={handleSort} />
                <SortTh label="Saved"   sortKey="created_at"  current={sortKey} dir={sortDir} onSort={handleSort} />
                <th className="py-2.5 px-3 text-right text-[10px] font-mono uppercase tracking-wider text-text-muted">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((c, idx) => {
                const isSel = selected.has(c.id);
                return (
                  <tr key={c.id} className="border-b border-hairline last:border-0 transition-colors"
                    style={{ backgroundColor: isSel ? "color-mix(in srgb, var(--color-accent) 6%, transparent)" : undefined }}>
                    <td className="py-3 pl-3 pr-1">
                      <input type="checkbox" checked={isSel} onChange={() => toggleOne(c.id)}
                        className="rounded accent-[var(--color-accent)] cursor-pointer" />
                    </td>
                    <td className="py-3 px-3">
                      <button onClick={() => handleLoad(c)}
                        className="text-sm font-medium text-text-main hover:text-accent transition-colors text-left">
                        {c.name || "Unnamed"}
                      </button>
                    </td>
                    <td className="py-3 px-3 text-sm font-mono text-text-muted tabular-nums whitespace-nowrap">
                      {c.birth_date}
                    </td>
                    <td className="py-3 px-3 text-sm font-mono text-text-muted tabular-nums">
                      {c.birth_time}
                    </td>
                    <td className="py-3 px-3 text-sm text-text-muted max-w-[180px] truncate">
                      {c.place || `${c.lat}, ${c.lon}`}
                    </td>
                    <td className="py-3 px-3 text-[11px] font-mono text-text-muted whitespace-nowrap">
                      {fmtDate(c.created_at)}
                    </td>
                    <td className="py-3 px-3">
                      <div className="flex items-center justify-end gap-1">
                        <button onClick={() => handleMove(c.id, "up")}
                          disabled={!inOrderMode || idx === 0} title="Move up"
                          className="p-1.5 rounded-lg text-text-muted hover:text-text-main hover:bg-white/5 disabled:opacity-20 disabled:cursor-default transition-colors">
                          <ChevronUp className="w-3.5 h-3.5" />
                        </button>
                        <button onClick={() => handleMove(c.id, "down")}
                          disabled={!inOrderMode || idx === sorted.length - 1} title="Move down"
                          className="p-1.5 rounded-lg text-text-muted hover:text-text-main hover:bg-white/5 disabled:opacity-20 disabled:cursor-default transition-colors">
                          <ChevronDown className="w-3.5 h-3.5" />
                        </button>
                        <button onClick={() => handleLoad(c)} title="Open chart"
                          className="p-1.5 rounded-lg text-text-muted hover:text-accent hover:bg-white/5 transition-colors">
                          <ExternalLink className="w-3.5 h-3.5" />
                        </button>
                        <button onClick={() => handleDelete(c.id)} title="Delete"
                          className="p-1.5 rounded-lg text-text-muted hover:text-danger hover:bg-danger/10 transition-colors">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <p className="text-[10px] font-mono text-text-muted px-1">
        {charts.length} chart{charts.length !== 1 ? "s" : ""} · saved to Supabase ·{" "}
        <span className="opacity-60">click column headers to sort · ↑↓ reorders when in default order</span>
      </p>
    </div>
  );
}
