"use client";

import { useCallback, useRef } from "react";
import type { PersonTimeline, TimelineMilestone } from "@/lib/types";
import { planetColor } from "@/lib/astroColors";
import {
  type Viewport,
  ageAt,
  clampPct,
  parseDate,
  pct,
  toneOf,
} from "@/lib/timeline-view";

const TONE_FILL: Record<string, string> = {
  good: "var(--color-success)",
  bad: "var(--color-danger)",
  mixed: "var(--color-warning)",
  neutral: "var(--color-text-muted)",
};

/**
 * Whole-life overview strip: Mahadasha blocks in muted planet colour, every
 * milestone as a valence-coloured diamond, a gold "today" tick, and the
 * current viewport as a draggable brush. One glance = the shape of the life;
 * one click = navigate there.
 */
export function TimelineMinimap({
  timeline,
  milestones,
  full,
  viewport,
  now,
  birthDatetime,
  onCenter,
}: {
  timeline: PersonTimeline;
  milestones: TimelineMilestone[];
  full: Viewport;
  viewport: Viewport;
  now: number;
  birthDatetime: string;
  onCenter: (time: number) => void;
}) {
  const trackRef = useRef<HTMLDivElement>(null);
  const mahadashas = timeline.timingPeriods.filter((period) => period.level === "Mahadasha");

  const timeFromPointer = useCallback(
    (clientX: number) => {
      const rect = trackRef.current?.getBoundingClientRect();
      if (!rect || rect.width === 0) return null;
      const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
      return full.start + ratio * (full.end - full.start);
    },
    [full],
  );

  const handlePointer = useCallback(
    (event: React.PointerEvent) => {
      const time = timeFromPointer(event.clientX);
      if (time != null) onCenter(time);
    },
    [timeFromPointer, onCenter],
  );

  const decadeTicks: number[] = [];
  const birth = parseDate(birthDatetime);
  if (birth) {
    for (let age = 0; ; age += 10) {
      const tick = new Date(birth);
      tick.setUTCFullYear(tick.getUTCFullYear() + age);
      if (tick.getTime() > full.end) break;
      decadeTicks.push(tick.getTime());
    }
  }

  const brushLeft = clampPct(pct(viewport.start, full));
  const brushWidth = Math.max(0.5, clampPct(pct(viewport.end, full)) - brushLeft);
  const isLifetime = brushLeft <= 0.5 && brushWidth >= 99;

  return (
    <div className="border-b border-hairline px-4 pb-3 pt-2 sm:px-5">
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-[9px] uppercase tracking-[0.14em] text-text-muted">Whole life at a glance</span>
        <span className="font-mono text-[9px] text-text-muted">click to travel · gold line = today</span>
      </div>
      <div
        ref={trackRef}
        role="slider"
        tabIndex={0}
        aria-label="Lifetime overview. Activate a position to move the detailed view there."
        aria-valuemin={full.start}
        aria-valuemax={full.end}
        aria-valuenow={(viewport.start + viewport.end) / 2}
        aria-valuetext={new Date((viewport.start + viewport.end) / 2).getUTCFullYear().toString()}
        onPointerDown={handlePointer}
        onKeyDown={(event) => {
          const span = viewport.end - viewport.start;
          const center = (viewport.start + viewport.end) / 2;
          if (event.key === "ArrowLeft") onCenter(center - span / 2);
          if (event.key === "ArrowRight") onCenter(center + span / 2);
          if (event.key === "Home") onCenter(full.start);
          if (event.key === "End") onCenter(full.end);
        }}
        className="relative mt-1.5 h-14 cursor-crosshair touch-none select-none overflow-hidden rounded-lg border border-hairline bg-background/60 focus-visible:ring-2 focus-visible:ring-accent"
      >
        {/* Mahadasha blocks: the base rhythm of the life */}
        {mahadashas.map((period) => {
          const start = parseDate(period.startAt)?.getTime();
          const end = parseDate(period.endAt)?.getTime();
          if (start == null || end == null) return null;
          const left = clampPct(pct(start, full));
          const width = clampPct(pct(end, full)) - left;
          if (width <= 0) return null;
          return (
            <div
              key={`md-${period.ruler}-${period.startAt}`}
              aria-hidden="true"
              className="absolute inset-y-0 border-r border-hairline/60"
              style={{ left: `${left}%`, width: `${width}%`, backgroundColor: planetColor(period.ruler), opacity: 0.13 }}
            >
              {width > 4 && (
                <span className="absolute left-1 top-0.5 font-mono text-[8px] leading-none text-text-muted">
                  {period.ruler.slice(0, 2)}
                </span>
              )}
            </div>
          );
        })}

        {/* Decade age ruler */}
        {decadeTicks.map((tick, index) => (
          <div key={tick} aria-hidden="true" className="absolute bottom-0 top-8" style={{ left: `${clampPct(pct(tick, full))}%` }}>
            <div className="h-full w-px bg-hairline" />
            <span className="absolute -left-1 bottom-0.5 font-mono text-[8px] text-text-muted">{index * 10}</span>
          </div>
        ))}

        {/* Milestones as valence diamonds; observed events sit lower than windows */}
        {milestones.map((item) => {
          const start = parseDate(item.window.start_at)?.getTime();
          if (start == null) return null;
          const end = parseDate(item.window.end_at)?.getTime() ?? start;
          const mid = (start + end) / 2;
          const observed = item.origin === "observed_event" || item.origin === "imported_history";
          return (
            <span
              key={item.milestone_id}
              aria-hidden="true"
              className="absolute size-1.5 -translate-x-1/2 rotate-45"
              style={{
                left: `${clampPct(pct(mid, full))}%`,
                top: observed ? "26px" : "14px",
                backgroundColor: TONE_FILL[toneOf(item)],
                opacity: observed ? 1 : 0.85,
              }}
            />
          );
        })}

        {/* Today */}
        <div aria-hidden="true" className="absolute inset-y-0 w-0.5 bg-accent" style={{ left: `${clampPct(pct(now, full))}%` }} />

        {/* Viewport brush */}
        {!isLifetime && (
          <div
            aria-hidden="true"
            className="absolute inset-y-0 rounded-sm border-2 border-primary/70 bg-primary/10"
            style={{ left: `${brushLeft}%`, width: `${brushWidth}%` }}
          />
        )}
      </div>
      <div className="mt-1 flex justify-between font-mono text-[8px] text-text-muted" aria-hidden="true">
        <span>birth · {birth?.getUTCFullYear() ?? "—"}</span>
        <span>today · age {ageAt(now, birthDatetime) ?? "—"}</span>
        <span>{new Date(full.end).getUTCFullYear()}</span>
      </div>
    </div>
  );
}
