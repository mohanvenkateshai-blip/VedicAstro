import { Filter, Plus, ZoomIn } from "lucide-react";
import { clsx } from "clsx";
import type { TimelineOrigin, TimelineZoom } from "@/lib/types";

export const ORIGIN_LABELS: Record<TimelineOrigin, string> = {
  observed_event: "Observed events",
  prospective_prediction: "Sealed predictions",
  retrospective_hypothesis: "Retrospective research",
  imported_history: "Imported history",
  engine_inference: "Engine inferences",
};

const ORIGIN_HINTS: Partial<Record<TimelineOrigin, string>> = {
  observed_event: "Add with the button below",
  prospective_prediction: "Not yet available — sealing workflow pending",
  retrospective_hypothesis: "Requires observed events plus research runs",
  imported_history: "Import pipeline not yet wired",
  engine_inference: "Auto-loaded from chart yoga activations",
};

const ZOOMS: TimelineZoom[] = ["lifetime", "decade", "year", "month", "week", "day"];

export function TimelineControls({
  zoom,
  origins,
  originCounts,
  onZoom,
  onToggleOrigin,
  onAddEvent,
}: {
  zoom: TimelineZoom;
  origins: Set<TimelineOrigin>;
  originCounts: Record<TimelineOrigin, number>;
  onZoom: (zoom: TimelineZoom) => void;
  onToggleOrigin: (origin: TimelineOrigin) => void;
  onAddEvent: () => void;
}) {
  return (
    <div className="flex flex-col gap-3 border-b border-hairline p-4 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Timeline zoom">
        <ZoomIn aria-hidden="true" className="mr-1 size-4 text-text-muted" />
        {ZOOMS.map((item) => (
          <button
            key={item}
            type="button"
            aria-pressed={zoom === item}
            onClick={() => onZoom(item)}
            className={`rounded-lg px-2.5 py-1.5 text-xs capitalize transition-colors focus-visible:ring-2 focus-visible:ring-accent ${
              zoom === item ? "bg-primary text-primary-fg" : "border border-hairline text-text-muted hover:text-text-main"
            }`}
          >
            {item}
          </button>
        ))}
      </div>

      <details className="group relative">
        <summary className="flex min-h-9 cursor-pointer list-none items-center gap-2 rounded-lg border border-hairline px-3 text-xs text-text-muted hover:text-text-main">
          <Filter aria-hidden="true" className="size-3.5" />
          Filters
          <span className="rounded-full bg-accent/15 px-1.5 font-mono text-[10px] text-accent">
            {origins.size}
          </span>
        </summary>
        <div className="z-30 mt-2 grid gap-1 rounded-xl border border-hairline bg-card p-2 shadow-lg lg:absolute lg:right-0 lg:w-72">
          <p className="px-2 pb-1 text-[10px] leading-relaxed text-text-muted">
            Filter what appears on the timeline lanes. Most categories start empty until you add or import data.
          </p>
          {(Object.entries(ORIGIN_LABELS) as Array<[TimelineOrigin, string]>).map(([origin, label]) => {
            const count = originCounts[origin] ?? 0;
            const empty = count === 0;
            return (
              <label
                key={origin}
                className={clsx(
                  "flex cursor-pointer items-start gap-2 rounded-lg px-2 py-2 text-xs hover:bg-accent/5",
                  empty && "opacity-70",
                )}
              >
                <input
                  type="checkbox"
                  checked={origins.has(origin)}
                  onChange={() => onToggleOrigin(origin)}
                  className="mt-0.5 size-4 accent-[var(--color-accent)]"
                />
                <span className="min-w-0 flex-1">
                  <span className="flex items-center justify-between gap-2">
                    <span className={empty ? "text-text-muted" : "text-text-main"}>{label}</span>
                    <span className="shrink-0 font-mono text-[10px] text-text-muted">{count}</span>
                  </span>
                  {ORIGIN_HINTS[origin] && (
                    <span className="mt-0.5 block text-[10px] leading-snug text-text-muted">{ORIGIN_HINTS[origin]}</span>
                  )}
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
        Add observed milestone
      </button>
    </div>
  );
}
