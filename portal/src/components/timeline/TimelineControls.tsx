"use client";

import { ChevronLeft, ChevronRight, Crosshair, Filter, LayoutList, Plus, Rows3 } from "lucide-react";
import { clsx } from "clsx";
import type { TimelineOrigin, TimelineZoom } from "@/lib/types";
import { type ValenceTone, TONE_LABELS } from "@/lib/timeline-view";

export const ORIGIN_LABELS: Record<TimelineOrigin, string> = {
  observed_event: "Observed events",
  prospective_prediction: "Sealed predictions",
  retrospective_hypothesis: "Retrospective research",
  imported_history: "Imported history",
  engine_inference: "Research candidates",
};

const ORIGIN_HINTS: Partial<Record<TimelineOrigin, string>> = {
  observed_event: "Added with the Add event button",
  prospective_prediction: "Sealing workflow not yet available",
  retrospective_hypothesis: "Requires observed events plus research runs",
  imported_history: "Import pipeline not yet wired",
  engine_inference: "Auto-loaded from chart yoga activations",
};

const ZOOMS: Array<[TimelineZoom, string]> = [
  ["lifetime", "Life"],
  ["decade", "10 yrs"],
  ["year", "Year"],
  ["month", "Month"],
  ["week", "Week"],
  ["day", "Day"],
];

const TONES: ValenceTone[] = ["good", "bad", "mixed", "neutral"];

const TONE_CHIP_ON: Record<ValenceTone, string> = {
  good: "border-success bg-success/10 text-success",
  bad: "border-danger bg-danger/10 text-danger",
  mixed: "border-warning bg-warning/10 text-warning",
  neutral: "border-text-muted bg-text-muted/10 text-text-main",
};

export type TimelineViewMode = "canvas" | "list";

export function TimelineControls({
  view,
  zoom,
  origins,
  originCounts,
  tones,
  onView,
  onZoom,
  onPan,
  onToday,
  onToggleOrigin,
  onToggleTone,
  onAddEvent,
}: {
  view: TimelineViewMode;
  zoom: TimelineZoom;
  origins: Set<TimelineOrigin>;
  originCounts: Record<TimelineOrigin, number>;
  tones: Set<ValenceTone>;
  onView: (view: TimelineViewMode) => void;
  onZoom: (zoom: TimelineZoom) => void;
  onPan: (direction: -1 | 1) => void;
  onToday: () => void;
  onToggleOrigin: (origin: TimelineOrigin) => void;
  onToggleTone: (tone: ValenceTone) => void;
  onAddEvent: () => void;
}) {
  return (
    <div className="flex flex-col gap-3 border-b border-hairline p-4">
      <div className="flex flex-wrap items-center gap-2">
        {/* View toggle */}
        <div role="group" aria-label="Timeline view" className="flex overflow-hidden rounded-lg border border-hairline">
          {([["canvas", "Canvas", Rows3], ["list", "List", LayoutList]] as const).map(([mode, label, Icon]) => (
            <button
              key={mode}
              type="button"
              aria-pressed={view === mode}
              onClick={() => onView(mode)}
              className={clsx(
                "inline-flex min-h-9 items-center gap-1.5 px-3 text-xs transition-colors focus-visible:ring-2 focus-visible:ring-accent",
                view === mode ? "bg-primary text-primary-fg" : "text-text-muted hover:text-text-main",
              )}
            >
              <Icon aria-hidden="true" className="size-3.5" />
              {label}
            </button>
          ))}
        </div>

        {/* Zoom presets */}
        <div role="group" aria-label="Timeline zoom" inert={view === "list" || undefined} className={clsx("flex flex-wrap items-center gap-1", view === "list" && "opacity-40")}>
          {ZOOMS.map(([value, label]) => (
            <button
              key={value}
              type="button"
              aria-pressed={zoom === value}
              onClick={() => onZoom(value)}
              className={clsx(
                "rounded-lg px-2.5 py-1.5 text-xs transition-colors focus-visible:ring-2 focus-visible:ring-accent",
                zoom === value ? "bg-primary text-primary-fg" : "border border-hairline text-text-muted hover:text-text-main",
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Travel */}
        <div role="group" aria-label="Move through time" inert={(view === "list" || zoom === "lifetime") || undefined} className={clsx("flex items-center gap-1", (view === "list" || zoom === "lifetime") && "opacity-40")}>
          <button type="button" onClick={() => onPan(-1)} aria-label="Earlier" className="rounded-lg border border-hairline p-2 text-text-muted hover:text-text-main focus-visible:ring-2 focus-visible:ring-accent">
            <ChevronLeft aria-hidden="true" className="size-3.5" />
          </button>
          <button type="button" onClick={onToday} className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-accent/60 px-3 text-xs font-semibold text-accent hover:bg-accent/10 focus-visible:ring-2 focus-visible:ring-accent">
            <Crosshair aria-hidden="true" className="size-3.5" />
            Today
          </button>
          <button type="button" onClick={() => onPan(1)} aria-label="Later" className="rounded-lg border border-hairline p-2 text-text-muted hover:text-text-main focus-visible:ring-2 focus-visible:ring-accent">
            <ChevronRight aria-hidden="true" className="size-3.5" />
          </button>
        </div>

        <div className="ml-auto flex items-center gap-2">
          <details
            className="group relative"
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                event.currentTarget.removeAttribute("open");
                event.currentTarget.querySelector("summary")?.focus();
              }
            }}
            onBlur={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
                event.currentTarget.removeAttribute("open");
              }
            }}
          >
            <summary className="flex min-h-9 cursor-pointer list-none items-center gap-2 rounded-lg border border-hairline px-3 text-xs text-text-muted hover:text-text-main">
              <Filter aria-hidden="true" className="size-3.5" />
              Sources
              <span className="rounded-full bg-accent/15 px-1.5 font-mono text-[10px] text-accent">{origins.size}</span>
            </summary>
            <div className="z-30 mt-2 grid gap-1 rounded-xl border border-hairline bg-card p-2 lg:absolute lg:right-0 lg:w-72">
              <p className="px-2 pb-1 text-[10px] leading-relaxed text-text-muted">
                Choose which record sources appear. Most start empty until you add or import data.
              </p>
              {(Object.entries(ORIGIN_LABELS) as Array<[TimelineOrigin, string]>).map(([origin, label]) => {
                const count = originCounts[origin] ?? 0;
                return (
                  <label key={origin} className={clsx("flex cursor-pointer items-start gap-2 rounded-lg px-2 py-2 text-xs hover:bg-accent/5", count === 0 && "opacity-70")}>
                    <input type="checkbox" checked={origins.has(origin)} onChange={() => onToggleOrigin(origin)} className="mt-0.5 size-4 accent-[var(--color-accent)]" />
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center justify-between gap-2">
                        <span className={count === 0 ? "text-text-muted" : "text-text-main"}>{label}</span>
                        <span className="shrink-0 font-mono text-[10px] text-text-muted">{count}</span>
                      </span>
                      {ORIGIN_HINTS[origin] && <span className="mt-0.5 block text-[10px] leading-snug text-text-muted">{ORIGIN_HINTS[origin]}</span>}
                    </span>
                  </label>
                );
              })}
            </div>
          </details>

          <button
            type="button"
            onClick={onAddEvent}
            className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg bg-accent px-3 text-xs font-semibold text-accent-fg hover:bg-accent-strong focus-visible:ring-2 focus-visible:ring-accent"
          >
            <Plus aria-hidden="true" className="size-4" />
            Add event
          </button>
        </div>
      </div>

      {/* Valence filter: locate the good and the bad at a glance */}
      <div role="group" aria-label="Filter by valence" className="flex flex-wrap items-center gap-1.5">
        <span className="mr-1 font-mono text-[9px] uppercase tracking-[0.14em] text-text-muted">Show</span>
        {TONES.map((tone) => (
          <button
            key={tone}
            type="button"
            aria-pressed={tones.has(tone)}
            onClick={() => onToggleTone(tone)}
            className={clsx(
              "rounded-full border px-2.5 py-1 font-mono text-[10px] transition-colors focus-visible:ring-2 focus-visible:ring-accent",
              tones.has(tone) ? TONE_CHIP_ON[tone] : "border-hairline text-text-muted line-through opacity-60 hover:opacity-100",
            )}
          >
            {TONE_LABELS[tone]}
          </button>
        ))}
      </div>
    </div>
  );
}
