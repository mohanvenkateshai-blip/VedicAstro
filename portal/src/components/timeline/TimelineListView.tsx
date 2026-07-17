"use client";

import { Fragment } from "react";
import { clsx } from "clsx";
import type { TimelineMilestone, TimelineOutcomeProjection } from "@/lib/types";
import {
  type Era,
  type ValenceTone,
  TONE_LABELS,
  ageAt,
  eraOf,
  formatRange,
  parseDate,
  toneOf,
} from "@/lib/timeline-view";

const TONE_BADGE: Record<ValenceTone, string> = {
  good: "border-success/50 text-success",
  bad: "border-danger/50 text-danger",
  mixed: "border-warning/50 text-warning",
  neutral: "border-hairline text-text-muted",
};

const ORIGIN_SHORT: Record<TimelineMilestone["origin"], string> = {
  observed_event: "Observed",
  imported_history: "Imported",
  prospective_prediction: "Sealed forecast",
  engine_inference: "Research candidate",
  retrospective_hypothesis: "Retrospective",
};

const ERA_HEADING: Record<Era, string> = {
  behind: "Past",
  current: "Active now",
  ahead: "Ahead",
};

const ERA_ORDER: Era[] = ["current", "ahead", "behind"];

/**
 * The reading view: every record in chronological order, grouped into
 * Active/Ahead/Past, with valence, kind and outcome as scannable columns.
 * This is also the screen-reader-friendly representation of the canvas.
 */
export function TimelineListView({
  milestones,
  outcomes,
  now,
  birthDatetime,
  selectedId,
  onSelect,
}: {
  milestones: TimelineMilestone[];
  outcomes: TimelineOutcomeProjection[];
  now: number;
  birthDatetime: string;
  selectedId: string | null;
  onSelect: (milestone: TimelineMilestone) => void;
}) {
  const outcomeFor = (id: string) => outcomes.find((item) => item.predictionMilestoneId === id) ?? null;
  const groups = ERA_ORDER.map((era) => ({
    era,
    items: milestones
      .filter((item) => eraOf(item, now) === era)
      .sort((a, b) => {
        const at = parseDate(a.window.start_at)?.getTime() ?? 0;
        const bt = parseDate(b.window.start_at)?.getTime() ?? 0;
        return era === "behind" ? bt - at : at - bt;
      }),
  })).filter((group) => group.items.length > 0);

  if (!groups.length) {
    return <p className="px-5 py-10 text-center text-sm text-text-muted">No records match the current filters.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[680px] border-collapse text-left">
        <thead>
          <tr className="border-b border-hairline font-mono text-[9px] uppercase tracking-[0.14em] text-text-muted">
            <th scope="col" className="px-4 py-2 font-medium sm:px-5">When</th>
            <th scope="col" className="px-3 py-2 font-medium">Age</th>
            <th scope="col" className="px-3 py-2 font-medium">Record</th>
            <th scope="col" className="px-3 py-2 font-medium">Valence</th>
            <th scope="col" className="px-3 py-2 font-medium">Kind</th>
            <th scope="col" className="px-3 py-2 font-medium">Outcome</th>
          </tr>
        </thead>
        <tbody>
          {groups.map((group) => (
            <Fragment key={group.era}>
              <tr className="border-b border-hairline bg-background/60">
                <th scope="rowgroup" colSpan={6} className="px-4 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-text-muted sm:px-5">
                  {ERA_HEADING[group.era]} · {group.items.length}
                </th>
              </tr>
              {group.items.map((item) => {
                const tone = toneOf(item);
                const outcome = outcomeFor(item.milestone_id);
                const startTime = parseDate(item.window.start_at)?.getTime();
                const age = startTime != null ? ageAt(startTime, birthDatetime) : null;
                return (
                  <tr
                    key={item.milestone_id}
                    className={clsx(
                      "cursor-pointer border-b border-hairline transition-colors hover:bg-accent/5",
                      selectedId === item.milestone_id && "bg-accent/10",
                    )}
                    onClick={() => onSelect(item)}
                  >
                    <td className="whitespace-nowrap px-4 py-2.5 font-mono text-[10px] text-text-muted sm:px-5">
                      {formatRange(item.window.start_at, item.window.end_at)}
                    </td>
                    <td className="px-3 py-2.5 font-mono text-[10px] text-text-muted">{age ?? "—"}</td>
                    <td className="max-w-64 px-3 py-2.5">
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          onSelect(item);
                        }}
                        className="block max-w-full truncate text-xs font-medium text-text-main hover:text-primary focus-visible:ring-2 focus-visible:ring-accent"
                      >
                        {item.title.replace(/\s*—\s*migrated research candidate$/i, "")}
                      </button>
                    </td>
                    <td className="px-3 py-2.5">
                      <span className={clsx("inline-flex rounded-full border px-2 py-0.5 font-mono text-[9px]", TONE_BADGE[tone])}>
                        {TONE_LABELS[tone]}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-[10px] text-text-muted">{ORIGIN_SHORT[item.origin]}</td>
                    <td className="whitespace-nowrap px-3 py-2.5 font-mono text-[10px] capitalize text-text-muted">
                      {outcome ? outcome.status.replaceAll("_", " ") : "—"}
                    </td>
                  </tr>
                );
              })}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
