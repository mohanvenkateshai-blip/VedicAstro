"use client";

import { useState, useEffect, useCallback } from "react";
import { Clock, Loader, AlertCircle, ChevronDown, ChevronUp } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import type { ChartData } from "@/lib/types";
import { postCvce } from "@/lib/cvce-client";
import { DashaSeriesChart } from "./DashaSeriesChart";

// ── Types ───────────────────────────────────────────────────────────────────

interface LadderRow {
  levelLabel: string;
  lord: string;
  start?: string | null;
  end?: string | null;
}

interface TreeNode {
  level: number;
  lord: string;
  start: string;
  end: string;
  durationYears: number;
  subPeriods: TreeNode[];
}

interface DashaSystemPayload {
  system: string;
  applicable?: boolean;
  applicabilityNote?: string | null;
  currentLadder: LadderRow[];
  dashaTree: TreeNode[];
}

interface VimshottariSummary {
  maha: string | null;
  antara: string | null;
  mahaStart?: string | null;
  mahaEnd?: string | null;
  antaraStart?: string | null;
  antaraEnd?: string | null;
  balanceAtBirth?: { label: string };
  ladder?: LadderRow[];
}

// ── Constants ───────────────────────────────────────────────────────────────

const THEMES = {
  yogini: {
    label:  "Yogini",
    color:  "#5EE6D0",
    bg:     "rgba(94, 230, 208, 0.08)",
    border: "rgba(94, 230, 208, 0.30)",
    tagBg:  "rgba(94, 230, 208, 0.14)",
  },
  ashtottari: {
    label:  "Ashtottari",
    color:  "#fbbf24",
    bg:     "rgba(251, 191, 36, 0.08)",
    border: "rgba(251, 191, 36, 0.30)",
    tagBg:  "rgba(251, 191, 36, 0.14)",
  },
} as const;

type OtherKey = keyof typeof THEMES;

const VIMS_COLOR  = "#7c3aed";
const VIMS_BORDER = "rgba(124, 58, 237, 0.30)";
const VIMS_BG     = "rgba(124, 58, 237, 0.06)";

// ── Helpers ──────────────────────────────────────────────────────────────────

function fmtDuration(years: number): string {
  if (years >= 1) return `${years.toFixed(1)}y`;
  const m = years * 12;
  if (m >= 1) return `${m.toFixed(0)}m`;
  return `${Math.round(years * 365)}d`;
}

function yearFrom(iso: string) { return iso.slice(0, 4); }

// ── Toggle (Moon / Ascendant) ─────────────────────────────────────────────

function Toggle({ label, checked, color, onChange }: {
  label: string; checked: boolean; color: string; onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-1.5 cursor-pointer select-none">
      <input type="checkbox" className="sr-only" checked={checked}
        onChange={(e) => onChange(e.target.checked)} />
      <span className="relative inline-flex w-7 h-[14px] rounded-full transition-colors duration-200"
        style={{ backgroundColor: checked ? color : "var(--color-hairline)" }}>
        <span className="absolute top-[2px] w-[10px] h-[10px] rounded-full bg-white transition-transform duration-200"
          style={{ transform: checked ? "translateX(14px)" : "translateX(2px)" }} />
      </span>
      <span className="text-[10px] font-mono" style={{ color: checked ? color : "var(--color-text-muted)" }}>
        {label}
      </span>
    </label>
  );
}

// ── Mahadasha chip (same style as DashaDeepTree) ──────────────────────────

function MahaChip({ lord, start, durationYears, isCurrent, isExpanded, color, border, bg, onClick }: {
  lord: string; start: string; durationYears: number;
  isCurrent: boolean; isExpanded: boolean;
  color: string; border: string; bg: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="shrink-0 flex flex-col items-center gap-0.5 px-3 py-2 rounded-xl border transition-colors duration-200 focus-visible:outline-none"
      style={{
        backgroundColor: isCurrent ? bg : isExpanded ? `${bg}` : "transparent",
        borderColor:     isCurrent ? color : isExpanded ? border : "var(--color-hairline)",
        opacity: 1,
      }}
    >
      <span className="text-xs font-mono font-semibold" style={{ color: isCurrent ? color : "var(--color-text-main)" }}>
        {lord}
      </span>
      <span className="text-[10px] font-mono" style={{ color: isCurrent ? color : "var(--color-text-muted)" }}>
        {yearFrom(start)} · {fmtDuration(durationYears)}
      </span>
      {isCurrent && (
        <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-full leading-none"
          style={{ backgroundColor: `${color}22`, color }}>
          now
        </span>
      )}
      {isExpanded && <ChevronDown className="w-3 h-3 mt-0.5" style={{ color }} />}
    </button>
  );
}

// ── Antardasha row ────────────────────────────────────────────────────────

function AntarRow({ node, isCurrent, isOpen, color, border, bg, chart, moonOn, lagnaOn, mahaLord, onClick }: {
  node: TreeNode; isCurrent: boolean; isOpen: boolean;
  color: string; border: string; bg: string;
  chart?: ChartData; moonOn: boolean; lagnaOn: boolean;
  mahaLord: string;
  onClick: () => void;
}) {
  const canChart = !!(chart?.meta?.birth_datetime && node.start && node.end);

  return (
    <div className="mb-1">
      <button
        onClick={onClick}
        className="w-full text-left rounded-xl border px-3 py-2 transition-colors duration-200"
        style={{
          backgroundColor: isCurrent ? bg : isOpen ? `${bg}` : "transparent",
          borderColor:     isCurrent ? color : isOpen ? border : "rgba(255,255,255,0.08)",
        }}
      >
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-sm font-medium" style={{ color: isCurrent ? color : "var(--color-text-main)" }}>
              {node.lord}
            </span>
            {isCurrent && (
              <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-md leading-none"
                style={{ backgroundColor: `${color}22`, color }}>
                now
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-[10px] font-mono text-text-muted tabular-nums">
              {node.start.slice(0,10)} → {node.end.slice(0,10)}
            </span>
            <span className="text-[10px] font-mono text-text-muted">{fmtDuration(node.durationYears)}</span>
            {canChart && <ChevronDown className="w-3 h-3 text-text-muted" style={{ transform: isOpen ? "rotate(180deg)" : undefined }} />}
          </div>
        </div>
      </button>

      <AnimatePresence>
        {isOpen && canChart && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22 }}
            className="overflow-hidden"
          >
            <div className="ml-4 mt-1 mb-2 rounded-xl border p-3.5"
              style={{ borderColor: border, backgroundColor: bg }}>
              <DashaSeriesChart
                chart={chart!}
                mahaLord={mahaLord}
                antarLord={node.lord}
                startDate={node.start}
                endDate={node.end}
                dashaScore={0}
                moonOn={moonOn}
                lagnaOn={lagnaOn}
                title={`${mahaLord} / ${node.lord}`}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── OtherDashaTree (Yogini | Ashtottari) ─────────────────────────────────

function OtherDashaTree({ dashaKey, chart }: { dashaKey: OtherKey; chart?: ChartData }) {
  const t = THEMES[dashaKey];
  const endpoint = dashaKey === "yogini" ? "dasha-deep-yogini" : "dasha-deep-ashtottari";

  const [data, setData]       = useState<DashaSystemPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);
  const [moonOn, setMoonOn]   = useState(true);
  const [lagnaOn, setLagnaOn] = useState(false);
  const [expandedMaha, setExpandedMaha] = useState<number | null>(null);
  const [expandedAntar, setExpandedAntar] = useState<string | null>(null);

  function toggleMoon(v: boolean)  { if (!v && !lagnaOn) return; setMoonOn(v); }
  function toggleLagna(v: boolean) { if (!v && !moonOn)  return; setLagnaOn(v); }

  const birth = chart?.meta;

  const load = useCallback(async () => {
    if (!birth?.birth_datetime) return;
    setLoading(true); setError(null);
    try {
      const json = await postCvce<DashaSystemPayload>(endpoint, {
        birth_datetime: birth.birth_datetime,
        birth_lat: birth.birth_lat,
        birth_lon: birth.birth_lon,
        birth_tz:  birth.birth_tz,
      });
      setData(json);
      // Auto-expand the running Mahadasha
      if (json.currentLadder.length > 0) {
        const runningMaha = json.currentLadder[0]?.lord;
        const idx = json.dashaTree.findIndex((n) => n.lord === runningMaha);
        if (idx !== -1) setExpandedMaha(idx);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [birth?.birth_datetime, birth?.birth_lat, birth?.birth_lon, birth?.birth_tz, endpoint]);

  useEffect(() => { load(); }, [load]);

  const runningMaha  = data?.currentLadder?.[0]?.lord ?? null;
  const runningAntar = data?.currentLadder?.[1]?.lord ?? null;

  return (
    <div className="rounded-2xl border space-y-4 p-5"
      style={{ borderColor: t.border, backgroundColor: "var(--color-card)", boxShadow: `inset 0 0 0 1px ${t.border}` }}>

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="font-[family-name:var(--font-display)] text-base font-semibold tracking-tight"
          style={{ color: t.color }}>
          {t.label}
        </h3>
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-mono uppercase tracking-wider text-text-muted">View from</span>
          <Toggle label="Moon"      checked={moonOn}  color="#60a5fa" onChange={toggleMoon} />
          <Toggle label="Ascendant" checked={lagnaOn} color="#f59e0b" onChange={toggleLagna} />
        </div>
      </div>

      {/* Applicability note (Ashtottari only) */}
      {data?.applicabilityNote && (
        <div className="rounded-lg px-3 py-2 text-[11px] font-mono leading-relaxed"
          style={{ backgroundColor: `${t.color}15`, color: t.color }}>
          ⚠ {data.applicabilityNote}
        </div>
      )}

      {/* Loading / error */}
      {loading && (
        <div className="flex items-center gap-2 py-4 text-text-muted">
          <Loader className="w-4 h-4 animate-spin" />
          <span className="text-sm font-mono">Loading {t.label} dasha…</span>
        </div>
      )}
      {error && !data && (
        <div className="flex items-center gap-2 py-4" style={{ color: "var(--color-danger)" }}>
          <AlertCircle className="w-4 h-4" />
          <span className="text-sm font-mono">{error}</span>
        </div>
      )}

      {data && (
        <>
          {/* Running Now ladder */}
          {data.currentLadder.length > 0 && (
            <div className="rounded-xl border p-3.5 space-y-2"
              style={{ borderColor: t.border, backgroundColor: t.bg }}>
              <p className="text-[10px] font-mono uppercase tracking-wider" style={{ color: t.color }}>
                Running now
              </p>
              {data.currentLadder.map((row) => (
                <div key={row.levelLabel} className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
                  <span className="text-[10px] font-mono uppercase tracking-wide shrink-0 w-28"
                    style={{ color: t.color, opacity: 0.7 }}>
                    {row.levelLabel}
                  </span>
                  <span className="text-sm font-semibold" style={{ color: t.color }}>{row.lord}</span>
                  {row.start && row.end && (
                    <span className="text-[11px] font-mono tabular-nums text-text-muted">
                      {row.start.slice(0,10)} → {row.end.slice(0,10)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Mahadasha chip row */}
          {data.dashaTree.length > 0 && (
            <div className="overflow-x-auto -mx-1 px-1 pb-1">
              <div className="flex gap-2 min-w-min">
                {data.dashaTree.map((node, i) => (
                  <MahaChip
                    key={i}
                    lord={node.lord}
                    start={node.start}
                    durationYears={node.durationYears}
                    isCurrent={node.lord === runningMaha}
                    isExpanded={expandedMaha === i}
                    color={t.color}
                    border={t.border}
                    bg={t.bg}
                    onClick={() => {
                      setExpandedMaha((prev) => (prev === i ? null : i));
                      setExpandedAntar(null);
                    }}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Expanded Mahadasha → Antardasha list */}
          <AnimatePresence>
            {expandedMaha !== null && data.dashaTree[expandedMaha] && (
              <motion.div
                key={expandedMaha}
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.22 }}
                className="overflow-hidden space-y-1"
              >
                {data.dashaTree[expandedMaha].subPeriods.length > 0 ? (
                  data.dashaTree[expandedMaha].subPeriods.map((antar, j) => {
                    const key = `${expandedMaha}-${j}`;
                    const isCurrent = antar.lord === runningAntar &&
                                      data.dashaTree[expandedMaha].lord === runningMaha;
                    return (
                      <AntarRow
                        key={key}
                        node={antar}
                        isCurrent={isCurrent}
                        isOpen={expandedAntar === key}
                        color={t.color}
                        border={t.border}
                        bg={t.bg}
                        chart={chart}
                        moonOn={moonOn}
                        lagnaOn={lagnaOn}
                        mahaLord={data.dashaTree[expandedMaha].lord}
                        onClick={() => setExpandedAntar((prev) => (prev === key ? null : key))}
                      />
                    );
                  })
                ) : (
                  <p className="text-xs text-text-muted py-2 px-1">No sub-periods available.</p>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {expandedMaha === null && data.dashaTree.length > 0 && (
            <p className="text-center text-xs text-text-muted py-2">
              Tap a Mahadasha above to explore its sub-periods
            </p>
          )}
        </>
      )}
    </div>
  );
}

// ── Vimshottari summary card ─────────────────────────────────────────────

function VimshottariCard({ data }: { data: VimshottariSummary }) {
  return (
    <div className="rounded-2xl border p-5"
      style={{ borderColor: VIMS_BORDER, backgroundColor: "var(--color-card)", boxShadow: `inset 0 0 0 1px ${VIMS_BORDER}` }}>
      <h3 className="font-[family-name:var(--font-display)] text-base font-semibold tracking-tight mb-3"
        style={{ color: VIMS_COLOR }}>
        Vimshottari
      </h3>

      {data.ladder && data.ladder.length > 0 ? (
        <div className="rounded-xl border p-3.5 space-y-2"
          style={{ borderColor: VIMS_BORDER, backgroundColor: VIMS_BG }}>
          <p className="text-[10px] font-mono uppercase tracking-wider" style={{ color: VIMS_COLOR }}>
            Running now
          </p>
          {data.ladder.map((row) => (
            <div key={row.levelLabel} className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
              <span className="text-[10px] font-mono uppercase tracking-wide shrink-0 w-28"
                style={{ color: VIMS_COLOR, opacity: 0.7 }}>
                {row.levelLabel}
              </span>
              <span className="text-sm font-semibold" style={{ color: VIMS_COLOR }}>{row.lord}</span>
              {row.start && row.end && (
                <span className="text-[11px] font-mono tabular-nums text-text-muted">
                  {row.start.slice(0,10)} → {row.end.slice(0,10)}
                </span>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-1.5 text-sm text-text-muted font-mono">
          {data.maha && <p>Maha: <span style={{ color: VIMS_COLOR }}>{data.maha}</span></p>}
          {data.antara && <p>Antar: <span style={{ color: VIMS_COLOR }}>{data.antara}</span></p>}
        </div>
      )}

      {data.balanceAtBirth?.label && (
        <p className="text-[11px] font-mono text-text-muted mt-3">
          Birth balance: {data.balanceAtBirth.label}
        </p>
      )}
    </div>
  );
}

// ── Main component ──────────────────────────────────────────────────────────

export function AllDashasPanel({ chart }: { chart?: ChartData }) {
  const [vims, setVims]       = useState<VimshottariSummary | null>(null);
  const [loading, setLoading] = useState(false);

  const birth = chart?.meta;

  useEffect(() => {
    if (!birth?.birth_datetime) return;
    setLoading(true);
    let cancelled = false;
    postCvce<{ dashas?: { vimshottari?: VimshottariSummary } } & { vimshottari?: VimshottariSummary }>(
      "dashas",
      { birth_datetime: birth.birth_datetime, birth_lat: birth.birth_lat, birth_lon: birth.birth_lon, birth_tz: birth.birth_tz },
    )
      .then((json) => { if (!cancelled) setVims(json.dashas?.vimshottari ?? (json as { vimshottari?: VimshottariSummary }).vimshottari ?? null); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [birth?.birth_datetime, birth?.birth_lat, birth?.birth_lon, birth?.birth_tz]);

  if (!chart) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-16 text-text-muted">
        <Clock className="h-5 w-5" />
        <span className="text-sm font-mono">No chart data provided</span>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Vimshottari summary */}
      {loading ? (
        <div className="rounded-2xl border border-hairline p-5 animate-pulse h-24" />
      ) : vims ? (
        <VimshottariCard data={vims} />
      ) : null}

      {/* Yogini full tree */}
      <OtherDashaTree dashaKey="yogini" chart={chart} />

      {/* Ashtottari full tree */}
      <OtherDashaTree dashaKey="ashtottari" chart={chart} />
    </div>
  );
}
