"use client";

import { useCallback, useMemo, useRef } from "react";
import { clsx } from "clsx";
import { LockKeyhole } from "lucide-react";
import type {
  TimelineMilestone,
  TimelineOutcomeProjection,
  TimelineTimingPeriod,
} from "@/lib/types";
import { planetColor } from "@/lib/astroColors";
import {
  type ValenceTone,
  type Viewport,
  TONE_LABELS,
  ageAt,
  axisTicks,
  clampPct,
  formatTick,
  packRows,
  parseDate,
  pct,
  toneOf,
} from "@/lib/timeline-view";

const DAY_MS = 24 * 60 * 60 * 1000;

const TONE_BAND: Record<ValenceTone, string> = {
  good: "border-success/60 bg-success/10 text-success",
  bad: "border-danger/60 bg-danger/10 text-danger",
  mixed: "border-warning/60 bg-warning/10 text-warning",
  neutral: "border-text-muted/50 bg-text-muted/10 text-text-muted",
};

const ORIGIN_BORDER: Record<TimelineMilestone["origin"], string> = {
  observed_event: "border-solid border-2",
  imported_history: "border-solid border-2",
  prospective_prediction: "border-solid border-2",
  engine_inference: "border-dotted border-2",
  retrospective_hypothesis: "border-dashed border-2",
};

const OUTCOME_GLYPH: Record<TimelineOutcomeProjection["status"], string> = {
  hit: "✓ hit",
  partial_hit: "◐ partial",
  miss: "✗ miss",
  false_alarm: "✗ false alarm",
  ambiguous: "· ambiguous",
  unresolved: "… unresolved",
};

const ROW_HEIGHT = 36;
const LANE_PAD = 8;

type MilestoneRow = { item: TimelineMilestone; row: number };

function laneHeight(rows: number, minimum = 1) {
  return Math.max(rows, minimum) * ROW_HEIGHT + LANE_PAD * 2;
}

function windowTimes(item: TimelineMilestone): { start: number; end: number } {
  const start = parseDate(item.window.start_at)?.getTime() ?? 0;
  const end = parseDate(item.window.end_at)?.getTime() ?? start;
  return { start, end: Math.max(end, start) };
}

function Lane({
  label,
  sublabel,
  height,
  children,
}: {
  label: string;
  sublabel?: string;
  height: number;
  children: React.ReactNode;
}) {
  return (
    <div className="flex border-b border-hairline last:border-b-0">
      <div className="w-28 shrink-0 border-r border-hairline bg-background/50 px-3 py-2 sm:w-36">
        <span className="block text-[11px] font-semibold leading-tight text-text-main">{label}</span>
        {sublabel && <span className="mt-0.5 block text-[9px] leading-snug text-text-muted">{sublabel}</span>}
      </div>
      <div className="relative min-w-0 flex-1" style={{ height }}>
        {children}
      </div>
    </div>
  );
}

/**
 * The detailed instrument: packed valence-coloured lanes over a shared time
 * axis, with the Vimshottari ribbon underneath and a gold "today" line
 * through everything. Drag horizontally to travel; click any record to open
 * its evidence.
 */
export function TimelineCanvas({
  milestones,
  periods,
  outcomes,
  viewport,
  now,
  birthDatetime,
  selectedId,
  onSelect,
  onCenter,
}: {
  milestones: TimelineMilestone[];
  periods: TimelineTimingPeriod[];
  outcomes: TimelineOutcomeProjection[];
  viewport: Viewport;
  now: number;
  birthDatetime: string;
  selectedId: string | null;
  onSelect: (milestone: TimelineMilestone) => void;
  onCenter: (time: number) => void;
}) {
  const surfaceRef = useRef<HTMLDivElement>(null);
  const drag = useRef<{ startX: number; startCenter: number; moved: boolean } | null>(null);
  const spanDays = (viewport.end - viewport.start) / DAY_MS;

  const events = useMemo<MilestoneRow[]>(() => {
    const list = milestones.filter((item) => item.origin === "observed_event" || item.origin === "imported_history");
    return packRows(list, (item) => windowTimes(item).start, (item) => windowTimes(item).end);
  }, [milestones]);

  const windows = useMemo<MilestoneRow[]>(() => {
    const list = milestones.filter((item) => item.origin !== "observed_event" && item.origin !== "imported_history");
    return packRows(list, (item) => windowTimes(item).start, (item) => windowTimes(item).end);
  }, [milestones]);

  const mahadashas = useMemo(
    () => periods.filter((period) => period.level === "Mahadasha"),
    [periods],
  );
  const antardashas = useMemo(
    () => (spanDays <= 5600 ? periods.filter((period) => period.level === "Antardasha") : []),
    [periods, spanDays],
  );

  const outcomeByPrediction = useMemo(
    () => new Map(outcomes.map((item) => [item.predictionMilestoneId, item])),
    [outcomes],
  );

  const eventRows = events.reduce((max, entry) => Math.max(max, entry.row + 1), 0);
  const windowRows = windows.reduce((max, entry) => Math.max(max, entry.row + 1), 0);
  const dashaHeight = antardashas.length ? 64 : 40;

  const ticks = axisTicks(viewport);
  const nowPct = pct(now, viewport);

  const beginDrag = useCallback((event: React.PointerEvent) => {
    if ((event.target as HTMLElement).closest("button, a")) return;
    drag.current = { startX: event.clientX, startCenter: (viewport.start + viewport.end) / 2, moved: false };
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
  }, [viewport]);

  const moveDrag = useCallback((event: React.PointerEvent) => {
    if (!drag.current) return;
    const rect = surfaceRef.current?.getBoundingClientRect();
    if (!rect || rect.width === 0) return;
    const deltaPx = event.clientX - drag.current.startX;
    if (Math.abs(deltaPx) > 4) drag.current.moved = true;
    if (!drag.current.moved) return;
    const deltaTime = (deltaPx / rect.width) * (viewport.end - viewport.start);
    onCenter(drag.current.startCenter - deltaTime);
  }, [viewport, onCenter]);

  const endDrag = useCallback(() => {
    drag.current = null;
  }, []);

  const band = (entry: MilestoneRow) => {
    const { item, row } = entry;
    const { start, end } = windowTimes(item);
    const left = pct(start, viewport);
    const right = pct(end, viewport);
    if (right < 0 || left > 100) return null;
    const visLeft = clampPct(left);
    const visWidth = Math.max(clampPct(right) - visLeft, 0.9);
    const tone = toneOf(item);
    const outcome = outcomeByPrediction.get(item.milestone_id);
    const peak = item.window.peak_at ? parseDate(item.window.peak_at)?.getTime() : null;
    const sealed = item.origin === "prospective_prediction";
    return (
      <button
        key={item.milestone_id}
        type="button"
        onClick={() => onSelect(item)}
        aria-pressed={selectedId === item.milestone_id}
        aria-label={`${item.title}, ${TONE_LABELS[tone]}, ${item.window.start_at.slice(0, 10)} to ${item.window.end_at.slice(0, 10)}${outcome ? `, outcome ${outcome.status.replaceAll("_", " ")}` : ""}`}
        title={item.title}
        className={clsx(
          "absolute flex h-7 items-center gap-1 overflow-hidden rounded-md px-1.5 text-left text-[10px] font-semibold transition-[transform,z-index] hover:z-20 hover:scale-y-110 focus-visible:z-20 focus-visible:ring-2 focus-visible:ring-accent",
          TONE_BAND[tone],
          ORIGIN_BORDER[item.origin],
          selectedId === item.milestone_id && "z-20 ring-2 ring-accent ring-offset-1 ring-offset-card",
        )}
        style={{ left: `${visLeft}%`, width: `${visWidth}%`, minWidth: 20, top: LANE_PAD + row * ROW_HEIGHT }}
      >
        {sealed && <LockKeyhole aria-hidden="true" className="size-2.5 shrink-0" />}
        {peak != null && peak >= viewport.start && peak <= viewport.end && (
          <span
            aria-hidden="true"
            className="absolute inset-y-0 w-px bg-current opacity-80"
            style={{ left: `${clampPct(((pct(peak, viewport) - visLeft) / visWidth) * 100)}%` }}
          />
        )}
        <span className="truncate">{item.title.replace(/\s*—\s*migrated research candidate$/i, "")}</span>
        {outcome && (
          <span className="ml-auto shrink-0 rounded-sm bg-card/80 px-1 font-mono text-[8px]">
            {OUTCOME_GLYPH[outcome.status]}
          </span>
        )}
      </button>
    );
  };

  return (
    <div
      ref={surfaceRef}
      role="group"
      className="relative cursor-grab touch-pan-y select-none active:cursor-grabbing"
      onPointerDown={beginDrag}
      onPointerMove={moveDrag}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      aria-label="Person timeline canvas. Drag horizontally to move through time; the earlier, today and later buttons do the same from the keyboard."
    >
      {/* Axis */}
      <div className="flex border-b border-hairline">
        <div className="w-28 shrink-0 border-r border-hairline bg-background/50 sm:w-36" />
        <div className="relative h-10 min-w-0 flex-1">
          <NowLine nowPct={nowPct} label />
          {ticks.map((tick, index) => {
            const age = ageAt(tick, birthDatetime);
            return (
              <div
                key={tick}
                className={clsx(
                  "absolute top-1 font-mono text-[9px] leading-tight text-text-muted",
                  index === 0 ? "" : index === ticks.length - 1 ? "-translate-x-full" : "-translate-x-1/2",
                  index % 2 === 1 && "hidden sm:block",
                )}
                style={{ left: `${(index / (ticks.length - 1)) * 100}%` }}
              >
                <span className="block whitespace-nowrap">{formatTick(tick, viewport)}</span>
                {age != null && <span className="block text-[8px] opacity-70">age {age}</span>}
              </div>
            );
          })}
        </div>
      </div>

      {/* Lanes wrapper so the now-line can span all of them */}
      <div className="relative">
        <Lane label="Life events" sublabel="observed history" height={laneHeight(eventRows)}>
          <Gridlines />
          <NowLine nowPct={nowPct} />
          {events.map(band)}
          {events.length === 0 && (
            <p className="absolute inset-0 flex items-center px-4 text-[11px] text-text-muted">
              No observed events in this range — add one to anchor the research to real life.
            </p>
          )}
        </Lane>

        <Lane label="Windows" sublabel="predictions & research" height={laneHeight(windowRows)}>
          <Gridlines />
          <NowLine nowPct={nowPct} />
          {windows.map(band)}
          {windows.length === 0 && (
            <p className="absolute inset-0 flex items-center px-4 text-[11px] text-text-muted">
              No prediction or research window overlaps this range.
            </p>
          )}
        </Lane>

        <Lane label="Dasha clock" sublabel={antardashas.length ? "MD + AD" : "Mahadasha"} height={dashaHeight}>
          <NowLine nowPct={nowPct} />
          {mahadashas.map((period) => {
            const start = parseDate(period.startAt)?.getTime();
            const end = parseDate(period.endAt)?.getTime();
            if (start == null || end == null) return null;
            const left = pct(start, viewport);
            const right = pct(end, viewport);
            if (right < 0 || left > 100) return null;
            const visLeft = clampPct(left);
            const width = clampPct(right) - visLeft;
            return (
              <div
                key={`md-${period.ruler}-${period.startAt}`}
                className="absolute flex h-6 items-center overflow-hidden border-r border-card px-1.5 font-mono text-[9px] font-semibold"
                style={{
                  left: `${clampPct(left)}%`,
                  width: `${width}%`,
                  top: 6,
                  backgroundColor: planetColor(period.ruler),
                  color: "var(--color-background)",
                  opacity: 0.82,
                }}
                title={`${period.ruler} Mahadasha · ${period.startAt.slice(0, 10)} → ${period.endAt.slice(0, 10)}`}
              >
                <span className="truncate">{period.ruler}</span>
              </div>
            );
          })}
          {antardashas.map((period) => {
            const start = parseDate(period.startAt)?.getTime();
            const end = parseDate(period.endAt)?.getTime();
            if (start == null || end == null) return null;
            const left = pct(start, viewport);
            const right = pct(end, viewport);
            if (right < 0 || left > 100) return null;
            const visLeft = clampPct(left);
            const width = clampPct(right) - visLeft;
            return (
              <div
                key={`ad-${period.parentRuler}-${period.ruler}-${period.startAt}`}
                className="absolute flex h-5 items-center overflow-hidden rounded-sm border border-card/70 px-1 font-mono text-[8px]"
                style={{
                  left: `${clampPct(left)}%`,
                  width: `${width}%`,
                  top: 36,
                  backgroundColor: planetColor(period.ruler),
                  color: "var(--color-background)",
                  opacity: 0.55,
                }}
                title={`${period.parentRuler}–${period.ruler} Antardasha · ${period.startAt.slice(0, 10)} → ${period.endAt.slice(0, 10)}`}
              >
                {width > 3 && <span className="truncate">{period.ruler}</span>}
              </div>
            );
          })}
        </Lane>

      </div>
    </div>
  );
}

function Gridlines() {
  return (
    <div
      aria-hidden="true"
      className="absolute inset-0 bg-[linear-gradient(to_right,var(--color-hairline)_1px,transparent_1px)] bg-[size:20%_100%] opacity-60"
    />
  );
}

/** Gold "today" line, rendered inside each lane's plotting area. */
function NowLine({ nowPct, label = false }: { nowPct: number; label?: boolean }) {
  if (nowPct < 0 || nowPct > 100) return null;
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-y-0 z-10 w-px bg-accent" style={{ left: `${nowPct}%` }}>
      {label && (
        <span className="absolute -top-0.5 left-1 whitespace-nowrap rounded-sm bg-accent px-1 font-mono text-[8px] font-semibold text-accent-fg">
          today
        </span>
      )}
    </div>
  );
}
