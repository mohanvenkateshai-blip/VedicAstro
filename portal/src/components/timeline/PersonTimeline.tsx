"use client";

import { useCallback, useMemo, useRef, useState } from "react";
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
import {
  type ValenceTone,
  buildDigest,
  collapseSuperseded,
  fullRange,
  overlapsViewport,
  panned,
  parseDate,
  toneOf,
  viewportFor,
} from "@/lib/timeline-view";
import { AddObservedEventForm } from "./AddObservedEventForm";
import { MilestoneDetailSheet } from "./MilestoneDetailSheet";
import { TimelineCanvas } from "./TimelineCanvas";
import { TimelineControls, type TimelineViewMode } from "./TimelineControls";
import { TimelineDigest } from "./TimelineDigest";
import { TimelineGuide } from "./TimelineGuide";
import { TimelineListView } from "./TimelineListView";
import { TimelineMinimap } from "./TimelineMinimap";

const ALL_ORIGINS: TimelineOrigin[] = [
  "observed_event",
  "prospective_prediction",
  "retrospective_hypothesis",
  "imported_history",
  "engine_inference",
];

const ALL_TONES: ValenceTone[] = ["good", "bad", "mixed", "neutral"];

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
  // Server-generated instant so SSR and hydration agree on "today".
  // generatedAt is a guaranteed contract field; 0 would only appear if the
  // backend broke its contract, and degrades visibly rather than unstably.
  const now = useMemo(
    () => parseDate(timeline.generatedAt)?.getTime() ?? 0,
    [timeline.generatedAt],
  );

  const [view, setView] = useState<TimelineViewMode>("canvas");
  const [zoom, setZoom] = useState<TimelineZoom>("decade");
  const [center, setCenter] = useState<number>(now);
  const [origins, setOrigins] = useState<Set<TimelineOrigin>>(() => new Set(ALL_ORIGINS));
  const [tones, setTones] = useState<Set<ValenceTone>>(() => new Set(ALL_TONES));
  const [selected, setSelected] = useState<TimelineMilestone | null>(
    () => timeline.milestones.find((item) => item.milestone_id === initialMilestoneId) ?? null,
  );
  const [detail, setDetail] = useState<PersonTimelineDetailResponse | null>(initialDetail ?? null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [eventForm, setEventForm] = useState<{ open: boolean; correcting: TimelineMilestone | null }>({ open: false, correcting: null });

  const full = useMemo(() => fullRange(timeline, birth.birth_datetime, now), [timeline, birth.birth_datetime, now]);
  const viewport = useMemo(() => viewportFor(zoom, center, full), [zoom, center, full]);

  const { visible, historyOf } = useMemo(() => collapseSuperseded(timeline.milestones), [timeline.milestones]);

  const filtered = useMemo(
    () => visible.filter((item) => origins.has(item.origin) && tones.has(toneOf(item))),
    [visible, origins, tones],
  );
  const inViewport = useMemo(
    () => filtered.filter((item) => overlapsViewport(item.window.start_at, item.window.end_at, viewport)),
    [filtered, viewport],
  );
  const periodsInViewport = useMemo(
    () => timeline.timingPeriods.filter((item) => overlapsViewport(item.startAt, item.endAt, viewport)),
    [timeline.timingPeriods, viewport],
  );
  const digest = useMemo(
    () => buildDigest(filtered, timeline.timingPeriods, timeline.outcomes, now),
    [filtered, timeline.timingPeriods, timeline.outcomes, now],
  );
  const originCounts = useMemo(() => {
    const counts = Object.fromEntries(ALL_ORIGINS.map((origin) => [origin, 0])) as Record<TimelineOrigin, number>;
    for (const item of visible) counts[item.origin] += 1;
    return counts;
  }, [visible]);

  const observedCount = visible.filter((item) => item.origin === "observed_event" || item.origin === "imported_history").length;
  const sealedCount = visible.filter((item) => item.origin === "prospective_prediction" && item.sealed_at !== null).length;
  const candidateCount = visible.filter((item) => item.origin === "engine_inference" || item.origin === "retrospective_hypothesis").length;

  const travelTo = useCallback(
    (time: number) => {
      setCenter(time);
      if (zoom === "lifetime") setZoom("decade");
    },
    [zoom],
  );

  const detailRequestId = useRef(0);
  const selectMilestone = useCallback(
    async (milestone: TimelineMilestone) => {
      // The detail endpoint recomputes the chart (seconds); a stale response
      // for an earlier click must not overwrite the latest selection.
      const requestId = ++detailRequestId.current;
      setSelected(milestone);
      setDetail(null);
      setDetailLoading(true);
      try {
        const response = await postCvce<PersonTimelineDetailResponse>(
          `timeline/milestones/${encodeURIComponent(milestone.milestone_id)}/detail`,
          { ...birth, subject_id: subjectId },
        );
        if (requestId !== detailRequestId.current) return;
        setSelected(response.milestone);
        setDetail(response);
      } catch {
        // The list representation stays useful when the detail endpoint is
        // briefly unavailable; its technical sections show empty states.
      } finally {
        if (requestId === detailRequestId.current) setDetailLoading(false);
      }
    },
    [birth, subjectId],
  );

  /** Digest/list rows also travel the canvas to the record they name. */
  const focusMilestone = useCallback(
    (milestone: TimelineMilestone) => {
      const start = parseDate(milestone.window.start_at)?.getTime();
      const end = parseDate(milestone.window.end_at)?.getTime() ?? start;
      if (start != null && end != null && (end < viewport.start || start > viewport.end)) {
        setCenter((start + end) / 2);
      }
      void selectMilestone(milestone);
    },
    [viewport, selectMilestone],
  );

  const toggleOrigin = useCallback((origin: TimelineOrigin) => {
    setOrigins((previous) => {
      const next = new Set(previous);
      if (next.has(origin)) next.delete(origin); else next.add(origin);
      return next;
    });
  }, []);

  const toggleTone = useCallback((tone: ValenceTone) => {
    setTones((previous) => {
      const next = new Set(previous);
      if (next.has(tone)) next.delete(tone); else next.add(tone);
      return next;
    });
  }, []);

  const closeDetail = useCallback(() => {
    setSelected(null);
    setDetail(null);
  }, []);

  const hasAnyData = timeline.milestones.length > 0 || timeline.timingPeriods.length > 0;

  return (
    <div className="space-y-5">
      {/* Scientific identity counters */}
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-hairline bg-card p-4">
          <div className="flex items-center gap-2 text-primary"><CalendarDays className="size-4" /><span className="font-mono text-[10px] uppercase tracking-wide">Observed</span></div>
          <p className="mt-2 text-2xl font-semibold">{observedCount}</p>
          <p className="text-xs text-text-muted">person-confirmed or imported milestones</p>
        </div>
        <div className="rounded-xl border border-hairline bg-card p-4">
          <div className="flex items-center gap-2 text-accent"><LockKeyhole className="size-4" /><span className="font-mono text-[10px] uppercase tracking-wide">Sealed</span></div>
          <p className="mt-2 text-2xl font-semibold">{sealedCount}</p>
          <p className="text-xs text-text-muted">prospective predictions</p>
        </div>
        <div className="rounded-xl border border-hairline bg-card p-4">
          <div className="flex items-center gap-2 text-warning"><FlaskConical className="size-4" /><span className="font-mono text-[10px] uppercase tracking-wide">Research</span></div>
          <p className="mt-2 text-2xl font-semibold">{candidateCount}</p>
          <p className="text-xs text-text-muted">inferences and retrospective hypotheses</p>
        </div>
      </div>

      {/* The five-second skim: behind / now / ahead */}
      <TimelineDigest digest={digest} onSelect={focusMilestone} />

      <section className="overflow-hidden rounded-2xl border border-hairline bg-card" aria-labelledby="timeline-workspace-title">
        <div className="flex flex-col gap-3 p-5 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 id="timeline-workspace-title" className="text-lg font-semibold">Life events, predictions and timing</h2>
            <p className="mt-1 max-w-3xl text-xs leading-relaxed text-text-muted">
              Colour is valence — green supportive, red challenging, amber mixed. Border style is scientific identity:
              solid records, dotted research candidates, dashed retrospectives, a lock for sealed forecasts.
            </p>
          </div>
          <div className="flex flex-wrap gap-3 font-mono text-[9px] text-text-muted">
            <span className="flex items-center gap-1"><CircleDot className="size-3 fill-success text-success" /> supportive</span>
            <span className="flex items-center gap-1"><CircleDot className="size-3 fill-danger text-danger" /> challenging</span>
            <span className="flex items-center gap-1"><CircleDot className="size-3 fill-warning text-warning" /> mixed</span>
          </div>
        </div>

        <TimelineControls
          view={view}
          zoom={zoom}
          origins={origins}
          originCounts={originCounts}
          tones={tones}
          onView={setView}
          onZoom={setZoom}
          onPan={(direction) => setCenter(panned(viewport, direction * 0.5, full))}
          onToday={() => travelTo(now)}
          onToggleOrigin={toggleOrigin}
          onToggleTone={toggleTone}
          onAddEvent={() => setEventForm({ open: true, correcting: null })}
        />

        {hasAnyData ? (
          <>
            <TimelineMinimap
              timeline={timeline}
              milestones={filtered}
              full={full}
              viewport={viewport}
              now={now}
              birthDatetime={birth.birth_datetime}
              onCenter={travelTo}
            />
            {view === "canvas" ? (
              <TimelineCanvas
                milestones={inViewport}
                periods={periodsInViewport}
                outcomes={timeline.outcomes}
                viewport={viewport}
                now={now}
                birthDatetime={birth.birth_datetime}
                selectedId={selected?.milestone_id ?? null}
                onSelect={selectMilestone}
                onCenter={setCenter}
              />
            ) : (
              <TimelineListView
                milestones={filtered}
                outcomes={timeline.outcomes}
                now={now}
                birthDatetime={birth.birth_datetime}
                selectedId={selected?.milestone_id ?? null}
                onSelect={focusMilestone}
              />
            )}
            <TimelineGuide />
          </>
        ) : (
          <div className="grid place-items-center px-6 py-16 text-center">
            <CalendarDays className="size-8 text-accent" />
            <h3 className="mt-3 text-base font-semibold">Your person timeline starts with lived history</h3>
            <p className="mt-1 max-w-md text-sm text-text-muted">Add a confirmed milestone. Predictions, timing activations and outcomes will remain separate as they are linked.</p>
            <button type="button" onClick={() => setEventForm({ open: true, correcting: null })} className="mt-4 rounded-lg bg-accent px-4 py-2 text-xs font-semibold text-accent-fg">Add your first milestone</button>
          </div>
        )}
      </section>

      {selected && (
        <MilestoneDetailSheet
          milestone={selected}
          detail={detail}
          subjectId={subjectId}
          observedMilestones={visible.filter((item) => item.origin === "observed_event" || item.origin === "imported_history")}
          history={historyOf(selected)}
          birthQuery={birthQuery}
          loading={detailLoading}
          currentOutcome={timeline.outcomes.find((item) => item.predictionMilestoneId === selected.milestone_id)}
          onOutcomeSaved={() => router.refresh()}
          onCorrect={
            // The ledger only permits corrections that keep origin observed_event;
            // imported history will get its own flow with the import pipeline.
            selected.origin === "observed_event"
              ? () => setEventForm({ open: true, correcting: selected })
              : undefined
          }
          onClose={closeDetail}
        />
      )}
      {eventForm.open && (
        <AddObservedEventForm
          birth={birth}
          subjectId={subjectId}
          correcting={eventForm.correcting}
          onClose={() => setEventForm({ open: false, correcting: null })}
          onSaved={() => {
            setEventForm({ open: false, correcting: null });
            closeDetail();
            router.refresh();
          }}
        />
      )}
    </div>
  );
}
