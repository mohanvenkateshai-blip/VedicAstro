/**
 * Pure view-model helpers for the Person Timeline workspace.
 *
 * Everything here is deterministic and free of DOM/React so the packing,
 * era-splitting and viewport math can be unit-tested with node:test. The
 * "now" instant is always passed in (the page uses the server-generated
 * timestamp) so SSR and client renders agree.
 */

import type {
  PersonTimeline,
  TimelineDirection,
  TimelineMilestone,
  TimelineOutcomeProjection,
  TimelineTimingPeriod,
  TimelineZoom,
} from "./types";

export type ValenceTone = "good" | "bad" | "mixed" | "neutral";

export const DIRECTION_TONE: Record<TimelineDirection, ValenceTone> = {
  favourable: "good",
  unfavourable: "bad",
  mixed: "mixed",
  neutral: "neutral",
  not_applicable: "neutral",
};

export const TONE_LABELS: Record<ValenceTone, string> = {
  good: "Supportive",
  bad: "Challenging",
  mixed: "Mixed",
  neutral: "Neutral",
};

export function toneOf(milestone: Pick<TimelineMilestone, "direction">): ValenceTone {
  return DIRECTION_TONE[milestone.direction] ?? "neutral";
}

const DAY_MS = 24 * 60 * 60 * 1000;

export function parseDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export type Viewport = { start: number; end: number };

export const ZOOM_SPAN_DAYS: Record<Exclude<TimelineZoom, "lifetime">, number> = {
  decade: 3653,
  year: 366,
  month: 31,
  week: 7,
  day: 1,
};

/** Full extent of the person's data: birth → last dated record (≥ now). */
export function fullRange(timeline: PersonTimeline, birthDatetime: string, now: number): Viewport {
  const values: number[] = [now];
  const birth = parseDate(birthDatetime);
  if (birth) values.push(birth.getTime());
  for (const item of timeline.milestones) {
    for (const raw of [item.window.start_at, item.window.end_at, item.window.peak_at]) {
      const parsed = parseDate(raw);
      if (parsed) values.push(parsed.getTime());
    }
  }
  for (const period of timeline.timingPeriods) {
    for (const raw of [period.startAt, period.endAt]) {
      const parsed = parseDate(raw);
      if (parsed) values.push(parsed.getTime());
    }
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = Math.max((max - min) * 0.01, 30 * DAY_MS);
  return { start: min - pad, end: max + pad };
}

/** Viewport for a zoom level centred on `center`, clamped inside `full`. */
export function viewportFor(zoom: TimelineZoom, center: number, full: Viewport): Viewport {
  if (zoom === "lifetime") return full;
  const half = (ZOOM_SPAN_DAYS[zoom] * DAY_MS) / 2;
  let start = center - half;
  let end = center + half;
  if (start < full.start) {
    end += full.start - start;
    start = full.start;
  }
  if (end > full.end) {
    start -= end - full.end;
    end = full.end;
  }
  return { start: Math.max(start, full.start), end: Math.min(end, full.end) };
}

export function panned(viewport: Viewport, fraction: number, full: Viewport): number {
  const span = viewport.end - viewport.start;
  const center = (viewport.start + viewport.end) / 2 + span * fraction;
  const half = span / 2;
  return Math.min(Math.max(center, full.start + half), full.end - half);
}

/** Position of an instant inside a viewport, in percent (unclamped may be <0 or >100). */
export function pct(time: number, viewport: Viewport): number {
  return ((time - viewport.start) / (viewport.end - viewport.start)) * 100;
}

export function clampPct(value: number): number {
  return Math.max(0, Math.min(100, value));
}

export function overlapsViewport(startValue: string, endValue: string, viewport: Viewport): boolean {
  const start = parseDate(startValue)?.getTime();
  const end = parseDate(endValue)?.getTime();
  if (start == null || end == null) return false;
  return start <= viewport.end && end >= viewport.start;
}

/** Whole-year age at an instant; null before birth (the dasha cycle can start earlier). */
export function ageAt(time: number, birthDatetime: string): number | null {
  const birth = parseDate(birthDatetime);
  if (!birth || time < birth.getTime()) return null;
  return Math.floor((time - birth.getTime()) / (365.25 * DAY_MS));
}

/**
 * Greedy interval row packing: earliest-start first, each interval takes the
 * lowest row whose last occupant ends before it starts. Replaces the old
 * `index % 2` layout that collided constantly once real data arrived.
 */
export function packRows<T>(
  items: T[],
  startOf: (item: T) => number,
  endOf: (item: T) => number,
  minGapMs = 0,
): Array<{ item: T; row: number }> {
  const sorted = [...items].sort((a, b) => startOf(a) - startOf(b) || endOf(a) - endOf(b));
  const rowEnds: number[] = [];
  return sorted.map((item) => {
    const start = startOf(item);
    let row = rowEnds.findIndex((end) => end + minGapMs <= start);
    if (row === -1) {
      row = rowEnds.length;
      rowEnds.push(endOf(item));
    } else {
      rowEnds[row] = endOf(item);
    }
    return { item, row };
  });
}

/**
 * Hide milestones that a later correction supersedes. Returns the visible
 * list plus, for each visible record, the chain of earlier versions so the
 * detail view can show correction history.
 */
export function collapseSuperseded(milestones: TimelineMilestone[]): {
  visible: TimelineMilestone[];
  supersededBy: Map<string, TimelineMilestone>;
  historyOf: (milestone: TimelineMilestone) => TimelineMilestone[];
} {
  const byId = new Map(milestones.map((item) => [item.milestone_id, item]));
  const supersededBy = new Map<string, TimelineMilestone>();
  for (const item of milestones) {
    if (item.supersedes_milestone_id && byId.has(item.supersedes_milestone_id)) {
      supersededBy.set(item.supersedes_milestone_id, item);
    }
  }
  const visible = milestones.filter((item) => !supersededBy.has(item.milestone_id));
  const historyOf = (milestone: TimelineMilestone) => {
    const chain: TimelineMilestone[] = [];
    let cursor = milestone.supersedes_milestone_id;
    while (cursor) {
      const prior = byId.get(cursor);
      if (!prior || chain.includes(prior)) break;
      chain.push(prior);
      cursor = prior.supersedes_milestone_id;
    }
    return chain;
  };
  return { visible, supersededBy, historyOf };
}

export type Era = "behind" | "current" | "ahead";

export function eraOf(milestone: TimelineMilestone, now: number): Era {
  const start = parseDate(milestone.window.start_at)?.getTime() ?? now;
  const end = parseDate(milestone.window.end_at)?.getTime() ?? start;
  if (end < now) return "behind";
  if (start > now) return "ahead";
  return "current";
}

export type DigestEntry = {
  milestone: TimelineMilestone;
  tone: ValenceTone;
  outcome: TimelineOutcomeProjection | null;
};

export type Digest = {
  behind: DigestEntry[];
  current: DigestEntry[];
  ahead: DigestEntry[];
  runningPeriods: TimelineTimingPeriod[];
};

/**
 * Skimmable three-era digest. "Behind" keeps the most recently ended
 * records, "ahead" the soonest-starting, "current" everything active now.
 */
export function buildDigest(
  milestones: TimelineMilestone[],
  periods: TimelineTimingPeriod[],
  outcomes: TimelineOutcomeProjection[],
  now: number,
  limit = 4,
): Digest {
  const outcomeFor = (id: string) => outcomes.find((item) => item.predictionMilestoneId === id) ?? null;
  const entry = (milestone: TimelineMilestone): DigestEntry => ({
    milestone,
    tone: toneOf(milestone),
    outcome: outcomeFor(milestone.milestone_id),
  });
  const behind = milestones
    .filter((item) => eraOf(item, now) === "behind")
    .sort((a, b) => (parseDate(b.window.end_at)?.getTime() ?? 0) - (parseDate(a.window.end_at)?.getTime() ?? 0))
    .slice(0, limit)
    .map(entry);
  const current = milestones
    .filter((item) => eraOf(item, now) === "current")
    .sort((a, b) => (parseDate(a.window.end_at)?.getTime() ?? 0) - (parseDate(b.window.end_at)?.getTime() ?? 0))
    .slice(0, limit)
    .map(entry);
  const ahead = milestones
    .filter((item) => eraOf(item, now) === "ahead")
    .sort((a, b) => (parseDate(a.window.start_at)?.getTime() ?? 0) - (parseDate(b.window.start_at)?.getTime() ?? 0))
    .slice(0, limit)
    .map(entry);
  const runningPeriods = periods.filter((period) => {
    const start = parseDate(period.startAt)?.getTime();
    const end = parseDate(period.endAt)?.getTime();
    return start != null && end != null && start <= now && end >= now;
  });
  return { behind, current, ahead, runningPeriods };
}

/** Evenly spaced axis ticks for a viewport. */
export function axisTicks(viewport: Viewport, count = 6): number[] {
  const span = viewport.end - viewport.start;
  return Array.from({ length: count }, (_, index) => viewport.start + (span * index) / (count - 1));
}

export function formatTick(time: number, viewport: Viewport): string {
  const span = viewport.end - viewport.start;
  const date = new Date(time);
  // UTC everywhere so server and client render identical tick labels.
  if (span < 370 * DAY_MS) {
    return new Intl.DateTimeFormat("en", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(date);
  }
  if (span < 15 * 365 * DAY_MS) {
    return new Intl.DateTimeFormat("en", { month: "short", year: "numeric", timeZone: "UTC" }).format(date);
  }
  return String(date.getUTCFullYear());
}

export function formatDateShort(value: string | null | undefined): string {
  const date = parseDate(value);
  if (!date) return "—";
  return new Intl.DateTimeFormat("en", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(date);
}

export function formatRange(startValue: string, endValue: string): string {
  const start = parseDate(startValue);
  const end = parseDate(endValue);
  if (!start || !end) return "—";
  const sameYear = start.getUTCFullYear() === end.getUTCFullYear();
  const startFmt = new Intl.DateTimeFormat("en", sameYear ? { day: "numeric", month: "short", timeZone: "UTC" } : { month: "short", year: "numeric", timeZone: "UTC" });
  const endFmt = new Intl.DateTimeFormat("en", { day: sameYear ? "numeric" : undefined, month: "short", year: "numeric", timeZone: "UTC" });
  return `${startFmt.format(start)} – ${endFmt.format(end)}`;
}
