import { Filter, Plus, ZoomIn } from "lucide-react";
import type { TimelineOrigin, TimelineZoom } from "@/lib/types";

export const ORIGIN_LABELS: Record<TimelineOrigin, string> = {
  observed_event: "Observed events",
  prospective_prediction: "Sealed predictions",
  retrospective_hypothesis: "Retrospective research",
  imported_history: "Imported history",
  engine_inference: "Engine inferences",
};

const ZOOMS: TimelineZoom[] = ["lifetime", "decade", "year", "month", "week", "day"];

export function TimelineControls({
  zoom,
  origins,
  onZoom,
  onToggleOrigin,
  onAddEvent,
}: {
  zoom: TimelineZoom;
  origins: Set<TimelineOrigin>;
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
        <div className="z-30 mt-2 grid gap-1 rounded-xl border border-hairline bg-card p-2 shadow-lg lg:absolute lg:right-0 lg:w-64">
          {(Object.entries(ORIGIN_LABELS) as Array<[TimelineOrigin, string]>).map(([origin, label]) => (
            <label key={origin} className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-2 text-xs hover:bg-accent/5">
              <input
                type="checkbox"
                checked={origins.has(origin)}
                onChange={() => onToggleOrigin(origin)}
                className="size-4 accent-[var(--color-accent)]"
              />
              {label}
            </label>
          ))}
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
