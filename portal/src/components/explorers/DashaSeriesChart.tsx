"use client";

import { useState, useEffect } from "react";
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceLine,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Loader, ChevronDown, ChevronRight } from "lucide-react";
import type { ChartData, DashaSeriesData, DashaSeriesPoint, DashaSeriesEvent } from "@/lib/types";
import { postCvce } from "@/lib/cvce-client";

// ── Colour tokens ─────────────────────────────────────────────────────────────

const SHUBH   = "#10b981";
const ASHUBH  = "#ef4444";
const DASHA   = "#7c3aed";
const MOON_C  = "#60a5fa";
const LAGNA_C = "#f59e0b";

const PLANET_COLOR: Record<string, string> = {
  Sun:     "#f97316",
  Moon:    "#94a3b8",
  Mars:    "#ef4444",
  Mercury: "#22c55e",
  Jupiter: "#facc15",
  Venus:   "#ec4899",
  Saturn:  "#7c3aed",
  Rahu:    "#64748b",
  Ketu:    "#a78bfa",
};

// Moon excluded — it changes sign every 2.5 days, so monthly sampling produces
// meaningless noise; its reference perspective is already the "View from Moon" line.
const PLANETS = ["Sun", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"];

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtMonth(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", { month: "short", year: "2-digit" });
}

function fmtEvent(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

function fmtFull(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric", month: "short", year: "numeric",
  });
}

// ── Custom tooltip ────────────────────────────────────────────────────────────

function ScoreTooltip({ active, payload, moonOn, lagnaOn, activePlanets }: {
  active?: boolean;
  payload?: { payload: DashaSeriesPoint }[];
  moonOn: boolean;
  lagnaOn: boolean;
  activePlanets: Set<string>;
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  const isShubh = d.combined_score > 0;
  const activePlanetList = PLANETS.filter((p) => activePlanets.has(p));

  return (
    <div
      className="rounded-xl border px-3 py-2.5 text-[11px] font-mono space-y-1 shadow-lg"
      style={{
        backgroundColor: "#0f0f1a",
        borderColor: isShubh ? `${SHUBH}88` : `${ASHUBH}88`,
        minWidth: 230,
      }}
    >
      <p className="text-text-muted">{fmtFull(d.date)}</p>

      {moonOn && (
        <div className="flex items-center gap-2">
          <span className="px-1.5 py-0.5 rounded-md font-semibold text-[10px]"
            style={{ backgroundColor: `${MOON_C}20`, color: MOON_C }}>
            Moon {d.combined_score > 0 ? "+" : ""}{d.combined_score}
          </span>
          <span className="text-text-muted">transit {d.transit_score > 0 ? "+" : ""}{d.transit_score}</span>
        </div>
      )}

      {lagnaOn && (
        <div className="flex items-center gap-2">
          <span className="px-1.5 py-0.5 rounded-md font-semibold text-[10px]"
            style={{ backgroundColor: `${LAGNA_C}20`, color: LAGNA_C }}>
            Lagna {d.lagna_combined_score > 0 ? "+" : ""}{d.lagna_combined_score}
          </span>
          <span className="text-text-muted">transit {d.lagna_transit_score > 0 ? "+" : ""}{d.lagna_transit_score}</span>
        </div>
      )}

      {activePlanetList.length > 0 && (
        <div className="pt-0.5 border-t border-white/10 mt-1 space-y-0.5">
          {activePlanetList.map((p) => {
            const s = d.planet_scores?.[p] ?? 0;
            return (
              <div key={p} className="flex items-center justify-between gap-3">
                <span style={{ color: PLANET_COLOR[p] }}>{p}</span>
                <span style={{ color: s > 0 ? SHUBH : s < 0 ? ASHUBH : "var(--color-text-muted)" }}>
                  {s > 0 ? "+" : ""}{s}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {d.key_planet && !activePlanetList.length && (
        <p className="text-text-main">
          <span style={{ color: DASHA }}>{d.key_planet}:</span>{" "}
          {(d.key_note ?? "").slice(0, 70)}
        </p>
      )}
    </div>
  );
}

// ── Event markers — two-column layout with TODAY divider ─────────────────────

type EventItem =
  | { kind: "event"; e: DashaSeriesEvent; past: boolean }
  | { kind: "today" };

function EventList({ events }: { events: DashaSeriesEvent[] }) {
  const [open, setOpen] = useState(false);
  if (!events.length) return null;

  const todayISO = new Date().toISOString().slice(0, 10);

  const items: EventItem[] = [];
  let markerInserted = false;
  for (const e of events) {
    if (!markerInserted && e.date > todayISO) {
      items.push({ kind: "today" });
      markerInserted = true;
    }
    items.push({ kind: "event", e, past: e.date <= todayISO });
  }
  if (!markerInserted) items.push({ kind: "today" });

  const half = Math.ceil(items.length / 2);
  const col1 = items.slice(0, half);
  const col2 = items.slice(half);

  const Row = ({ item }: { item: EventItem }) => {
    if (item.kind === "today") {
      return (
        <div className="flex items-center gap-1.5 py-0.5 my-0.5">
          <div className="flex-1 h-px" style={{ backgroundColor: "#eab30855" }} />
          <span className="text-[9px] font-mono font-semibold" style={{ color: "#eab308" }}>TODAY</span>
          <div className="flex-1 h-px" style={{ backgroundColor: "#eab30855" }} />
        </div>
      );
    }
    const { e, past } = item;
    return (
      <div className="flex items-center gap-1.5 text-[10px]" style={{ opacity: past ? 0.45 : 1 }}>
        <span className="font-mono tabular-nums text-text-muted w-[76px] shrink-0">{fmtEvent(e.date)}</span>
        <span className="font-mono shrink-0 w-[54px]" style={{ color: PLANET_COLOR[e.planet] ?? "#94a3b8" }}>
          {e.planet}
        </span>
        <span className="text-text-muted truncate">
          {e.from_rashi} → {e.to_rashi}{e.house_from_moon ? ` h${e.house_from_moon}` : ""}
        </span>
      </div>
    );
  };

  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen((s) => !s)}
        className="flex items-center gap-1.5 text-[9px] font-mono uppercase tracking-widest text-text-muted hover:text-text-main transition-colors w-full text-left"
      >
        {open ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        Planetary Sign Changes ({events.length})
      </button>
      {open && (
        <div className="flex gap-0 mt-1.5">
          <div className="flex-1 space-y-0.5 pr-3">
            {col1.map((item, i) => <Row key={i} item={item} />)}
          </div>
          <div className="w-px bg-hairline shrink-0" />
          <div className="flex-1 space-y-0.5 pl-3">
            {col2.map((item, i) => <Row key={i} item={item} />)}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Planet toggle chips ───────────────────────────────────────────────────────

function PlanetToggles({
  activePlanets,
  onToggle,
}: {
  activePlanets: Set<string>;
  onToggle: (planet: string) => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen((s) => !s)}
        className="flex items-center gap-1.5 text-[9px] font-mono uppercase tracking-widest text-text-muted hover:text-text-main transition-colors w-full text-left"
      >
        {open ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        Individual planet contributions
        {activePlanets.size > 0 && (
          <span
            className="ml-1 px-1.5 py-0.5 rounded-full text-[8px] font-semibold"
            style={{ backgroundColor: `${DASHA}22`, color: DASHA }}
          >
            {activePlanets.size} on
          </span>
        )}
      </button>
      {open && (
        <p className="text-[9px] text-text-muted font-mono mt-1 mb-0.5">
          Each planet&apos;s own house score (one of 9 inputs to the total line above)
        </p>
      )}

      {open && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {PLANETS.map((p) => {
            const on = activePlanets.has(p);
            return (
              <button
                key={p}
                onClick={() => onToggle(p)}
                className="text-[10px] font-mono px-2 py-0.5 rounded-full border transition-colors duration-150"
                style={{
                  backgroundColor: on ? `${PLANET_COLOR[p]}18` : "transparent",
                  color: on ? PLANET_COLOR[p] : "var(--color-text-muted)",
                  borderColor: on ? `${PLANET_COLOR[p]}66` : "var(--color-hairline)",
                }}
              >
                {p}
              </button>
            );
          })}
          {activePlanets.size > 0 && (
            <button
              onClick={() => PLANETS.forEach((p) => activePlanets.has(p) && onToggle(p))}
              className="text-[9px] font-mono px-2 py-0.5 rounded-full border border-hairline text-text-muted hover:text-text-main transition-colors"
            >
              clear
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ── Stats bar ─────────────────────────────────────────────────────────────────

function StatsBar({ stats, dashaScore, moonOn, lagnaOn }: {
  stats: DashaSeriesData["stats"];
  dashaScore: number;
  moonOn: boolean;
  lagnaOn: boolean;
}) {
  const shubhPct = Math.round((stats.shubh_months / stats.total_months) * 100);

  return (
    <div className="mt-3 space-y-1.5">
      <div className="flex items-center gap-2 text-[10px] font-mono">
        <span style={{ color: SHUBH }}>{stats.shubh_months}m Shubh</span>
        <div className="flex-1 h-1.5 rounded-full bg-hairline overflow-hidden">
          <div className="h-full rounded-full" style={{ width: `${shubhPct}%`, backgroundColor: SHUBH }} />
        </div>
        <span style={{ color: ASHUBH }}>{stats.ashubh_months}m Ashubh</span>
      </div>

      {moonOn && (
        <div className="flex gap-4 text-[10px] font-mono text-text-muted">
          <span style={{ color: MOON_C }}>Moon</span>
          <span>Best: <span style={{ color: SHUBH }}>{stats.peak.score > 0 ? "+" : ""}{stats.peak.score}</span> ({fmtEvent(stats.peak.date)})</span>
          <span>Worst: <span style={{ color: ASHUBH }}>{stats.trough.score > 0 ? "+" : ""}{stats.trough.score}</span> ({fmtEvent(stats.trough.date)})</span>
        </div>
      )}

      {lagnaOn && stats.lagna_peak && (
        <div className="flex gap-4 text-[10px] font-mono text-text-muted">
          <span style={{ color: LAGNA_C }}>Lagna</span>
          <span>Best: <span style={{ color: SHUBH }}>{stats.lagna_peak.score > 0 ? "+" : ""}{stats.lagna_peak.score}</span> ({fmtEvent(stats.lagna_peak.date)})</span>
          <span>Worst: <span style={{ color: ASHUBH }}>{stats.lagna_trough.score > 0 ? "+" : ""}{stats.lagna_trough.score}</span> ({fmtEvent(stats.lagna_trough.date)})</span>
        </div>
      )}

      <div className="text-[10px] font-mono text-text-muted">
        Dasha base: <span style={{ color: DASHA }}>{dashaScore > 0 ? "+" : ""}{dashaScore}</span>
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
  title?: string;
  moonOn: boolean;
  lagnaOn: boolean;
}

export function DashaSeriesChart({
  chart,
  mahaLord,
  antarLord,
  startDate,
  endDate,
  dashaScore,
  title,
  moonOn,
  lagnaOn,
}: DashaSeriesChartProps) {
  const [data, setData] = useState<DashaSeriesData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activePlanets, setActivePlanets] = useState<Set<string>>(new Set());

  function togglePlanet(planet: string) {
    setActivePlanets((prev) => {
      const next = new Set(prev);
      if (next.has(planet)) next.delete(planet);
      else next.add(planet);
      return next;
    });
  }

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const durationDays =
      (new Date(endDate).getTime() - new Date(startDate).getTime()) / 86_400_000;
    const intervalDays = Math.max(3, Math.min(30, Math.round(durationDays / 8)));

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
      interval_days: intervalDays,
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
    return <p className="text-[11px] font-mono text-text-muted py-2">Transit series unavailable.</p>;
  }

  const { series, events, stats } = data;
  const bothOn = moonOn && lagnaOn;
  const activePlanetList = PLANETS.filter((p) => activePlanets.has(p));

  const eventLines = events.filter((e) =>
    ["Saturn", "Jupiter", "Rahu", "Ketu"].includes(e.planet),
  );

  // Gradient split at y=0 (used in single-line mode)
  const activeScores = moonOn
    ? series.map((s) => s.combined_score)
    : series.map((s) => s.lagna_combined_score);
  const maxScore = Math.max(...activeScores, 0);
  const minScore = Math.min(...activeScores, 0);
  const range = maxScore - minScore || 1;
  const zeroOffsetPct = Math.round((maxScore / range) * 100);

  const moonGradId  = `grad-moon-${mahaLord}-${antarLord}`;
  const lagnaGradId = `grad-lagna-${mahaLord}-${antarLord}`;

  return (
    <div className="space-y-0">
      <p className="text-[9px] font-mono uppercase tracking-widest text-text-muted mb-2">
        {title ?? `Auspiciousness — ${mahaLord} Maha / ${antarLord} Antar`}
      </p>

      {/* Legend when both reference lines are showing */}
      {bothOn && (
        <div className="flex gap-4 mb-1.5 text-[10px] font-mono">
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-5 h-0.5 rounded" style={{ backgroundColor: MOON_C }} />
            <span style={{ color: MOON_C }}>Moon (Chandra)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-5 h-0.5 rounded" style={{ backgroundColor: LAGNA_C }} />
            <span style={{ color: LAGNA_C }}>Ascendant (Lagna)</span>
          </span>
        </div>
      )}

      <ResponsiveContainer width="100%" height={180}>
        <ComposedChart data={series} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
          <defs>
            <linearGradient id={moonGradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"                  stopColor={SHUBH}  stopOpacity={0.45} />
              <stop offset={`${zeroOffsetPct}%`} stopColor={SHUBH}  stopOpacity={0.15} />
              <stop offset={`${zeroOffsetPct}%`} stopColor={ASHUBH} stopOpacity={0.15} />
              <stop offset="100%"                stopColor={ASHUBH} stopOpacity={0.45} />
            </linearGradient>
            <linearGradient id={lagnaGradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"                  stopColor={LAGNA_C} stopOpacity={0.40} />
              <stop offset={`${zeroOffsetPct}%`} stopColor={LAGNA_C} stopOpacity={0.12} />
              <stop offset={`${zeroOffsetPct}%`} stopColor={ASHUBH}  stopOpacity={0.12} />
              <stop offset="100%"                stopColor={ASHUBH}  stopOpacity={0.40} />
            </linearGradient>
          </defs>

          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
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

          <ReferenceLine y={0} stroke="rgba(255,255,255,0.30)" strokeWidth={1.5} strokeDasharray="4 3" />
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

          {eventLines.map((e, i) => (
            <ReferenceLine
              key={i}
              x={e.date}
              stroke={e.transit_score_at_event > 0 ? `${SHUBH}66` : `${ASHUBH}55`}
              strokeWidth={1}
              strokeDasharray="2 3"
            />
          ))}

          <Tooltip
            content={(props) => (
              <ScoreTooltip
                active={props.active}
                payload={props.payload as unknown as { payload: DashaSeriesPoint }[] | undefined}
                moonOn={moonOn}
                lagnaOn={lagnaOn}
                activePlanets={activePlanets}
              />
            )}
          />

          {/* Moon — Area when alone, Line when dual */}
          {moonOn && !bothOn && (
            <Area type="monotone" dataKey="combined_score" name="Moon"
              stroke={MOON_C} strokeWidth={1.5}
              fill={`url(#${moonGradId})`} dot={false}
              activeDot={{ r: 3, strokeWidth: 0, fill: MOON_C }} />
          )}
          {moonOn && bothOn && (
            <Line type="monotone" dataKey="combined_score" name="Moon"
              stroke={MOON_C} strokeWidth={1.5}
              dot={false} activeDot={{ r: 3, strokeWidth: 0, fill: MOON_C }} />
          )}

          {/* Lagna — Area when alone, Line when dual */}
          {lagnaOn && !bothOn && (
            <Area type="monotone" dataKey="lagna_combined_score" name="Lagna"
              stroke={LAGNA_C} strokeWidth={1.5}
              fill={`url(#${lagnaGradId})`} dot={false}
              activeDot={{ r: 3, strokeWidth: 0, fill: LAGNA_C }} />
          )}
          {lagnaOn && bothOn && (
            <Line type="monotone" dataKey="lagna_combined_score" name="Lagna"
              stroke={LAGNA_C} strokeWidth={1.5}
              dot={false} activeDot={{ r: 3, strokeWidth: 0, fill: LAGNA_C }} />
          )}

          {/* Individual planet lines */}
          {activePlanetList.map((planet) => (
            <Line
              key={`planet-${planet}`}
              type="monotone"
              dataKey={(d: unknown) => (d as DashaSeriesPoint).planet_scores?.[planet] ?? 0}
              name={planet}
              stroke={PLANET_COLOR[planet]}
              strokeWidth={2}
              strokeDasharray="6 2"
              dot={{ r: 2.5, fill: PLANET_COLOR[planet], strokeWidth: 0 }}
              activeDot={{ r: 4, strokeWidth: 0, fill: PLANET_COLOR[planet] }}
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>

      <StatsBar stats={stats} dashaScore={dashaScore} moonOn={moonOn} lagnaOn={lagnaOn} />
      <PlanetToggles activePlanets={activePlanets} onToggle={togglePlanet} />
      <EventList events={events} />
    </div>
  );
}
