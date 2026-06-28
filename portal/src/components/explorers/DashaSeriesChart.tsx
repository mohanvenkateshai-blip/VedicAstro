"use client";

import { useState, useEffect } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceLine,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Loader } from "lucide-react";
import type { ChartData, DashaSeriesData, DashaSeriesPoint, DashaSeriesEvent } from "@/lib/types";
import { postCvce } from "@/lib/cvce-client";

// ── Colour tokens ─────────────────────────────────────────────────────────────

const SHUBH  = "#10b981";
const ASHUBH = "#ef4444";
const DASHA  = "#7c3aed";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtMonth(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", { month: "short", year: "2-digit" });
}

function fmtFull(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric", month: "short", year: "numeric",
  });
}

// ── Custom tooltip ────────────────────────────────────────────────────────────

function ScoreTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: { payload: DashaSeriesPoint }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  const isShubh = d.combined_score > 0;

  return (
    <div
      className="rounded-xl border px-3 py-2.5 text-[11px] font-mono space-y-1 shadow-lg"
      style={{
        backgroundColor: "var(--color-surface)",
        borderColor: isShubh ? `${SHUBH}55` : `${ASHUBH}55`,
        minWidth: 220,
      }}
    >
      <p className="text-text-muted">{fmtFull(d.date)}</p>
      <div className="flex items-center gap-2">
        <span
          className="px-1.5 py-0.5 rounded-md font-semibold text-[10px]"
          style={{
            backgroundColor: isShubh ? `${SHUBH}20` : `${ASHUBH}20`,
            color: isShubh ? SHUBH : ASHUBH,
          }}
        >
          {isShubh ? "Shubh" : "Ashubh"} {d.combined_score > 0 ? "+" : ""}{d.combined_score}
        </span>
        <span className="text-text-muted">Transit {d.transit_score > 0 ? "+" : ""}{d.transit_score}</span>
      </div>
      {d.key_planet && (
        <p className="text-text-main">
          <span style={{ color: DASHA }}>{d.key_planet}:</span>{" "}
          {(d.key_note ?? "").slice(0, 70)}
        </p>
      )}
    </div>
  );
}

// ── Event markers (slow-planet sign changes) ──────────────────────────────────

function EventList({ events }: { events: DashaSeriesEvent[] }) {
  // Filter to slow planets only (Saturn, Jupiter, Rahu/Ketu) for the list
  const notable = events.filter((e) =>
    ["Saturn", "Jupiter", "Rahu", "Ketu"].includes(e.planet),
  );
  if (!notable.length) return null;

  return (
    <div className="mt-3 space-y-1.5">
      <p className="text-[9px] font-mono uppercase tracking-widest text-text-muted">
        Planetary Sign Changes
      </p>
      {notable.map((e, i) => {
        const isGood = e.transit_score_at_event > 0;
        return (
          <div key={i} className="flex items-start gap-2 text-[11px]">
            <span
              className="shrink-0 font-mono text-[10px] tabular-nums text-text-muted w-20"
            >
              {fmtMonth(e.date)}
            </span>
            <span
              className="font-mono shrink-0"
              style={{ color: isGood ? SHUBH : ASHUBH }}
            >
              {e.planet}
            </span>
            <span className="text-text-muted">
              {e.from_rashi} → {e.to_rashi}
              {e.house_from_moon ? ` (house ${e.house_from_moon})` : ""}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ── Stats bar ─────────────────────────────────────────────────────────────────

function StatsBar({ stats, dashaScore }: {
  stats: DashaSeriesData["stats"];
  dashaScore: number;
}) {
  const shubhPct = Math.round((stats.shubh_months / stats.total_months) * 100);

  return (
    <div className="mt-3 space-y-2">
      {/* Shubh/Ashubh bar */}
      <div className="flex items-center gap-2 text-[10px] font-mono">
        <span style={{ color: SHUBH }}>{stats.shubh_months}m Shubh</span>
        <div className="flex-1 h-1.5 rounded-full bg-hairline overflow-hidden">
          <div
            className="h-full rounded-full"
            style={{ width: `${shubhPct}%`, backgroundColor: SHUBH }}
          />
        </div>
        <span style={{ color: ASHUBH }}>{stats.ashubh_months}m Ashubh</span>
      </div>
      {/* Peak/trough */}
      <div className="flex gap-4 text-[10px] font-mono text-text-muted">
        <span>
          Best:{" "}
          <span style={{ color: SHUBH }}>
            {stats.peak.score > 0 ? "+" : ""}{stats.peak.score}
          </span>{" "}
          ({fmtMonth(stats.peak.date)})
        </span>
        <span>
          Worst:{" "}
          <span style={{ color: ASHUBH }}>
            {stats.trough.score > 0 ? "+" : ""}{stats.trough.score}
          </span>{" "}
          ({fmtMonth(stats.trough.date)})
        </span>
        <span>
          Dasha base:{" "}
          <span style={{ color: DASHA }}>
            {dashaScore > 0 ? "+" : ""}{dashaScore}
          </span>
        </span>
      </div>
    </div>
  );
}

// ── Main chart component ──────────────────────────────────────────────────────

export interface DashaSeriesChartProps {
  chart: ChartData;
  mahaLord: string;
  antarLord: string;
  startDate: string;
  endDate: string;
  dashaScore: number;
}

export function DashaSeriesChart({
  chart,
  mahaLord,
  antarLord,
  startDate,
  endDate,
  dashaScore,
}: DashaSeriesChartProps) {
  const [data, setData] = useState<DashaSeriesData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    postCvce<DashaSeriesData>("dasha-series", {
      birth_datetime: chart.meta?.birth_datetime,
      birth_lat: chart.meta?.birth_lat,
      birth_lon: chart.meta?.birth_lon,
      birth_tz: chart.meta?.birth_tz,
      maha_lord: mahaLord,
      antar_lord: antarLord,
      start_date: startDate,
      end_date: endDate,
      dasha_score: dashaScore,
      interval_days: 30,
    })
      .then((d) => { if (!cancelled) { setData(d); setLoading(false); } })
      .catch((e) => { if (!cancelled) { setError(e.message); setLoading(false); } });

    return () => { cancelled = true; };
  }, [chart, mahaLord, antarLord, startDate, endDate, dashaScore]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-4 text-[11px] font-mono text-text-muted">
        <Loader className="w-3 h-3 animate-spin" style={{ color: DASHA }} />
        computing transit series…
      </div>
    );
  }
  if (error || !data || !data.series.length) {
    return (
      <p className="text-[11px] font-mono text-text-muted py-2">
        Transit series unavailable.
      </p>
    );
  }

  const { series, events, stats } = data;

  // Build event map for reference lines (slow planets only, to avoid clutter)
  const eventLines = events.filter((e) =>
    ["Saturn", "Jupiter", "Rahu", "Ketu"].includes(e.planet),
  );

  // Compute where y=0 falls as a % from the top of the chart area.
  // This lets the gradient split green/red exactly at the zero line.
  const maxScore = Math.max(...series.map((s) => s.combined_score), 0);
  const minScore = Math.min(...series.map((s) => s.combined_score), 0);
  const range = maxScore - minScore || 1;
  const zeroOffsetPct = Math.round((maxScore / range) * 100);

  const gradientId = `grad-${mahaLord}-${antarLord}`;

  return (
    <div className="space-y-0">
      <p className="text-[9px] font-mono uppercase tracking-widest text-text-muted mb-2">
        Auspiciousness Over Time — {mahaLord} Maha / {antarLord} Antar
      </p>

      <ResponsiveContainer width="100%" height={180}>
        <AreaChart
          data={series}
          margin={{ top: 8, right: 8, bottom: 0, left: -20 }}
        >
          <defs>
            {/* Gradient that transitions from green→red exactly at y=0 */}
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"                stopColor={SHUBH}  stopOpacity={0.45} />
              <stop offset={`${zeroOffsetPct}%`} stopColor={SHUBH}  stopOpacity={0.15} />
              <stop offset={`${zeroOffsetPct}%`} stopColor={ASHUBH} stopOpacity={0.15} />
              <stop offset="100%"              stopColor={ASHUBH} stopOpacity={0.45} />
            </linearGradient>
          </defs>

          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(255,255,255,0.06)"
            vertical={false}
          />

          <XAxis
            dataKey="date"
            tickFormatter={fmtMonth}
            tick={{ fontSize: 9, fontFamily: "monospace", fill: "var(--color-text-muted)" }}
            tickLine={false}
            axisLine={false}
            interval={Math.floor(series.length / 6)}
          />

          <YAxis
            tick={{ fontSize: 9, fontFamily: "monospace", fill: "var(--color-text-muted)" }}
            tickLine={false}
            axisLine={false}
            width={36}
          />

          {/* Zero line — the key visual boundary */}
          <ReferenceLine
            y={0}
            stroke="rgba(255,255,255,0.30)"
            strokeWidth={1.5}
            strokeDasharray="4 3"
          />

          {/* Dasha baseline — constant, shows how much transit bends it */}
          <ReferenceLine
            y={dashaScore}
            stroke={`${DASHA}55`}
            strokeWidth={1}
            strokeDasharray="2 4"
            label={{
              value: `Dasha ${dashaScore > 0 ? "+" : ""}${dashaScore}`,
              position: "insideTopRight",
              fontSize: 8,
              fill: `${DASHA}99`,
              fontFamily: "monospace",
            }}
          />

          {/* Slow-planet sign change events — vertical inflection markers */}
          {eventLines.map((e, i) => (
            <ReferenceLine
              key={i}
              x={e.date}
              stroke={e.transit_score_at_event > 0 ? `${SHUBH}66` : `${ASHUBH}55`}
              strokeWidth={1}
              strokeDasharray="2 3"
            />
          ))}

          <Tooltip content={<ScoreTooltip />} />

          {/* Single line + gradient fill that splits green/red at zero */}
          <Area
            type="monotone"
            dataKey="combined_score"
            stroke={DASHA}
            strokeWidth={1.5}
            fill={`url(#${gradientId})`}
            dot={false}
            activeDot={{ r: 3, strokeWidth: 0, fill: DASHA }}
          />
        </AreaChart>
      </ResponsiveContainer>

      <StatsBar stats={stats} dashaScore={dashaScore} />
      <EventList events={events} />
    </div>
  );
}
