"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Clock, Loader, AlertCircle, ChevronDown, Zap } from "lucide-react";
import type { DashaPrediction, FructificationResult, FructificationWindow } from "@/lib/types";
import { motion, AnimatePresence } from "motion/react";
import type { ChartData } from "@/lib/types";
import { postCvce } from "@/lib/cvce-client";
import { DashaSeriesChart, ViewFromToggle } from "./DashaSeriesChart";

// ── Types ───────────────────────────────────────────────────────────────────

interface LadderRow {
  levelLabel: string;
  lord: string;
  yoginiName?: string;
  start?: string | null;
  end?: string | null;
}

interface TreeNode {
  level: number;
  lord: string;
  yoginiName?: string;   // Yogini deity name (Mangala, Pingala, etc.)
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

function MahaChip({ lord, yoginiName, start, durationYears, isCurrent, isExpanded, color, border, bg, onClick }: {
  lord: string; yoginiName?: string; start: string; durationYears: number;
  isCurrent: boolean; isExpanded: boolean;
  color: string; border: string; bg: string;
  onClick: () => void;
}) {
  const primary   = yoginiName ?? lord;
  const secondary = yoginiName ? `(${lord})` : null;

  return (
    <button
      onClick={onClick}
      className="shrink-0 flex flex-col items-center gap-0.5 px-3 py-2 rounded-xl border transition-colors duration-200 focus-visible:outline-none"
      style={{
        backgroundColor: isCurrent ? bg : isExpanded ? `${bg}` : "transparent",
        borderColor:     isCurrent ? color : isExpanded ? border : "var(--color-hairline)",
      }}
    >
      <span className="text-xs font-mono font-semibold" style={{ color: isCurrent ? color : "var(--color-text-main)" }}>
        {primary}
      </span>
      {secondary && (
        <span className="text-[9px] font-mono" style={{ color: isCurrent ? color : "var(--color-text-muted)", opacity: 0.7 }}>
          {secondary}
        </span>
      )}
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

// ── Fructification Panel ───────────────────────────────────────────────────

const STRENGTH_STYLE: Record<string, { color: string; label: string }> = {
  exceptional: { color: "#fbbf24", label: "Exceptional" },
  strong:      { color: "#34d399", label: "Strong" },
  moderate:    { color: "#60a5fa", label: "Moderate" },
  limited:     { color: "#94a3b8", label: "Limited" },
};

function FructificationPanel({ result, color }: { result: FructificationResult; color: string }) {
  if (result.total_windows === 0) {
    return (
      <div className="rounded-lg border px-3 py-2.5 space-y-1"
        style={{ borderColor: "rgba(255,255,255,0.08)", backgroundColor: "rgba(255,255,255,0.02)" }}>
        <p className="text-[10px] font-mono uppercase tracking-wider flex items-center gap-1.5" style={{ color }}>
          <Zap className="w-3 h-3" /> Fructification Windows
        </p>
        <p className="text-[11px] text-text-muted leading-relaxed">
          No overlapping Saturn+Jupiter benefic transit found within this antardasha window.
          The dasha promise may still operate through other mechanisms (benefic MD lord transit,
          natal promise activation) — the classical double-transit signature is absent here.
        </p>
        <p className="text-[10px] text-text-muted font-mono opacity-60 mt-1">
          {result.source.split("|")[0].trim()}
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border px-3 py-2.5 space-y-2.5"
      style={{ borderColor: `${color}22`, backgroundColor: `${color}06` }}>
      <div className="flex items-center justify-between flex-wrap gap-1">
        <p className="text-[10px] font-mono uppercase tracking-wider flex items-center gap-1.5" style={{ color }}>
          <Zap className="w-3 h-3" />
          Fructification Windows — {result.total_windows} found
        </p>
        <div className="flex flex-wrap gap-1.5">
          {result.reference_points.map((rp) => (
            <span key={rp.label} className="text-[9px] font-mono px-1.5 py-0.5 rounded-full"
              style={{ backgroundColor: `${color}18`, color }}>
              {rp.label}: {rp.sign}
            </span>
          ))}
        </div>
      </div>

      {result.progressed_lagna && (
        <p className="text-[10px] font-mono text-text-muted leading-relaxed">
          Progressed Lagna (cycle {result.progressed_lagna.cycle}): {result.progressed_lagna.progressed_lagna}
          {" · "}{result.progressed_lagna.contributing_nak_name} nakshatra
          {" · "}<span style={{ color }}>Star Lord: {result.progressed_lagna.star_lord}</span>
        </p>
      )}

      <div className="space-y-2">
        {result.windows.map((w, i) => (
          <FructificationWindowCard key={i} window={w} color={color} />
        ))}
      </div>

      <p className="text-[9px] text-text-muted font-mono opacity-50">
        {result.source.split("|")[0].trim()}
      </p>
    </div>
  );
}

function FructificationWindowCard({ window: w, color }: { window: FructificationWindow; color: string }) {
  const style = STRENGTH_STYLE[w.strength] ?? STRENGTH_STYLE.moderate;
  return (
    <div className="rounded-lg border px-3 py-2 space-y-1.5"
      style={{ borderColor: `${style.color}30`, backgroundColor: `${style.color}08` }}>
      <div className="flex items-center justify-between flex-wrap gap-1">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono font-semibold tabular-nums" style={{ color: style.color }}>
            {w.start.slice(0, 7)} → {w.end.slice(0, 7)}
          </span>
          <span className="text-[9px] px-1.5 py-0.5 rounded-full font-mono"
            style={{ backgroundColor: `${style.color}22`, color: style.color }}>
            {style.label}
          </span>
          <span className="text-[9px] font-mono text-text-muted">
            {w.duration_months}m
          </span>
        </div>
        {w.sav_bindus !== null && (
          <span className="text-[9px] font-mono" style={{ color: style.color }}>
            SAV {w.sav_bindus} bindus
          </span>
        )}
      </div>

      <div className="flex flex-wrap gap-x-3 gap-y-0.5">
        <span className="text-[10px] font-mono text-text-muted">
          ♄ {w.saturn.sign} · {w.saturn.house}th house
        </span>
        <span className="text-[10px] font-mono text-text-muted">
          ♃ {w.jupiter.sign} · {w.jupiter.house}th house
        </span>
        <span className="text-[9px] font-mono text-text-muted opacity-70">
          from {w.ref_label}
        </span>
      </div>

      <p className="text-[10px] text-text-muted leading-relaxed">
        {w.narrative}
      </p>

      {w.domains.length > 0 && (
        <div className="flex flex-wrap gap-1 pt-0.5">
          {w.domains.map((d) => (
            <span key={d} className="text-[9px] font-mono px-1.5 py-0.5 rounded-full capitalize"
              style={{ backgroundColor: `${color}14`, color }}>
              {d}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Antardasha row ────────────────────────────────────────────────────────

const DOMAIN_LABELS: { key: keyof DashaPrediction; label: string; warn: boolean }[] = [
  { key: "career",  label: "Career",  warn: false },
  { key: "wealth",  label: "Wealth",  warn: false },
  { key: "health",  label: "Health",  warn: false },
  { key: "family",  label: "Family",  warn: false },
  { key: "caution", label: "Caution", warn: true  },
];

function AntarRow({
  node, isCurrent, isOpen, color, border, bg, chart, moonOn, lagnaOn,
  onToggleMoon, onToggleLagna, mahaLord, mahaNode, prediction, system, onClick,
}: {
  node: TreeNode; isCurrent: boolean; isOpen: boolean;
  color: string; border: string; bg: string;
  chart?: ChartData; moonOn: boolean; lagnaOn: boolean;
  onToggleMoon: (v: boolean) => void; onToggleLagna: (v: boolean) => void;
  mahaLord: string;
  mahaNode: TreeNode;
  prediction?: DashaPrediction | null;
  system: string;
  onClick: () => void;
}) {
  const canChart = !!(chart?.meta?.birth_datetime && node.start && node.end);
  const displayName = node.yoginiName ? `${node.yoginiName} (${node.lord})` : node.lord;
  const domains = prediction
    ? DOMAIN_LABELS.filter((d) => (prediction[d.key] as string[]).length > 0)
    : [];

  // Fructification — lazy fetch when expanded
  const [fructResult, setFructResult] = useState<FructificationResult | null>(null);
  const [fructLoading, setFructLoading] = useState(false);
  const fetchedRef = useRef(false);

  useEffect(() => {
    if (!isOpen || fetchedRef.current || !chart?.meta?.birth_datetime) return;
    fetchedRef.current = true;
    setFructLoading(true);

    const birth = chart.meta;
    postCvce<FructificationResult>("fructification", {
      birth_datetime: birth.birth_datetime,
      birth_lat: birth.birth_lat,
      birth_lon: birth.birth_lon,
      birth_tz: birth.birth_tz,
      system,
      maha_lord: mahaNode.yoginiName ?? mahaNode.lord,
      antar_lord: node.yoginiName ?? node.lord,
      maha_start: mahaNode.start,
      maha_end: mahaNode.end,
      antar_start: node.start,
      antar_end: node.end,
    }).then(setFructResult).catch(() => {}).finally(() => setFructLoading(false));
  }, [isOpen, chart?.meta?.birth_datetime, system, mahaNode, node]);

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
              {displayName}
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
            <ChevronDown className="w-3 h-3 text-text-muted" style={{ transform: isOpen ? "rotate(180deg)" : undefined }} />
          </div>
        </div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22 }}
            className="overflow-hidden"
          >
            <div className="ml-4 mt-1 mb-2 rounded-xl border p-3.5 space-y-4"
              style={{ borderColor: border, backgroundColor: bg }}>

              {/* Life-domain predictions */}
              {domains.length > 0 && (
                <div className="space-y-2">
                  {domains.map(({ key, label, warn }) => (
                    <div key={key}>
                      <p className="text-[10px] font-mono uppercase tracking-wider mb-1"
                        style={{ color: warn ? "#f87171" : color, opacity: 0.8 }}>
                        {label}
                      </p>
                      <ul className="space-y-0.5">
                        {(prediction![key] as string[]).map((item, i) => (
                          <li key={i} className="text-[11px] leading-snug flex gap-1.5"
                            style={{ color: warn ? "#fca5a5" : "var(--color-text-main)" }}>
                            <span style={{ color, opacity: 0.6 }}>·</span>
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              )}

              {/* Fructification windows */}
              {fructLoading && (
                <div className="flex items-center gap-2 text-text-muted">
                  <Loader className="w-3 h-3 animate-spin" />
                  <span className="text-[10px] font-mono">Computing fructification windows…</span>
                </div>
              )}
              {fructResult && (
                <FructificationPanel result={fructResult} color={color} />
              )}

              {/* Transit chart */}
              {canChart && (
                <DashaSeriesChart
                  chart={chart!}
                  mahaLord={mahaLord}
                  antarLord={node.lord}
                  startDate={node.start}
                  endDate={node.end}
                  dashaScore={0}
                  moonOn={moonOn}
                  lagnaOn={lagnaOn}
                  title={`${mahaLord} / ${node.yoginiName ?? node.lord}`}
                  titleControls={<ViewFromToggle moonOn={moonOn} lagnaOn={lagnaOn} onToggleMoon={onToggleMoon} onToggleLagna={onToggleLagna} />}
                />
              )}
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
  const [predictions, setPredictions] = useState<Record<string, DashaPrediction>>({});

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
        const runningStart = json.currentLadder[0]?.start;
        const idx = json.dashaTree.findIndex((n) => n.lord === runningMaha && n.start === runningStart);
        if (idx !== -1) setExpandedMaha(idx);
      }

      // Fetch predictions for Yogini (same engine as Vimshottari, keyed by planet lords)
      if (dashaKey === "yogini") {
        postCvce<{ predictions: Record<string, DashaPrediction> }>("dasha-predict-yogini", {
          birth_datetime: birth!.birth_datetime,
          birth_lat: birth!.birth_lat,
          birth_lon: birth!.birth_lon,
          birth_tz:  birth!.birth_tz,
        }).then((r) => setPredictions(r.predictions ?? {})).catch(() => {});
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [birth?.birth_datetime, birth?.birth_lat, birth?.birth_lon, birth?.birth_tz, endpoint, dashaKey]);

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
      </div>

      {/* Not applicable — full stop, no tree */}
      {data && data.applicable === false && (
        <div className="rounded-xl border p-4 space-y-3"
          style={{ borderColor: "rgba(239,68,68,0.3)", backgroundColor: "rgba(239,68,68,0.06)" }}>
          <p className="text-[11px] font-mono font-semibold tracking-wide" style={{ color: "#f87171" }}>
            Not Applicable for this chart — BPHS (Parasara)
          </p>
          <div className="space-y-2">
            <p className="text-[11px] font-mono text-text-muted leading-relaxed">
              Ashtottari Dasha is a conditional system. BPHS requires{" "}
              <span className="text-text-main">both</span> conditions at birth:
            </p>
            <ul className="space-y-1.5 pl-3">
              <li className="text-[11px] leading-snug text-text-muted flex gap-2">
                <span style={{ color: "#f87171" }}>1.</span>
                <span>Rahu must be in a Kendra (1st, 4th, 7th, 10th) or Trikona (5th, 9th) from the Lagna Lord — but <em>not</em> in the Lagna itself</span>
              </li>
              <li className="text-[11px] leading-snug text-text-muted flex gap-2">
                <span style={{ color: "#f87171" }}>2.</span>
                <span>Daytime birth during Krishna Paksha (waning Moon), <em>or</em> nighttime birth during Shukla Paksha (waxing Moon)</span>
              </li>
            </ul>
            {data.applicabilityNote && (
              <p className="text-[11px] font-mono leading-relaxed mt-1 pt-2 border-t"
                style={{ color: "#f87171", borderColor: "rgba(239,68,68,0.2)" }}>
                This chart: {data.applicabilityNote.replace("Ashtottari Dasha does not apply to this chart per BPHS (Parasara). Both conditions must be satisfied: (1) Rahu in kendra/trikona from Lagna Lord, not in Lagna; and (2) daytime birth during Krishna Paksha or nighttime birth during Shukla Paksha. Failed: ", "")}
              </p>
            )}
            <p className="text-[10px] text-text-muted font-mono pt-1">
              Note: Applicability is determined once from the birth chart and holds for the native&apos;s entire life — it is not period-specific.
            </p>
          </div>
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

      {data && (data.applicable !== false) && (
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
                  <span className="text-sm font-semibold" style={{ color: t.color }}>
                    {row.yoginiName ? `${row.yoginiName} (${row.lord})` : row.lord}
                  </span>
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
                    yoginiName={node.yoginiName}
                    start={node.start}
                    durationYears={node.durationYears}
                    isCurrent={node.lord === runningMaha && node.start === data.currentLadder[0]?.start}
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

          {/* Expanded Mahadasha → full-span spectrum chart + Antardasha list */}
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
                {/* Mahadasha overview spectrum — full time window */}
                {chart?.meta?.birth_datetime && (
                  <div className="rounded-xl border p-3.5 mb-3"
                    style={{ borderColor: t.border, backgroundColor: t.bg }}>
                    <DashaSeriesChart
                      chart={chart}
                      mahaLord={data.dashaTree[expandedMaha].lord}
                      antarLord={data.dashaTree[expandedMaha].lord}
                      startDate={data.dashaTree[expandedMaha].start}
                      endDate={data.dashaTree[expandedMaha].end}
                      dashaScore={0}
                      moonOn={moonOn}
                      lagnaOn={lagnaOn}
                      title={`${data.dashaTree[expandedMaha].yoginiName ?? data.dashaTree[expandedMaha].lord} Mahadasha — Full Span Overview`}
                      titleControls={<ViewFromToggle moonOn={moonOn} lagnaOn={lagnaOn} onToggleMoon={toggleMoon} onToggleLagna={toggleLagna} />}
                    />
                  </div>
                )}

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
                        onToggleMoon={toggleMoon}
                        onToggleLagna={toggleLagna}
                        mahaLord={data.dashaTree[expandedMaha].lord}
                        mahaNode={data.dashaTree[expandedMaha]}
                        system={dashaKey}
                        prediction={(() => {
                          const maha = data.dashaTree[expandedMaha];
                          const mahaKey = maha.yoginiName ?? maha.lord;
                          const antarKey = antar.yoginiName ?? antar.lord;
                          return predictions[`${mahaKey}/${antarKey}`] ?? null;
                        })()}
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
