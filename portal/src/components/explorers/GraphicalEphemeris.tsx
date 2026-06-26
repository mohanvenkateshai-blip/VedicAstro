"use client";

import { useState, useEffect, useRef } from "react";
import { Loader } from "lucide-react";
import type { ChartData } from "@/lib/types";

const PLANET_COLORS: Record<string, string> = {
  Sun: "#f59e0b",
  Moon: "#c0c0c0",
  Mars: "#ef4444",
  Mercury: "#22c55e",
  Jupiter: "#c5a46e",
  Venus: "#ec4899",
  Saturn: "#6b7280",
  Rahu: "#8b5cf6",
  Ketu: "#14b8a6",
};

const PLANET_ORDER = [
  "Sun",
  "Moon",
  "Mars",
  "Mercury",
  "Jupiter",
  "Venus",
  "Saturn",
  "Rahu",
  "Ketu",
] as const;

const RASHI_SHORT = [
  "Ar",
  "Ta",
  "Ge",
  "Ca",
  "Le",
  "Vi",
  "Li",
  "Sc",
  "Sg",
  "Cp",
  "Aq",
  "Pi",
] as const;

const RASHI_NAMES = [
  "Aries",
  "Taurus",
  "Gemini",
  "Cancer",
  "Leo",
  "Virgo",
  "Libra",
  "Scorpio",
  "Sagittarius",
  "Capricorn",
  "Aquarius",
  "Pisces",
] as const;

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
] as const;

// ── Types ───────────────────────────────────────────────────────────────────

interface MonthlyPosition {
  date: string;
  [planet: string]: number | string;
}

interface TooltipData {
  planet: string;
  date: string;
  rashi: string;
  degree: string;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function longitudeToRashi(longitude: number) {
  const idx = Math.floor(longitude / 30) % 12;
  return { idx, name: RASHI_NAMES[idx], short: RASHI_SHORT[idx] };
}

function formatDegree(longitude: number): string {
  const deg = Math.floor(longitude % 30);
  const min = Math.floor(((longitude % 30) - deg) * 60);
  return `${deg}°${String(min).padStart(2, "0")}'`;
}

function rashiForY(yNorm: number) {
  const idx = Math.min(11, Math.max(0, Math.floor(yNorm * 12)));
  return 11 - idx;
}

// ── Constants for SVG geometry ──────────────────────────────────────────────

const VB_W = 900;
const VB_H = 560;
const MARGIN = { top: 44, right: 24, bottom: 34, left: 44 };
const PLOT_W = VB_W - MARGIN.left - MARGIN.right;
const PLOT_H = VB_H - MARGIN.top - MARGIN.bottom;

// ── Main Component ──────────────────────────────────────────────────────────

export function GraphicalEphemeris({ chart }: { chart: ChartData | undefined }) {
  const [positions, setPositions] = useState<MonthlyPosition[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!chart?.meta?.birth_datetime) return;
    let cancelled = false;

    async function fetchPositions() {
      if (!chart?.meta?.birth_datetime) return;

      const year = new Date().getFullYear();
      setLoading(true);
      setError(null);

      try {
        const res = await fetch(
          `/positions?birth_datetime=${encodeURIComponent(chart.meta?.birth_datetime!)}&birth_lat=${chart.meta?.birth_lat}&birth_lon=${chart.meta?.birth_lon}&birth_tz=${chart.meta?.birth_tz}&year=${year}`,
        );
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        const json: MonthlyPosition[] = await res.json();
        if (!cancelled) setPositions(json);
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof Error
              ? e.message
              : "Failed to fetch ephemeris positions",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchPositions();
    return () => {
      cancelled = true;
    };
  }, [
    chart?.meta?.birth_datetime,
    chart?.meta?.birth_lat,
    chart?.meta?.birth_lon,
    chart?.meta?.birth_tz,
  ]);

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const svg = svgRef.current;
    if (!svg || !positions) return;

    const rect = svg.getBoundingClientRect();
    const scaleX = rect.width / VB_W;
    const scaleY = rect.height / VB_H;
    const mx = (e.clientX - rect.left) / scaleX;
    const my = (e.clientY - rect.top) / scaleY;

    if (
      mx < MARGIN.left ||
      mx > VB_W - MARGIN.right ||
      my < MARGIN.top ||
      my > VB_H - MARGIN.bottom
    ) {
      setTooltip(null);
      return;
    }

    const xNorm = (mx - MARGIN.left) / PLOT_W;
    const yNorm = (my - MARGIN.top) / PLOT_H;
    const monthIdx = Math.round(xNorm * 11);
    const clampedMonth = Math.max(0, Math.min(11, monthIdx));
    const rashiIdx = rashiForY(yNorm);

    const pos = positions[clampedMonth];
    if (!pos) {
      setTooltip(null);
      return;
    }

    let closest = "";
    let minDist = Infinity;
    for (const planet of PLANET_ORDER) {
      const lon = pos[planet] as number | undefined;
      if (lon == null) continue;
      const yPos = MARGIN.top + (1 - lon / 360) * PLOT_H;
      const dist = Math.abs(my - yPos);
      if (dist < minDist && dist < 30) {
        minDist = dist;
        closest = planet;
      }
    }

    if (!closest) {
      setTooltip(null);
      return;
    }

    const lon = pos[closest] as number;
    const rashi = longitudeToRashi(lon);
    setTooltip({
      planet: closest,
      date: pos.date,
      rashi: `${rashi.short} (${rashi.name})`,
      degree: formatDegree(lon),
    });
  };

  const handleMouseLeave = () => setTooltip(null);

  // ── Loading ───────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-3 py-16 text-text-muted text-sm">
        <span className="grid h-7 w-7 place-items-center rounded-lg bg-accent/15 text-accent">
          <Loader className="h-4 w-4 animate-spin" />
        </span>
        Computing ephemeris positions…
      </div>
    );
  }

  // ── Error ─────────────────────────────────────────────────────────────────

  if (error) {
    return (
      <div className="flex flex-col items-center gap-3 py-16 text-text-muted text-sm">
        <span className="text-xs font-mono px-3 py-1 rounded-md bg-danger/10 text-danger">
          {error}
        </span>
        <button
          onClick={() => {
            setError(null);
            setPositions(null);
          }}
          className="text-accent hover:underline text-xs"
        >
          Retry
        </button>
      </div>
    );
  }

  // ── Empty ─────────────────────────────────────────────────────────────────

  if (!positions) {
    return (
      <div className="flex flex-col items-center gap-2 py-16 text-text-muted text-sm">
        <p>No ephemeris data available.</p>
      </div>
    );
  }

  // ── Render chart ──────────────────────────────────────────────────────────

  const plotLeft = MARGIN.left;
  const plotTop = MARGIN.top;
  const plotRight = VB_W - MARGIN.right;
  const plotBottom = VB_H - MARGIN.bottom;

  return (
    <div className="w-full relative">
      <div
        className="absolute z-10 pointer-events-none"
        style={{
          left: tooltip ? `calc(${tooltip ? "50%" : "0"} - 120px)` : "-9999px",
          top: "8px",
        }}
      >
        {tooltip && (
          <div className="rounded-lg border border-hairline bg-card px-3 py-2 text-xs shadow-sm pointer-events-none">
            <span className="font-medium text-text-main">{tooltip.planet}</span>
            <span className="text-text-muted ml-1.5">{tooltip.date}</span>
            <br />
            <span className="text-accent font-mono">
              {tooltip.rashi}
            </span>
            <span className="text-text-muted font-mono ml-1">
              {tooltip.degree}
            </span>
          </div>
        )}
      </div>

      <svg
        ref={svgRef}
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        className="w-full h-auto"
        role="img"
        aria-label="Annual ephemeris chart showing planet positions by month"
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
        {/* Background */}
        <rect
          x={plotLeft}
          y={plotTop}
          width={PLOT_W}
          height={PLOT_H}
          fill="var(--color-card)"
        />

        {/* Rashi horizontal bands */}
        {Array.from({ length: 12 }, (_, i) => {
          const rIdx = 11 - i;
          const y = plotTop + (i / 12) * PLOT_H;
          const h = PLOT_H / 12;
          return (
            <g key={rIdx}>
              <rect
                x={plotLeft}
                y={y}
                width={PLOT_W}
                height={h}
                fill={i % 2 === 0 ? "color-mix(in srgb, var(--color-accent) 4%, transparent)" : "transparent"}
              />
              <line
                x1={plotLeft}
                y1={y}
                x2={plotRight}
                y2={y}
                stroke="var(--color-hairline)"
                strokeWidth={0.5}
              />
              <text
                x={plotLeft - 6}
                y={y + h / 2}
                textAnchor="end"
                fontSize={11}
                fill="var(--color-text-muted)"
                className="font-mono"
                dominantBaseline="central"
              >
                {RASHI_SHORT[rIdx]}
              </text>
            </g>
          );
        })}
        {/* Bottom border of last band */}
        <line
          x1={plotLeft}
          y1={plotBottom}
          x2={plotRight}
          y2={plotBottom}
          stroke="var(--color-hairline)"
          strokeWidth={0.5}
        />

        {/* Vertical month grid lines */}
        {Array.from({ length: 12 }, (_, i) => {
          const x = plotLeft + (i / 11) * PLOT_W;
          return (
            <g key={i}>
              <line
                x1={x}
                y1={plotTop}
                x2={x}
                y2={plotBottom}
                stroke={i === 0 || i === 11 ? "var(--color-hairline)" : "var(--color-hairline)"}
                strokeWidth={0.5}
              />
              <text
                x={x}
                y={plotBottom + 18}
                textAnchor="middle"
                fontSize={11}
                fill="var(--color-text-muted)"
                className="font-mono"
              >
                {MONTHS[i]}
              </text>
            </g>
          );
        })}

        {/* Plot border */}
        <rect
          x={plotLeft}
          y={plotTop}
          width={PLOT_W}
          height={PLOT_H}
          fill="none"
          stroke="var(--color-hairline)"
          strokeWidth={1}
        />

        {/* Planet polylines */}
        {PLANET_ORDER.map((planet) => {
          const points = positions
            .map((p, idx) => {
              const lon = p[planet] as number | undefined;
              if (lon == null) return null;
              const x = plotLeft + (idx / 11) * PLOT_W;
              const y = plotTop + (1 - lon / 360) * PLOT_H;
              return `${x.toFixed(1)},${y.toFixed(1)}`;
            })
            .filter(Boolean);

          if (points.length < 2) return null;

          const color = PLANET_COLORS[planet] ?? "#94a3b8";

          return (
            <polyline
              key={planet}
              points={points.join(" ")}
              fill="none"
              stroke={color}
              strokeWidth={1.8}
              strokeLinejoin="round"
              strokeLinecap="round"
              opacity={0.85}
            />
          );
        })}

        {/* Planet dots on each polyline */}
        {PLANET_ORDER.map((planet) =>
          positions.map((p, idx) => {
            const lon = p[planet] as number | undefined;
            if (lon == null) return null;
            const x = plotLeft + (idx / 11) * PLOT_W;
            const y = plotTop + (1 - lon / 360) * PLOT_H;
            const color = PLANET_COLORS[planet] ?? "#94a3b8";
            return (
              <circle
                key={`${planet}-${idx}`}
                cx={x}
                cy={y}
                r={3}
                fill={color}
                stroke="var(--color-card)"
                strokeWidth={1}
              />
            );
          }),
        )}

        {/* Planet legend at top */}
        <g transform={`translate(${plotLeft}, ${plotTop - 28})`}>
          {PLANET_ORDER.map((planet, i) => {
            const color = PLANET_COLORS[planet] ?? "#94a3b8";
            const x = i * 72;
            return (
              <g key={planet} transform={`translate(${x}, 0)`}>
                <circle cx={5} cy={5} r={4} fill={color} />
                <text
                  x={14}
                  y={9}
                  fontSize={11}
                  fill="var(--color-text-muted)"
                  className="font-mono"
                >
                  {planet}
                </text>
              </g>
            );
          })}
        </g>

        {/* Title */}
        <text
          x={VB_W / 2}
          y={plotTop - 36}
          textAnchor="middle"
          fontSize={13}
          fontWeight={600}
          fill="var(--color-text-main)"
          className="font-display"
        >
          Annual Ephemeris — {new Date().getFullYear()}
        </text>
      </svg>
    </div>
  );
}
