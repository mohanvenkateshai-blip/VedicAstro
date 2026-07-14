"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { ArrowUpRight, CalendarRange, ChevronRight, ShieldCheck, X } from "lucide-react";
import { clsx } from "clsx";
import type { PersonTimelineDetailResponse, TimelineEvidenceProjection, TimelineMilestone, TimelineOutcomeProjection } from "@/lib/types";
import { OutcomeResolutionForm } from "./OutcomeResolutionForm";

const ORIGIN_COPY: Record<TimelineMilestone["origin"], { label: string; className: string }> = {
  prospective_prediction: { label: "Sealed prospective prediction", className: "border-accent text-accent" },
  observed_event: { label: "Observed event", className: "border-primary text-primary" },
  retrospective_hypothesis: { label: "Retrospective hypothesis", className: "border-text-muted text-text-muted" },
  imported_history: { label: "Imported history", className: "border-primary text-primary" },
  engine_inference: { label: "Engine inference · migrated research candidate", className: "border-warning text-warning" },
};

function formatDate(value?: string | null) {
  if (!value) return "Not specified";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(date);
}

function displayText(value: string) {
  return value
    .replace(/\b(?:chapter|ch\.?|page|p\.)\s*\d+[\w.-]*/gi, "")
    .replace(/\s*·\s*[-\w]+-Ch\d+-p\d+/gi, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function EvidenceColumn({ title, rows, opposing = false }: { title: string; rows: TimelineEvidenceProjection[]; opposing?: boolean }) {
  return (
    <div className="space-y-2">
      <h4 className={clsx("font-mono text-[10px] uppercase tracking-[0.14em]", opposing ? "text-danger" : "text-success")}>{title} · {rows.length}</h4>
      {rows.length ? rows.map((row) => (
        <div key={`${row.role}-${row.artifactRef}-${row.statement}`} className="rounded-xl border border-hairline p-3">
          <div className="flex flex-wrap items-center justify-between gap-2"><p className="text-xs font-semibold capitalize">{row.role.replaceAll("_", " ")}</p>{row.nativeScoreRef && <span className="rounded-md bg-background px-2 py-1 font-mono text-[9px] text-text-muted">{displayText(row.nativeScoreRef.replaceAll("_", " "))}</span>}</div>
          <p className="mt-1 text-xs leading-relaxed text-text-muted">{displayText(row.statement)}</p>
        </div>
      )) : <p className="rounded-xl border border-dashed border-hairline p-3 text-xs text-text-muted">No {title.toLowerCase()} recorded.</p>}
    </div>
  );
}

export function MilestoneDetailSheet({
  milestone,
  detail,
  subjectId,
  observedMilestones,
  birthQuery,
  loading,
  currentOutcome,
  onOutcomeSaved,
  onClose,
}: {
  milestone: TimelineMilestone;
  detail: PersonTimelineDetailResponse | null;
  subjectId: string;
  observedMilestones: TimelineMilestone[];
  birthQuery: string;
  loading?: boolean;
  currentOutcome?: TimelineOutcomeProjection | null;
  onOutcomeSaved: () => void;
  onClose: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closeRef.current?.focus();
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", escape);
    return () => { window.removeEventListener("keydown", escape); previouslyFocused?.focus(); };
  }, [onClose]);
  const origin = ORIGIN_COPY[milestone.origin];
  const supporting = detail?.supportingEvidence ?? [];
  const opposing = detail?.opposingEvidence ?? [];
  const ladder = detail?.timingLadders[0]?.periods ?? [];
  const dashaUrl = new URL(detail?.dashaDeepLink ?? "/chart/dasha", "https://timeline.local");
  new URLSearchParams(birthQuery).forEach((value, key) => dashaUrl.searchParams.set(key, value));
  dashaUrl.searchParams.set("milestone", milestone.milestone_id);
  const dashaHref = `${dashaUrl.pathname}?${dashaUrl.searchParams.toString()}`;
  const narrative = detail?.humanStatement || milestone.description;

  return (
    <aside className="fixed inset-y-0 right-0 z-40 w-full overflow-y-auto border-l border-hairline bg-card shadow-2xl sm:max-w-2xl" role="dialog" aria-modal="true" aria-labelledby="milestone-title">
      <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-hairline bg-card/95 p-5 backdrop-blur">
        <div className="min-w-0">
          <span className={clsx("inline-flex rounded-full border px-2 py-1 font-mono text-[9px] font-semibold uppercase tracking-wide", origin.className)}>{origin.label}</span>
          <h2 id="milestone-title" className="mt-3 text-xl font-semibold">{displayText(milestone.title)}</h2>
          {milestone.origin === "engine_inference" && <p className="mt-1 text-xs text-warning">This broad activation candidate was migrated from research output. It is not a sealed prediction and not evidence that this event occurred.</p>}
        </div>
        <button ref={closeRef} type="button" onClick={onClose} aria-label="Close milestone details" className="shrink-0 rounded-lg border border-hairline p-2 hover:bg-accent/10"><X className="size-4" /></button>
      </div>

      <div className="space-y-7 p-5 pb-16">
        {loading && <p role="status" className="animate-pulse text-xs text-text-muted">Loading the complete evidence record…</p>}
        <section aria-labelledby="timing-heading">
          <h3 id="timing-heading" className="flex items-center gap-2 text-base font-semibold"><CalendarRange className="size-4 text-accent" />Timing window</h3>
          <dl className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {[['Start', milestone.window.start_at], ['Peak', milestone.window.peak_at], ['End', milestone.window.end_at], ['Tolerance', milestone.window.tolerance.native_label]].map(([label, value]) => (
              <div key={label} className="rounded-xl border border-hairline bg-background/50 p-3"><dt className="font-mono text-[9px] uppercase text-text-muted">{label}</dt><dd className="mt-1 text-xs font-semibold">{label === "Tolerance" ? (value || "None stated") : formatDate(value)}</dd></div>
            ))}
          </dl>
          <p className="mt-2 text-[10px] text-text-muted">Native resolution: {milestone.window.native_resolution_label}. The dates above retain the source interval rather than implying false precision.</p>
        </section>

        <section aria-labelledby="meaning-heading">
          <h3 id="meaning-heading" className="text-base font-semibold">What this record means</h3>
          <p className="mt-2 text-sm leading-7 text-text-muted">{displayText(narrative || "The engine has not supplied a human-readable explanation for this record.")}</p>
          {detail?.scientificIdentity.notice && <p className="mt-3 rounded-lg border border-hairline bg-background/50 p-3 text-xs text-text-muted">{detail.scientificIdentity.notice}</p>}
        </section>

        <section aria-labelledby="ladder-heading">
          <div className="flex flex-wrap items-center justify-between gap-2"><h3 id="ladder-heading" className="text-base font-semibold">Timing ladder</h3>{ladder.length > 0 && <Link href={dashaHref} className="inline-flex items-center gap-1 text-xs font-semibold text-accent hover:underline">Open exact period in Dasha <ArrowUpRight className="size-3" /></Link>}</div>
          {ladder.length ? <ol className="mt-3 overflow-hidden rounded-xl border border-hairline">{ladder.map((period, index) => (
            <li key={`${period.level}-${period.start_at}`} className="flex items-center gap-3 border-b border-hairline p-3 last:border-b-0" style={{ paddingLeft: `${12 + index * 14}px` }}>
              {index > 0 && <ChevronRight aria-hidden="true" className="size-3 text-text-muted" />}
              <div className="min-w-0 flex-1"><p className="text-xs font-semibold">{period.ruler} {period.level}</p><p className="font-mono text-[9px] text-text-muted">{formatDate(period.start_at)} → {formatDate(period.end_at)}</p></div>
              <span className="font-mono text-[9px] text-text-muted">{detail?.timingLadders[0]?.system}</span>
            </li>
          ))}</ol> : <p className="mt-3 rounded-xl border border-dashed border-hairline p-3 text-xs text-text-muted">No exact Dasha ladder is linked to this record.</p>}
        </section>

        <section aria-labelledby="evidence-heading">
          <h3 id="evidence-heading" className="flex items-center gap-2 text-base font-semibold"><ShieldCheck className="size-4 text-accent" />Why the engine linked this timing</h3>
          <p className="mt-1 text-xs text-text-muted">Supporting and opposing techniques are shown separately. Numeric values are native rule scores, not probabilities.</p>
          <div className="mt-3 grid gap-4 sm:grid-cols-2"><EvidenceColumn title="Supporting" rows={supporting} /><EvidenceColumn title="Opposing" rows={opposing} opposing /></div>
        </section>

        <details className="rounded-xl border border-hairline p-4">
          <summary className="cursor-pointer text-sm font-semibold">Technical calculation trace</summary>
          <p className="mt-2 text-xs text-text-muted">Audit identifiers and exact replay inputs are retained here for technical verification, away from the normal reading experience.</p>
          <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap rounded-lg bg-background p-3 font-mono text-[10px] leading-relaxed text-text-muted">{JSON.stringify(detail?.calculationTrace ?? { provenance: milestone.provenance }, null, 2)}</pre>
        </details>

        <section aria-labelledby="outcome-heading">
          <h3 id="outcome-heading" className="text-base font-semibold">Outcome and feedback</h3>
          <p className="mb-3 mt-1 text-xs text-text-muted">Feedback creates a new append-only resolution. It never rewrites this milestone or a sealed forecast.</p>
          {milestone.origin === "prospective_prediction" ? (
            <OutcomeResolutionForm milestone={milestone} subjectId={subjectId} observedMilestones={observedMilestones} currentResolutionId={currentOutcome?.resolutionId} onSaved={onOutcomeSaved} />
          ) : (
            <p className="rounded-xl border border-dashed border-hairline p-3 text-xs text-text-muted">Only a sealed prospective prediction can be scored as a hit, partial hit, miss or false alarm. This {origin.label.toLowerCase()} keeps its original scientific identity.</p>
          )}
        </section>
      </div>
    </aside>
  );
}
