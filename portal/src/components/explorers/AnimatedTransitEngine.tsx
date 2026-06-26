"use client";

import { useState, useEffect, useRef, useCallback, useReducer, useMemo } from "react";
import { Play, Pause, SkipBack, SkipForward } from "lucide-react";
import { motion } from "motion/react";
import type { ChartData, Dignity } from "@/lib/types";

// ── Constants ───────────────────────────────────────────────────────────────

const CVCE_BASE_URL =
  process.env.NEXT_PUBLIC_CVCE_BASE_URL ?? "https://vedicastro-cvce.fly.dev";

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

const PLANETS = [
  "Sun",
  "Moon",
  "Mars",
  "Mercury",
  "Jupiter",
  "Venus",
  "Saturn",
  "Rahu",
  "Ketu",
];

const RASHI_SHORT = ["Ar", "Ta", "Ge", "Ca", "Le", "Vi", "Li", "Sc", "Sg", "Cp", "Aq", "Pi"];

const MONTH_NAMES = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

const SPEEDS: readonly number[] = [1, 2, 5, 10] as const;

// ── Types ───────────────────────────────────────────────────────────────────

type Speed = 1 | 2 | 5 | 10;

interface AnimState {
  dateIndex: number;
  playing: boolean;
  speed: Speed;
}

type AnimAction =
  | { type: "SET_DATE_INDEX"; index: number }
  | { type: "PLAY" }
  | { type: "PAUSE" }
  | { type: "TOGGLE_PLAY" }
  | { type: "STEP_FORWARD" }
  | { type: "STEP_BACKWARD" }
  | { type: "SET_SPEED"; speed: Speed };

interface CellData {
  signIndex: number;
  dignity?: Dignity;
}

interface TransitPlanet {
  planet: string;
  signIndex: number;
  rashi?: string;
  dignity?: Dignity;
}

interface TransitResponse {
  planets?: TransitPlanet[];
  [key: string]: unknown;
}

// ── Reducer ─────────────────────────────────────────────────────────────────

function animReducer(state: AnimState, action: AnimAction): AnimState {
  switch (action.type) {
    case "SET_DATE_INDEX":
      return { ...state, dateIndex: Math.max(0, Math.min(11, action.index)) };
    case "PLAY":
      return { ...state, playing: true };
    case "PAUSE":
      return { ...state, playing: false };
    case "TOGGLE_PLAY":
      return { ...state, playing: !state.playing };
    case "STEP_FORWARD":
      return {
        ...state,
        dateIndex: state.dateIndex < 11 ? state.dateIndex + 1 : 0,
      };
    case "STEP_BACKWARD":
      return {
        ...state,
        dateIndex: state.dateIndex > 0 ? state.dateIndex - 1 : 11,
      };
    case "SET_SPEED":
      return { ...state, speed: action.speed };
    default:
      return state;
  }
}

// ── Helpers ─────────────────────────────────────────────────────────────────

const ANIM_BASE_DELAY = 450;

function getDignityCellClass(dignity?: Dignity): string {
  switch (dignity) {
    case "exalted":
      return "ring-1 ring-inset ring-amber-300/50 shadow-[inset_0_0_6px_rgba(245,158,11,0.25)]";
    case "own":
      return "font-semibold";
    case "debilitated":
      return "opacity-45";
    default:
      return "";
  }
}

function formatMonthYear(months: Date[], index: number): string {
  if (index < 0 || index >= months.length) return "";
  const d = months[index];
  return `${MONTH_NAMES[d.getMonth()]} ${d.getFullYear()}`;
}

// ── Sub-components ──────────────────────────────────────────────────────────

function SkeletonGrid() {
  return (
    <div className="space-y-1 animate-pulse">
      <div className="grid gap-px" style={{ gridTemplateColumns: "80px repeat(12, minmax(44px, 1fr))" }}>
        <div className="h-7 rounded bg-[color-mix(in_srgb,var(--color-accent)_8%,transparent)]" />
        {Array.from({ length: 12 }).map((_, i) => (
          <div
            key={i}
            className="h-7 rounded bg-[color-mix(in_srgb,var(--color-accent)_5%,transparent)]"
          />
        ))}
      </div>
      {Array.from({ length: 9 }).map((_, r) => (
        <div
          key={r}
          className="grid gap-px"
          style={{ gridTemplateColumns: "80px repeat(12, minmax(44px, 1fr))" }}
        >
          <div className="h-8 rounded bg-[color-mix(in_srgb,var(--color-accent)_10%,transparent)]" />
          {Array.from({ length: 12 }).map((_, c) => (
            <div
              key={c}
              className="h-8 rounded bg-[color-mix(in_srgb,var(--color-accent)_6%,transparent)]"
            />
          ))}
        </div>
      ))}
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────────────────

export default function AnimatedTransitEngine({ chart }: { chart?: ChartData }) {
  const [animState, dispatch] = useReducer(animReducer, {
    dateIndex: 0,
    playing: false,
    speed: 1,
  });

  const [transitGrid, setTransitGrid] = useState<CellData[][]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [columnWidth, setColumnWidth] = useState(52);

  const timelineRef = useRef<HTMLDivElement>(null);
  const rafId = useRef(0);
  const draggingRef = useRef(false);

  // ── Generate 12 monthly dates ─────────────────────────────────────────────

  const months = useMemo(() => {
    const now = new Date();
    const year = now.getFullYear();
    return Array.from({ length: 12 }, (_, i) => new Date(year, i, 15));
  }, []);

  // ── Fetch transit positions for every month ───────────────────────────────

  useEffect(() => {
    if (months.length === 0) return;

    let cancelled = false;

    async function fetchTransits() {
      setLoading(true);
      setError(null);

      const lat = chart?.meta?.birth_lat ?? 12.3;
      const lon = chart?.meta?.birth_lon ?? 76.65;
      const tz = chart?.meta?.birth_tz ?? 5.5;

      try {
        const responses = await Promise.all(
          months.map((date) => {
            const dateStr = date.toISOString().slice(0, 10);
            return fetch(`${CVCE_BASE_URL}/positions`, {
              method: "POST",
              headers: { "content-type": "application/json" },
              body: JSON.stringify({ datetime: dateStr + "T12:00:00", lat, lon, tz_offset: tz, ayanamsa: "LAHIRI" }),
            }).then(async (res) => {
              if (!res.ok) {
                throw new Error(`Engine returned ${res.status} for ${dateStr}`);
              }
              return (await res.json()) as TransitResponse;
            });
          }),
        );

        if (cancelled) return;

        const grid: CellData[][] = PLANETS.map((planet) =>
          responses.map((res) => {
            const p = res.planets?.find((bp) => bp.planet === planet);
            return {
              signIndex: p?.signIndex ?? 0,
              dignity: p?.dignity ?? undefined,
            };
          }),
        );

        setTransitGrid(grid);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load transit data");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchTransits();
    return () => {
      cancelled = true;
    };
  }, [months, chart?.meta?.birth_lat, chart?.meta?.birth_lon, chart?.meta?.birth_tz]);

  // ── rAF animation loop for autoplay ──────────────────────────────────────

  useEffect(() => {
    if (!animState.playing) {
      cancelAnimationFrame(rafId.current);
      return;
    }

    const interval = ANIM_BASE_DELAY / animState.speed;
    let lastTime = performance.now();

    function loop(now: number) {
      if (now - lastTime >= interval) {
        lastTime = now - ((now - lastTime) % interval);
        dispatch({ type: "STEP_FORWARD" });
      }
      rafId.current = requestAnimationFrame(loop);
    }

    rafId.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(rafId.current);
  }, [animState.playing, animState.speed]);

  // ── Drag helpers ──────────────────────────────────────────────────────────

  const computeIndexFromClientX = useCallback((clientX: number): number => {
    const el = timelineRef.current;
    if (!el) return 0;
    const rect = el.getBoundingClientRect();
    const x = clientX - rect.left;
    const colCount = 12;
    const effective = rect.width / colCount;
    return Math.max(0, Math.min(colCount - 1, Math.round(x / effective - 0.5)));
  }, []);

  // ── Drag handlers (declared before mouse-down for hoisting) ───────────────

  const handleGlobalMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!draggingRef.current) return;
      const idx = computeIndexFromClientX(e.clientX);
      dispatch({ type: "SET_DATE_INDEX", index: idx });
    },
    [computeIndexFromClientX],
  );

  const handleGlobalMouseUp = useCallback(() => {
    draggingRef.current = false;
    setIsDragging(false);
    document.removeEventListener("mousemove", handleGlobalMouseMove);
  }, [handleGlobalMouseMove]);

  const handleTimelineMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      draggingRef.current = true;
      setIsDragging(true);

      const el = timelineRef.current;
      if (el) {
        const rect = el.getBoundingClientRect();
        setColumnWidth(rect.width / 12);
      }

      const idx = computeIndexFromClientX(e.clientX);
      dispatch({ type: "PAUSE" });
      dispatch({ type: "SET_DATE_INDEX", index: idx });

      document.addEventListener("mousemove", handleGlobalMouseMove);
      document.addEventListener("mouseup", handleGlobalMouseUp, { once: true });
    },
    [computeIndexFromClientX, handleGlobalMouseMove, handleGlobalMouseUp],
  );

  // ── Computed playhead position ────────────────────────────────────────────

  const playheadPct = useMemo(() => {
    return ((animState.dateIndex + 0.5) / 12) * 100;
  }, [animState.dateIndex]);

  // ── Motion transition based on drag state ─────────────────────────────────

  const playheadTransition = useMemo(() => {
    return isDragging
      ? { duration: 0 }
      : { type: "spring" as const, stiffness: 280, damping: 26, mass: 0.4 };
  }, [isDragging]);

  // ── Empty / no-chart state ────────────────────────────────────────────────

  if (!chart) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-16 text-text-muted">
        <span className="text-sm font-mono">No chart data available</span>
        <span className="text-xs">
          Load or generate a chart to explore transits.
        </span>
      </div>
    );
  }

  // ── Error state ───────────────────────────────────────────────────────────

  if (error && transitGrid.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-16">
        <span className="text-sm font-mono text-text-muted">
          Could not load transit data
        </span>
        <span className="text-xs font-mono text-[color-mix(in_srgb,var(--color-danger)_80%,transparent)]">
          {error}
        </span>
      </div>
    );
  }

  // ── Main render ───────────────────────────────────────────────────────────

  return (
    <div className="space-y-3">
      {/* ═══ Horizontal scroll container (timeline + grid) ═══ */}
      <div className="overflow-x-auto rounded-xl border border-hairline bg-card">
        <div className="min-w-[720px] relative select-none">
          {/* ── Timeline bar ──────────────────────────────────────────────── */}
          <div
            ref={timelineRef}
            className="h-12 relative cursor-pointer border-b border-hairline"
            onMouseDown={handleTimelineMouseDown}
          >
            {/* Month label markers */}
            {months.map((m, i) => {
              const isActive = i === animState.dateIndex;
              return (
                <div
                  key={i}
                  className="absolute top-0 h-full flex flex-col items-center justify-center"
                  style={{ left: `${((i + 0.5) / 12) * 100}%`, transform: "translateX(-50%)" }}
                >
                  <span
                    className="text-[10px] font-mono uppercase tracking-wider transition-colors"
                    style={{
                      color: isActive
                        ? "var(--color-accent)"
                        : "var(--color-text-muted)",
                    }}
                  >
                    {MONTH_NAMES[m.getMonth()]}
                  </span>
                  <span
                    className="text-[9px] font-mono transition-colors"
                    style={{
                      color: isActive
                        ? "var(--color-accent)"
                        : "var(--color-text-muted)",
                    }}
                  >
                    {m.getFullYear()}
                  </span>
                </div>
              );
            })}

            {/* Playhead vertical line */}
            <motion.div
              className="absolute top-0 bottom-0 w-px pointer-events-none z-10"
              style={{ backgroundColor: "var(--color-accent)" }}
              animate={{ left: `${playheadPct}%` }}
              transition={playheadTransition}
            >
              {/* Playhead triangle handle */}
              <div
                className="absolute -top-0.5 left-1/2 -translate-x-1/2 w-0 h-0"
                style={{
                  borderLeft: "5px solid transparent",
                  borderRight: "5px solid transparent",
                  borderTop: "6px solid var(--color-accent)",
                }}
              />
              {/* Playhead dot handle */}
              <div
                className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2.5 h-2.5 rounded-full"
                style={{
                  backgroundColor: "var(--color-accent)",
                  boxShadow: "0 0 6px color-mix(in srgb, var(--color-accent) 50%, transparent)",
                }}
              />
            </motion.div>
          </div>

          {/* ── Current month label below timeline ────────────────────────── */}
          <div className="px-3 py-1.5 border-b border-hairline flex items-center">
            <motion.span
              className="text-xs font-mono font-semibold"
              style={{ color: "var(--color-accent)" }}
              key={animState.dateIndex}
              initial={{ opacity: 0.6, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.15 }}
            >
              {formatMonthYear(months, animState.dateIndex)}
            </motion.span>
          </div>

          {/* ── Transit grid (sticky first column) ───────────────────────── */}
          <div className="relative">
            {loading ? (
              <div className="p-3">
                <SkeletonGrid />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse" style={{ minWidth: 720 }}>
                  {/* Month header row */}
                  <thead>
                    <tr>
                      <th
                        className="sticky left-0 z-20 bg-card px-2.5 py-2 text-left text-[10px] uppercase tracking-wider text-text-muted font-medium border-b border-hairline"
                        style={{ minWidth: 76 }}
                      >
                        Planet
                      </th>
                      {months.map((m, i) => {
                        const isActive = i === animState.dateIndex;
                        return (
                          <th
                            key={i}
                            className="px-1 py-2 text-center text-[10px] font-mono uppercase tracking-wider border-b border-hairline transition-colors"
                            style={{
                              minWidth: 44,
                              color: isActive
                                ? "var(--color-accent)"
                                : "var(--color-text-muted)",
                              backgroundColor: isActive
                                ? "color-mix(in srgb, var(--color-accent) 6%, transparent)"
                                : "transparent",
                            }}
                          >
                            {MONTH_NAMES[m.getMonth()]}
                          </th>
                        );
                      })}
                    </tr>
                  </thead>

                  <tbody>
                    {PLANETS.map((planet, pi) => (
                      <tr key={planet}>
                        {/* Sticky planet name cell */}
                        <td
                          className="sticky left-0 z-10 bg-card px-2.5 py-2 border-b border-hairline/60"
                          style={{ minWidth: 76 }}
                        >
                          <span
                            className="text-xs font-semibold font-mono tracking-wide"
                            style={{ color: PLANET_COLORS[planet] }}
                          >
                            {planet}
                          </span>
                        </td>

                        {/* Transit cells */}
                        {months.map((_, mi) => {
                          const cell = transitGrid[pi]?.[mi];
                          const si = cell?.signIndex ?? 0;
                          const isActive = mi === animState.dateIndex;
                          const color = PLANET_COLORS[planet];

                          return (
                            <td
                              key={mi}
                              className={`text-center px-1 py-2 border-b border-hairline/60 transition-all duration-200 ${getDignityCellClass(cell?.dignity)}`}
                              style={{
                                minWidth: 44,
                                backgroundColor: isActive
                                  ? `color-mix(in srgb, ${color} 10%, transparent)`
                                  : "transparent",
                              }}
                            >
                              <span
                                className="text-[11px] font-mono font-medium inline-block"
                                style={{ color }}
                                title={`${planet} in ${RASHI_SHORT[si]}${cell?.dignity ? ` (${cell.dignity})` : ""}`}
                              >
                                {RASHI_SHORT[si]}
                              </span>
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* ── Active-column highlight overlay ───────────────────────────── */}
          {!loading && transitGrid.length > 0 && (
            <motion.div
              className="absolute top-0 bottom-0 pointer-events-none"
              style={{
                left: `calc(76px + ${playheadPct}% * ((100% - 76px) / 100%))`,
                width: columnWidth,
                background:
                  "color-mix(in srgb, var(--color-accent) 3%, transparent)",
                borderLeft: "1px solid color-mix(in srgb, var(--color-accent) 12%, transparent)",
                borderRight: "1px solid color-mix(in srgb, var(--color-accent) 12%, transparent)",
              }}
              animate={
                isDragging
                  ? {}
                  : {
                      left: `calc(76px + ${playheadPct}% * ((100% - 76px) / 100%))`,
                    }
              }
              transition={playheadTransition}
            />
          )}
        </div>
      </div>

      {/* ═══ Controls ═══ */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        {/* Transport controls */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => dispatch({ type: "STEP_BACKWARD" })}
            className="p-2 rounded-lg text-text-muted hover:text-text-main hover:bg-[color-mix(in_srgb,var(--color-accent)_8%,transparent)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
            aria-label="Previous month"
          >
            <SkipBack className="w-4 h-4" />
          </button>

          <button
            onClick={() => dispatch({ type: "TOGGLE_PLAY" })}
            className="p-2 rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
            style={{
              color: "var(--color-accent)",
              backgroundColor: "color-mix(in srgb, var(--color-accent) 12%, transparent)",
            }}
            aria-label={animState.playing ? "Pause" : "Play"}
          >
            {animState.playing ? (
              <Pause className="w-4 h-4" />
            ) : (
              <Play className="w-4 h-4" />
            )}
          </button>

          <button
            onClick={() => dispatch({ type: "STEP_FORWARD" })}
            className="p-2 rounded-lg text-text-muted hover:text-text-main hover:bg-[color-mix(in_srgb,var(--color-accent)_8%,transparent)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
            aria-label="Next month"
          >
            <SkipForward className="w-4 h-4" />
          </button>
        </div>

        {/* Speed selector */}
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] uppercase tracking-wider text-text-muted">
            Speed
          </span>
          <div className="inline-flex rounded-lg border border-hairline p-0.5">
            {SPEEDS.map((s) => (
              <button
                key={s}
                onClick={() => dispatch({ type: "SET_SPEED", speed: s as Speed })}
                className={`px-2.5 py-1 min-h-[36px] rounded-md text-[11px] font-mono transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 ${
                  animState.speed === s
                    ? "bg-accent text-accent-fg"
                    : "text-text-muted hover:text-text-main"
                }`}
              >
                {s}&times;
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
