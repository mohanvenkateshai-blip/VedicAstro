"use client";

import { clsx } from "clsx";
import { CalendarClock, History, Radio } from "lucide-react";
import type { TimelineMilestone } from "@/lib/types";
import { planetColor } from "@/lib/astroColors";
import {
  type Digest,
  type DigestEntry,
  type ValenceTone,
  TONE_LABELS,
  formatRange,
} from "@/lib/timeline-view";

const TONE_DOT: Record<ValenceTone, string> = {
  good: "bg-success",
  bad: "bg-danger",
  mixed: "bg-warning",
  neutral: "bg-text-muted",
};

const OUTCOME_BADGE: Record<string, string> = {
  hit: "text-success border-success/40",
  partial_hit: "text-warning border-warning/40",
  miss: "text-danger border-danger/40",
  false_alarm: "text-danger border-danger/40",
  ambiguous: "text-text-muted border-hairline",
  unresolved: "text-primary border-primary/40",
};

function EntryRow({ entry, onSelect }: { entry: DigestEntry; onSelect: (milestone: TimelineMilestone) => void }) {
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(entry.milestone)}
        className="group flex w-full items-start gap-2.5 rounded-lg px-2 py-1.5 text-left hover:bg-background/70 focus-visible:ring-2 focus-visible:ring-accent"
      >
        <span aria-hidden="true" className={clsx("mt-1.5 size-2 shrink-0 rounded-full", TONE_DOT[entry.tone])} />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-xs font-medium text-text-main group-hover:text-primary">
            {entry.milestone.title.replace(/\s*—\s*migrated research candidate$/i, "")}
          </span>
          <span className="mt-0.5 flex items-center gap-2 font-mono text-[9px] text-text-muted">
            {formatRange(entry.milestone.window.start_at, entry.milestone.window.end_at)}
            <span className="sr-only">{TONE_LABELS[entry.tone]}</span>
            {entry.outcome && (
              <span className={clsx("rounded-full border px-1.5 py-px capitalize", OUTCOME_BADGE[entry.outcome.status])}>
                {entry.outcome.status.replaceAll("_", " ")}
              </span>
            )}
          </span>
        </span>
      </button>
    </li>
  );
}

function EraColumn({
  title,
  icon,
  entries,
  emptyCopy,
  onSelect,
  highlight = false,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  entries: DigestEntry[];
  emptyCopy: string;
  onSelect: (milestone: TimelineMilestone) => void;
  highlight?: boolean;
  children?: React.ReactNode;
}) {
  return (
    <section
      aria-label={title}
      className={clsx(
        "rounded-xl border p-3",
        highlight ? "border-accent/50 bg-accent/[0.04]" : "border-hairline bg-card",
      )}
    >
      <h3 className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">
        {icon}
        {title}
      </h3>
      {children}
      {entries.length ? (
        <ul className="mt-2 space-y-0.5">
          {entries.map((entry) => (
            <EntryRow key={entry.milestone.milestone_id} entry={entry} onSelect={onSelect} />
          ))}
        </ul>
      ) : (
        <p className="mt-2 px-2 text-xs leading-relaxed text-text-muted">{emptyCopy}</p>
      )}
    </section>
  );
}

/**
 * The five-second skim: what recently closed, what is running right now
 * (including the current dasha rulers), and what opens next.
 */
export function TimelineDigest({
  digest,
  onSelect,
}: {
  digest: Digest;
  onSelect: (milestone: TimelineMilestone) => void;
}) {
  const running = [...digest.runningPeriods].sort((a, b) => (a.level === "Mahadasha" ? -1 : 1) - (b.level === "Mahadasha" ? -1 : 1));
  return (
    <div className="grid gap-3 lg:grid-cols-3">
      <h2 className="sr-only">Timeline digest: recently behind, active now, opening ahead</h2>
      <EraColumn
        title="Recently behind"
        icon={<History aria-hidden="true" className="size-3.5" />}
        entries={digest.behind}
        emptyCopy="Nothing has closed recently in the visible record."
        onSelect={onSelect}
      />
      <EraColumn
        title="Active now"
        icon={<Radio aria-hidden="true" className="size-3.5 text-accent" />}
        entries={digest.current}
        emptyCopy="No window is active at this exact moment."
        onSelect={onSelect}
        highlight
      >
        {running.length > 0 && (
          <p className="mt-2 flex flex-wrap items-center gap-1.5 px-2">
            {running.map((period) => (
              <span
                key={`${period.level}-${period.ruler}-${period.startAt}`}
                className="inline-flex items-center gap-1.5 rounded-full border border-hairline bg-card px-2 py-0.5 font-mono text-[9px] text-text-main"
              >
                <span aria-hidden="true" className="size-1.5 rounded-full" style={{ backgroundColor: planetColor(period.ruler) }} />
                {period.ruler} {period.level === "Mahadasha" ? "MD" : "AD"}
              </span>
            ))}
          </p>
        )}
      </EraColumn>
      <EraColumn
        title="Opening ahead"
        icon={<CalendarClock aria-hidden="true" className="size-3.5" />}
        entries={digest.ahead}
        emptyCopy="No upcoming window in the current record."
        onSelect={onSelect}
      />
    </div>
  );
}
