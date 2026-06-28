"use client";

import { useState, useEffect, useCallback } from "react";
import { Clock, Loader, AlertCircle, ChevronDown, ChevronUp } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import type { ChartData } from "@/lib/types";
import { postCvce } from "@/lib/cvce-client";
import { DashaSeriesChart } from "./DashaSeriesChart";

// ── Types ───────────────────────────────────────────────────────────────────

interface DashaItem {
  maha: string | null;
  antara: string | null;
  mahaStart?: string | null;
  mahaEnd?: string | null;
  antaraStart?: string | null;
  antaraEnd?: string | null;
  balanceAtBirth?: { label: string };
  applicable?: boolean;
  reason?: string;
}

interface YoginiPeriod {
  lord: string;
  startYear: number;
  durationYears: number;
}

interface DashaSystemsData {
  vimshottari?: DashaItem;
  yogini?: DashaItem & { upcoming?: YoginiPeriod[] };
  ashtottari?: DashaItem;
}

// ── Constants ───────────────────────────────────────────────────────────────

const THEMES = {
  vimshottari: {
    label: "Vimshottari",
    color: "#7c3aed",
    bg: "rgba(124, 58, 237, 0.08)",
    border: "rgba(124, 58, 237, 0.30)",
    tagBg: "rgba(124, 58, 237, 0.14)",
  },
  yogini: {
    label: "Yogini",
    color: "#5EE6D0",
    bg: "rgba(94, 230, 208, 0.08)",
    border: "rgba(94, 230, 208, 0.30)",
    tagBg: "rgba(94, 230, 208, 0.14)",
  },
  ashtottari: {
    label: "Ashtottari",
    color: "#fbbf24",
    bg: "rgba(251, 191, 36, 0.08)",
    border: "rgba(251, 191, 36, 0.30)",
    tagBg: "rgba(251, 191, 36, 0.14)",
  },
} as const;

type DashaKey = keyof typeof THEMES;
const KEYS: DashaKey[] = ["vimshottari", "yogini", "ashtottari"];

// ── Moon/Lagna toggle (same style as DashaDeepTree) ─────────────────────────

function Toggle({
  label, checked, color, onChange,
}: {
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

// ── Skeleton ─────────────────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="rounded-2xl border border-hairline bg-card p-5">
      <div className="h-5 w-24 rounded-md animate-pulse bg-hairline mb-4" />
      <div className="space-y-3">
        <div className="h-4 w-32 rounded-md animate-pulse bg-hairline" />
        <div className="h-4 w-20 rounded-md animate-pulse bg-hairline" />
      </div>
    </div>
  );
}

// ── DashaCard ────────────────────────────────────────────────────────────────

function DashaCard({
  dashaKey, data, chart, moonOn, lagnaOn,
}: {
  dashaKey: DashaKey;
  data: DashaItem & { upcoming?: YoginiPeriod[] };
  chart?: ChartData;
  moonOn: boolean;
  lagnaOn: boolean;
}) {
  const t = THEMES[dashaKey];
  const [chartOpen, setChartOpen] = useState(false);

  const hasChart = Boolean(
    data.maha && data.antara &&
    (data.antaraStart || data.mahaStart) &&
    (data.antaraEnd || data.mahaEnd) &&
    chart,
  );

  const startDate = data.antaraStart || data.mahaStart || "";
  const endDate   = data.antaraEnd   || data.mahaEnd   || "";

  return (
    <motion.div
      className="rounded-2xl border flex flex-col"
      style={{ backgroundColor: "var(--color-card)", borderColor: t.border, boxShadow: `inset 0 0 0 1px ${t.border}` }}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
    >
      {/* Card body */}
      <div className="p-5 flex-1">
        <h3 className="font-[family-name:var(--font-display)] text-base font-semibold tracking-tight mb-4"
          style={{ color: t.color }}>
          {t.label}
        </h3>

        {data.maha ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2.5">
              <span className="text-[11px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-md"
                style={{ backgroundColor: t.tagBg, color: t.color }}>
                Maha
              </span>
              <span className="text-sm font-semibold" style={{ color: "var(--color-text-main)" }}>
                {data.maha}
              </span>
            </div>

            {data.antara && (
              <div className="flex items-center gap-2.5">
                <span className="text-[11px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-md"
                  style={{ backgroundColor: t.tagBg, color: t.color }}>
                  Antar
                </span>
                <span className="text-sm font-medium" style={{ color: "var(--color-text-main)" }}>
                  {data.antara}
                </span>
              </div>
            )}

            {dashaKey === "vimshottari" && data.balanceAtBirth?.label && (
              <p className="text-[11px] font-mono text-text-muted pt-1">
                Birth balance: {data.balanceAtBirth.label}
              </p>
            )}

            {data.mahaStart && data.mahaEnd && (
              <p className="text-[11px] font-mono text-text-muted">
                Maha {data.mahaStart.slice(0, 10)} → {data.mahaEnd.slice(0, 10)}
              </p>
            )}

            {data.antaraStart && data.antaraEnd && (
              <p className="text-[11px] font-mono text-text-muted">
                Antar {data.antaraStart.slice(0, 10)} → {data.antaraEnd.slice(0, 10)}
              </p>
            )}

            {data.upcoming && data.upcoming.length > 0 && (
              <div className="mt-4 pt-4" style={{ borderTop: "1px solid var(--color-hairline)" }}>
                <p className="text-[11px] font-mono uppercase tracking-wider mb-2.5"
                  style={{ color: "var(--color-text-muted)" }}>
                  Upcoming
                </p>
                <table className="w-full text-xs">
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--color-hairline)" }}>
                      <th className="pb-1.5 font-mono font-normal text-left" style={{ color: "var(--color-text-muted)" }}>Lord</th>
                      <th className="pb-1.5 font-mono font-normal text-left" style={{ color: "var(--color-text-muted)" }}>Start</th>
                      <th className="pb-1.5 font-mono font-normal text-right" style={{ color: "var(--color-text-muted)" }}>Dur</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.upcoming.map((p, i) => (
                      <tr key={i} style={{ borderBottom: "1px solid var(--color-hairline)" }}>
                        <td className="py-1.5 font-mono font-medium" style={{ color: t.color }}>{p.lord}</td>
                        <td className="py-1.5 font-mono tabular-nums" style={{ color: "var(--color-text-main)" }}>{p.startYear}</td>
                        <td className="py-1.5 font-mono tabular-nums text-right" style={{ color: "var(--color-text-muted)" }}>{p.durationYears}y</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ) : data.applicable === false ? (
          <div className="flex-1 flex flex-col gap-2">
            <p className="text-xs leading-relaxed" style={{ color: "var(--color-text-muted)" }}>
              Not applicable for this chart
            </p>
            {data.reason && (
              <p className="text-[10px] leading-relaxed" style={{ color: "var(--color-text-muted)" }}>
                {data.reason}
              </p>
            )}
          </div>
        ) : (
          <p className="text-xs text-center py-4" style={{ color: "var(--color-text-muted)" }}>
            Not available for this chart
          </p>
        )}
      </div>

      {/* Transit chart toggle */}
      {hasChart && (
        <>
          <button
            onClick={() => setChartOpen((o) => !o)}
            className="flex items-center justify-between w-full px-5 py-2.5 text-[11px] font-mono transition-colors"
            style={{
              borderTop: `1px solid ${t.border}`,
              color: chartOpen ? t.color : "var(--color-text-muted)",
              backgroundColor: chartOpen ? `${t.bg}` : "transparent",
            }}
          >
            <span>{chartOpen ? "Hide transit chart" : "View transit chart"}</span>
            {chartOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>

          <AnimatePresence>
            {chartOpen && chart && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.25 }}
                className="overflow-hidden"
              >
                <div className="p-4 pt-2">
                  <DashaSeriesChart
                    chart={chart}
                    mahaLord={data.maha!}
                    antarLord={data.antara!}
                    startDate={startDate}
                    endDate={endDate}
                    dashaScore={0}
                    moonOn={moonOn}
                    lagnaOn={lagnaOn}
                    title={`${t.label} — ${data.maha} / ${data.antara}`}
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </>
      )}
    </motion.div>
  );
}

// ── Main component ──────────────────────────────────────────────────────────

export function AllDashasPanel({ chart }: { chart?: ChartData }) {
  const [data, setData] = useState<DashaSystemsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [moonOn, setMoonOn] = useState(true);
  const [lagnaOn, setLagnaOn] = useState(false);

  function toggleMoon(v: boolean)  { if (!v && !lagnaOn) return; setMoonOn(v); }
  function toggleLagna(v: boolean) { if (!v && !moonOn)  return; setLagnaOn(v); }

  const fetchDashas = useCallback(async () => {
    if (!chart?.meta?.birth_datetime) return;
    setLoading(true);
    setError(null);
    try {
      const json = await postCvce<{ dashas?: DashaSystemsData } & DashaSystemsData>(
        "dashas",
        {
          birth_datetime: chart.meta.birth_datetime,
          birth_lat: chart.meta.birth_lat,
          birth_lon: chart.meta.birth_lon,
          birth_tz: chart.meta.birth_tz,
        },
      );
      setData(json.dashas ?? json);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dasha data");
    } finally {
      setLoading(false);
    }
  }, [chart]);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!chart?.meta?.birth_datetime) return;
      setLoading(true); setError(null); setData(null);
      try {
        const json = await postCvce<{ dashas?: DashaSystemsData } & DashaSystemsData>(
          "dashas",
          {
            birth_datetime: chart.meta.birth_datetime,
            birth_lat: chart.meta.birth_lat,
            birth_lon: chart.meta.birth_lon,
            birth_tz: chart.meta.birth_tz,
          },
        );
        if (!cancelled) setData(json.dashas ?? json);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load dasha data");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    run();
    return () => { cancelled = true; };
  }, [chart?.meta?.birth_datetime, chart?.meta?.birth_lat, chart?.meta?.birth_lon, chart?.meta?.birth_tz]);

  if (!chart) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-16 text-text-muted">
        <Clock className="h-5 w-5" />
        <span className="text-sm font-mono">No chart data provided</span>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SkeletonCard /><SkeletonCard /><SkeletonCard />
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16 text-text-muted">
        <div className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5" style={{ color: "var(--color-danger)" }} />
          <span className="text-sm font-mono">Could not load dasha data</span>
        </div>
        <span className="text-xs font-mono px-3 py-1 rounded-md"
          style={{ backgroundColor: "rgba(185, 28, 28, 0.08)", color: "var(--color-danger)" }}>
          {error}
        </span>
        <button onClick={fetchDashas}
          className="mt-2 text-xs font-mono px-4 py-1.5 rounded-lg border transition-colors hover:bg-card"
          style={{ borderColor: "var(--color-hairline)", color: "var(--color-text-main)" }}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Moon / Lagna toggles — shared across all 3 systems */}
      <div className="flex items-center gap-4 px-1">
        <span className="text-[10px] font-mono uppercase tracking-wider text-text-muted">View from</span>
        <Toggle label="Moon"      checked={moonOn}  color="#60a5fa" onChange={toggleMoon} />
        <Toggle label="Ascendant" checked={lagnaOn} color="#f59e0b" onChange={toggleLagna} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {KEYS.map((key) => (
          <DashaCard
            key={key}
            dashaKey={key}
            data={data?.[key] ?? { maha: null, antara: null }}
            chart={chart}
            moonOn={moonOn}
            lagnaOn={lagnaOn}
          />
        ))}
      </div>
    </div>
  );
}
