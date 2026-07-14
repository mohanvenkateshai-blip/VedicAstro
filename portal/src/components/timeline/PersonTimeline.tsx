"use client";

import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { CalendarDays, CircleDot, FlaskConical, LockKeyhole } from "lucide-react";
import { postCvce } from "@/lib/cvce-client";
import type {
  BirthInput,
  PersonTimeline as PersonTimelineData,
  PersonTimelineDetailResponse,
  TimelineMilestone,
  TimelineOrigin,
  TimelineZoom,
} from "@/lib/types";
import { AddObservedEventForm } from "./AddObservedEventForm";
import { MilestoneDetailSheet } from "./MilestoneDetailSheet";
import { TimelineControls } from "./TimelineControls";
import { TimelineLanes } from "./TimelineLanes";

const ALL_ORIGINS: TimelineOrigin[] = [
  "observed_event",
  "prospective_prediction",
  "retrospective_hypothesis",
  "imported_history",
  "engine_inference",
];

function validDate(value: string | null | undefined) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function addDays(date: Date, days: number) {
  const result = new Date(date);
  result.setUTCDate(result.getUTCDate() + days);
  return result;
}

function overlapsRange(startValue: string, endValue: string, range: { start: Date; end: Date }) {
  const start = validDate(startValue)?.getTime();
  const end = validDate(endValue)?.getTime();
  if (start == null || end == null) return false;
  return start <= range.end.getTime() && end >= range.start.getTime();
}

function rangeFor(
  zoom: TimelineZoom,
  timeline: PersonTimelineData,
  birth: BirthInput,
  focus: TimelineMilestone | null,
) {
  const focusDate = validDate(focus?.window.peak_at ?? focus?.window.start_at) ?? new Date();
  if (zoom !== "lifetime") {
    const days: Record<Exclude<TimelineZoom, "lifetime">, number> = { decade: 3653, year: 366, month: 31, week: 7, day: 1 };
    return { start: addDays(focusDate, -days[zoom] / 2), end: addDays(focusDate, days[zoom] / 2) };
  }
  const values = [
    birth.birth_datetime,
    ...timeline.milestones.flatMap((item) => [item.window.start_at, item.window.end_at, item.window.peak_at]),
    ...timeline.timingPeriods.flatMap((item) => [item.startAt, item.endAt]),
  ].map(validDate).filter((item): item is Date => item !== null);
  if (!values.length) return { start: addDays(new Date(), -365 * 5), end: addDays(new Date(), 365 * 5) };
  const min = Math.min(...values.map((date) => date.getTime()));
  const max = Math.max(...values.map((date) => date.getTime()), Date.now());
  const padding = Math.max((max - min) * 0.04, 1000 * 60 * 60 * 24 * 30);
  return { start: new Date(min - padding), end: new Date(max + padding) };
}

export function PersonTimeline({
  timeline,
  birth,
  subjectId,
  birthQuery,
  initialMilestoneId,
  initialDetail,
}: {
  timeline: PersonTimelineData;
  birth: BirthInput;
  subjectId: string;
  birthQuery: string;
  initialMilestoneId?: string | null;
  initialDetail?: PersonTimelineDetailResponse | null;
}) {
  const router = useRouter();
  const [zoom, setZoom] = useState<TimelineZoom>("lifetime");
  const [origins, setOrigins] = useState<Set<TimelineOrigin>>(() => new Set(ALL_ORIGINS));
  const [selected, setSelected] = useState<TimelineMilestone | null>(() => timeline.milestones.find((item) => item.milestone_id === initialMilestoneId) ?? null);
  const [detail, setDetail] = useState<PersonTimelineDetailResponse | null>(initialDetail ?? null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [showAddEvent, setShowAddEvent] = useState(false);

  const range = useMemo(() => rangeFor(zoom, timeline, birth, selected), [zoom, timeline, birth, selected]);
  const filtered = useMemo(() => timeline.milestones.filter((item) => origins.has(item.origin) && overlapsRange(item.window.start_at, item.window.end_at, range)), [timeline.milestones, origins, range]);
  const visiblePeriods = useMemo(() => timeline.timingPeriods.filter((item) => overlapsRange(item.startAt, item.endAt, range)), [timeline.timingPeriods, range]);
  const visibleOutcomes = useMemo(() => timeline.outcomes.filter((outcome) => {
    const prediction = timeline.milestones.find((item) => item.milestone_id === outcome.predictionMilestoneId);
    const window = outcome.actualWindow ?? prediction?.window;
    return Boolean(window && overlapsRange(window.start_at, window.end_at, range));
  }), [timeline.outcomes, timeline.milestones, range]);
  const observedCount = timeline.milestones.filter((item) => item.origin === "observed_event" || item.origin === "imported_history").length;
  const sealedCount = timeline.milestones.filter((item) => item.origin === "prospective_prediction" && item.sealed_at !== null).length;
  const candidateCount = timeline.milestones.filter((item) => item.origin === "engine_inference" || item.origin === "retrospective_hypothesis").length;

  function toggleOrigin(origin: TimelineOrigin) {
    setOrigins((previous) => {
      const next = new Set(previous);
      if (next.has(origin)) next.delete(origin); else next.add(origin);
      return next;
    });
  }

  const closeDetail = useCallback(() => {
    setSelected(null);
    setDetail(null);
  }, []);

  async function selectMilestone(milestone: TimelineMilestone) {
    setSelected(milestone);
    setDetail(null);
    setDetailLoading(true);
    try {
      const response = await postCvce<PersonTimelineDetailResponse>(`timeline/milestones/${encodeURIComponent(milestone.milestone_id)}/detail`, { ...birth, subject_id: subjectId });
      setSelected(response.milestone);
      setDetail(response);
    } catch {
      // The query representation remains useful if the detail endpoint is
      // temporarily unavailable; its technical sections show empty states.
    } finally {
      setDetailLoading(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-hairline bg-card p-4"><div className="flex items-center gap-2 text-primary"><CalendarDays className="size-4" /><span className="font-mono text-[10px] uppercase tracking-wide">Observed</span></div><p className="mt-2 text-2xl font-semibold">{observedCount}</p><p className="text-xs text-text-muted">person-confirmed or imported milestones</p></div>
        <div className="rounded-xl border border-hairline bg-card p-4"><div className="flex items-center gap-2 text-accent"><LockKeyhole className="size-4" /><span className="font-mono text-[10px] uppercase tracking-wide">Sealed</span></div><p className="mt-2 text-2xl font-semibold">{sealedCount}</p><p className="text-xs text-text-muted">prospective predictions</p></div>
        <div className="rounded-xl border border-hairline bg-card p-4"><div className="flex items-center gap-2 text-warning"><FlaskConical className="size-4" /><span className="font-mono text-[10px] uppercase tracking-wide">Research</span></div><p className="mt-2 text-2xl font-semibold">{candidateCount}</p><p className="text-xs text-text-muted">inferences and retrospective hypotheses</p></div>
      </div>

      <section className="overflow-hidden rounded-2xl border border-hairline bg-card" aria-labelledby="timeline-workspace-title">
        <div className="flex flex-col gap-3 p-5 sm:flex-row sm:items-start sm:justify-between">
          <div><h2 id="timeline-workspace-title" className="text-lg font-semibold">Life events, predictions and timing</h2><p className="mt-1 max-w-3xl text-xs leading-relaxed text-text-muted">One synchronized view keeps observed history, sealed forecasts and after-the-fact research scientifically distinct. Select any record for its timing and evidence.</p></div>
          <div className="flex flex-wrap gap-3 font-mono text-[9px] text-text-muted"><span className="flex items-center gap-1"><CircleDot className="size-3 fill-primary text-primary" /> observed</span><span className="flex items-center gap-1"><CircleDot className="size-3 text-accent" /> sealed prediction</span><span className="flex items-center gap-1"><CircleDot className="size-3 text-warning" /> research candidate</span></div>
        </div>
        <TimelineControls zoom={zoom} origins={origins} onZoom={setZoom} onToggleOrigin={toggleOrigin} onAddEvent={() => setShowAddEvent(true)} />
        {timeline.milestones.length || timeline.timingPeriods.length ? (
          <TimelineLanes milestones={filtered} periods={visiblePeriods} outcomes={visibleOutcomes} range={range} selectedId={selected?.milestone_id ?? null} onSelect={selectMilestone} />
        ) : (
          <div className="grid place-items-center px-6 py-16 text-center"><CalendarDays className="size-8 text-accent" /><h3 className="mt-3 text-base font-semibold">Your person timeline starts with lived history</h3><p className="mt-1 max-w-md text-sm text-text-muted">Add a confirmed milestone. Predictions, timing activations and outcomes will remain separate as they are linked.</p><button type="button" onClick={() => setShowAddEvent(true)} className="mt-4 rounded-lg bg-accent px-4 py-2 text-xs font-semibold text-accent-fg">Add your first milestone</button></div>
        )}
      </section>

      {selected && <MilestoneDetailSheet milestone={selected} detail={detail} subjectId={subjectId} observedMilestones={timeline.milestones.filter((item) => item.origin === "observed_event" || item.origin === "imported_history")} birthQuery={birthQuery} loading={detailLoading} currentOutcome={timeline.outcomes.find((item) => item.predictionMilestoneId === selected.milestone_id)} onOutcomeSaved={() => router.refresh()} onClose={closeDetail} />}
      {showAddEvent && <AddObservedEventForm birth={birth} subjectId={subjectId} onClose={() => setShowAddEvent(false)} onSaved={() => { setShowAddEvent(false); router.refresh(); }} />}
    </div>
  );
}
