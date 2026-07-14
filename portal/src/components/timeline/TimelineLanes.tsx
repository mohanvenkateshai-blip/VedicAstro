import { clsx } from "clsx";
import type {
  TimelineMilestone,
  TimelineOutcomeProjection,
  TimelineTimingPeriod,
} from "@/lib/types";

type Range = { start: Date; end: Date };

const ORIGIN_STYLE: Record<TimelineMilestone["origin"], string> = {
  observed_event: "border-primary bg-primary text-primary-fg",
  prospective_prediction: "border-accent bg-card text-accent",
  retrospective_hypothesis: "border-dashed border-text-muted bg-card text-text-muted",
  imported_history: "border-primary/60 bg-primary/10 text-primary",
  engine_inference: "border-dotted border-warning bg-card text-warning",
};

const OUTCOME_STYLE: Record<TimelineOutcomeProjection["status"], string> = {
  hit: "border-success/40 bg-success/10 text-success",
  partial_hit: "border-warning/50 bg-warning/10 text-warning",
  miss: "border-danger/50 bg-danger/10 text-danger",
  false_alarm: "border-danger/50 bg-danger/10 text-danger",
  ambiguous: "border-text-muted/40 bg-background text-text-muted",
  unresolved: "border-primary/40 bg-primary/10 text-primary",
};

function at(value: string | null | undefined, range: Range): number {
  if (!value) return 0;
  const time = new Date(value).getTime();
  const span = range.end.getTime() - range.start.getTime();
  return Math.max(0, Math.min(100, ((time - range.start.getTime()) / span) * 100));
}

function width(start: string, end: string, range: Range, minimum = 0.8): number {
  return Math.max(minimum, at(end, range) - at(start, range));
}

function dateLabel(value: Date, includeDay: boolean) {
  return new Intl.DateTimeFormat("en", includeDay
    ? { day: "numeric", month: "short", year: "numeric" }
    : { month: "short", year: "numeric" }).format(value);
}

function Axis({ range }: { range: Range }) {
  const ticks = Array.from({ length: 6 }, (_, index) => {
    const time = range.start.getTime() + ((range.end.getTime() - range.start.getTime()) * index) / 5;
    return new Date(time);
  });
  const includeDay = range.end.getTime() - range.start.getTime() < 1000 * 60 * 60 * 24 * 370;
  return (
    <div className="relative ml-32 h-8 border-b border-hairline sm:ml-40">
      {ticks.map((tick, index) => (
        <span
          key={tick.toISOString()}
          className="absolute bottom-1 -translate-x-1/2 whitespace-nowrap font-mono text-[9px] text-text-muted first:translate-x-0 last:-translate-x-full"
          style={{ left: `${index * 20}%` }}
        >
          {dateLabel(tick, includeDay)}
        </span>
      ))}
    </div>
  );
}

function Lane({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex min-h-20 border-b border-hairline last:border-b-0">
      <div className="flex w-32 shrink-0 items-center border-r border-hairline bg-background/50 px-3 sm:w-40">
        <span className="text-xs font-semibold text-text-muted">{label}</span>
      </div>
      <div className="relative min-w-[760px] flex-1 overflow-hidden bg-[linear-gradient(to_right,var(--color-hairline)_1px,transparent_1px)] bg-[size:20%_100%]">
        {children}
      </div>
    </div>
  );
}

export function TimelineLanes({
  milestones,
  periods,
  outcomes,
  range,
  selectedId,
  onSelect,
}: {
  milestones: TimelineMilestone[];
  periods: TimelineTimingPeriod[];
  outcomes: TimelineOutcomeProjection[];
  range: Range;
  selectedId: string | null;
  onSelect: (milestone: TimelineMilestone) => void;
}) {
  const observed = milestones.filter((item) => ["observed_event", "imported_history"].includes(item.origin));
  const predictions = milestones.filter((item) => !["observed_event", "imported_history"].includes(item.origin));
  const activations = milestones.filter((item) => item.origin === "engine_inference");

  const marker = (item: TimelineMilestone, row: number) => {
    const start = item.window.start_at;
    const end = item.window.end_at || start;
    const peak = item.window.peak_at || start;
    const left = at(start, range);
    const bandWidth = width(start, end, range, 1.4);
    return (
      <button
        key={item.milestone_id}
        type="button"
        aria-label={`${item.title}, ${item.origin.replaceAll("_", " ")}, ${start} to ${end}`}
        aria-pressed={selectedId === item.milestone_id}
        onClick={() => onSelect(item)}
        className={clsx(
          "absolute h-8 overflow-visible rounded-lg border-2 px-2 text-left text-[10px] font-semibold transition-transform hover:z-20 hover:scale-[1.03] focus-visible:z-20 focus-visible:ring-2 focus-visible:ring-accent",
          ORIGIN_STYLE[item.origin],
          selectedId === item.milestone_id && "z-20 ring-2 ring-accent ring-offset-2 ring-offset-card",
        )}
        style={{ left: `${left}%`, width: `${bandWidth}%`, minWidth: 24, top: `${10 + (row % 2) * 34}px` }}
        title={item.title}
      >
        {item.window.peak_at && (
          <span
            aria-hidden="true"
            className="absolute inset-y-0 w-px bg-current opacity-70"
            style={{ left: `${Math.max(0, Math.min(100, ((at(peak, range) - left) / bandWidth) * 100))}%` }}
          />
        )}
        <span className="block truncate">{item.title}</span>
      </button>
    );
  };

  return (
    <div className="overflow-x-auto" aria-label="Synchronized person timeline lanes">
      <div className="min-w-[920px]">
        <Axis range={range} />
        <Lane label="Observed events">
          {observed.map(marker)}
          {observed.length === 0 && <p className="p-5 text-xs text-text-muted">No observed milestones yet.</p>}
        </Lane>
        <Lane label="Predictions & research">
          {predictions.map(marker)}
          {predictions.length === 0 && <p className="p-5 text-xs text-text-muted">No prediction or research records in this range.</p>}
        </Lane>
        <Lane label="Timing periods">
          {periods.map((period, index) => (
            <div
              key={`${period.system}-${period.level}-${period.startAt}-${index}`}
              className={clsx(
                "absolute h-7 overflow-hidden rounded-md border border-primary/30 bg-primary/10 px-2 py-1 font-mono text-[9px] text-primary",
              )}
              style={{ left: `${at(period.startAt, range)}%`, width: `${width(period.startAt, period.endAt, range)}%`, top: `${9 + (index % 2) * 33}px`, minWidth: 28 }}
              title={`${period.system} · ${period.level} ${period.ruler}: ${period.startAt} – ${period.endAt}`}
            >
              <span className="whitespace-nowrap">{period.ruler} · {period.level}</span>
            </div>
          ))}
        </Lane>
        <Lane label="Activation windows">
          {activations.map((activation, index) => (
            <div
              key={`activation-${activation.milestone_id}`}
              className="absolute h-7 rounded-md border border-accent/40 bg-accent/10 px-2 py-1 text-[9px] text-accent"
              style={{ left: `${at(activation.window.start_at, range)}%`, width: `${width(activation.window.start_at, activation.window.end_at, range)}%`, top: `${10 + (index % 2) * 33}px`, minWidth: 20 }}
              title={`${activation.title}: ${activation.window.start_at} – ${activation.window.end_at}`}
            >
              <span className="block truncate">{activation.original_label}</span>
            </div>
          ))}
          {activations.length === 0 && <p className="p-5 text-xs text-text-muted">No linked activation windows in this range.</p>}
        </Lane>
        <Lane label="Outcomes">
          {outcomes.map((outcome, index) => {
            const prediction = milestones.find((item) => item.milestone_id === outcome.predictionMilestoneId);
            const window = outcome.actualWindow ?? prediction?.window;
            if (!window) return null;
            return (
              <button
                key={outcome.resolutionId}
                type="button"
                onClick={() => prediction && onSelect(prediction)}
                disabled={!prediction}
                className={clsx("absolute h-7 rounded-md border px-2 py-1 text-left text-[9px] font-semibold capitalize focus-visible:ring-2 focus-visible:ring-accent disabled:cursor-default", OUTCOME_STYLE[outcome.status])}
                style={{ left: `${at(window.start_at, range)}%`, width: `${width(window.start_at, window.end_at, range)}%`, top: `${10 + (index % 2) * 33}px`, minWidth: 36 }}
                aria-label={`${outcome.status.replaceAll("_", " ")} outcome, resolved ${outcome.resolvedAt}`}
              >
                {outcome.status.replaceAll("_", " ")}
              </button>
            );
          })}
          {outcomes.length === 0 && <p className="p-5 text-xs text-text-muted">No sealed prediction has been resolved yet.</p>}
        </Lane>
      </div>
    </div>
  );
}
