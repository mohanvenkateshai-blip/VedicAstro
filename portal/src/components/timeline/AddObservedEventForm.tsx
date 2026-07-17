"use client";

import { useEffect, useState } from "react";
import { Loader2, X } from "lucide-react";
import { postCvce } from "@/lib/cvce-client";
import type { BirthInput, TimelineMilestone } from "@/lib/types";

const EVENT_FAMILIES = [
  ["employment.offer_received", "Received a formal job offer"],
  ["employment.start", "Started a new paid role"],
  ["employment.involuntary_end", "Employment ended by employer"],
  ["contract.signed", "Signed a binding contract"],
  ["travel.departure_international", "Departed for international travel"],
  ["residence.move_completed", "Completed a primary-residence move"],
  ["education.enrolment", "Enrolled in an education programme"],
  ["education.credential_completed", "Completed an education credential"],
  ["relationship.marriage_registered", "Marriage legally registered"],
  ["user.observed.unclassified", "Other life event (history only; not prediction-scored)"],
] as const;

function offsetSuffix(hours: number) {
  const minutes = Math.round(hours * 60);
  const sign = minutes < 0 ? "-" : "+";
  const absolute = Math.abs(minutes);
  return `${sign}${String(Math.floor(absolute / 60)).padStart(2, "0")}:${String(absolute % 60).padStart(2, "0")}`;
}

function localDateTime(date: FormDataEntryValue | null, end = false, tz = 0) {
  return `${String(date)}T${end ? "23:59:59" : "00:00:00"}${offsetSuffix(tz)}`;
}

function datePart(value: string | null | undefined) {
  return value ? value.slice(0, 10) : "";
}

/**
 * Records an observed milestone. When `correcting` is set the form is
 * prefilled from the existing record and saves an append-only successor
 * (`supersedes_milestone_id`); the original is preserved in history.
 */
export function AddObservedEventForm({
  birth,
  subjectId,
  correcting = null,
  onClose,
  onSaved,
}: {
  birth: BirthInput;
  subjectId: string;
  correcting?: TimelineMilestone | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [state, setState] = useState<"idle" | "saving" | "error">("idle");
  const [message, setMessage] = useState("");
  const [eventFamily, setEventFamily] = useState<(typeof EVENT_FAMILIES)[number][0]>("user.observed.unclassified");

  // Capture-phase window listener so Escape closes only this dialog even when
  // focus sits on <body> (e.g. after a backdrop click) — the detail sheet's
  // own window listener must never see it while this form is open.
  useEffect(() => {
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        onClose();
      }
    };
    window.addEventListener("keydown", escape, { capture: true });
    return () => window.removeEventListener("keydown", escape, { capture: true });
  }, [onClose]);
  // The ledger requires a correction to keep its exact canonical event id,
  // so in correction mode the family is displayed but never editable.
  const familyLabel = EVENT_FAMILIES.find(([value]) => value === correcting?.canonical_event_id)?.[1];

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    // Manual submit (not <form action>) so a failed save keeps what the
    // user typed instead of React resetting the uncontrolled fields.
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    setState("saving");
    setMessage("");
    try {
      await postCvce("timeline/events", {
        subject_id: subjectId,
        event_id: `portal-event:${crypto.randomUUID()}`,
        canonical_event_id: correcting ? correcting.canonical_event_id : String(formData.get("event_family")),
        original_label: formData.get("event_title"),
        title: formData.get("event_title"),
        description: formData.get("description") || "",
        direction: formData.get("direction"),
        magnitude: null,
        window: {
          start_at: localDateTime(formData.get("start"), false, birth.birth_tz),
          peak_at: formData.get("peak") ? localDateTime(formData.get("peak"), false, birth.birth_tz) : null,
          end_at: localDateTime(formData.get("end") || formData.get("start"), true, birth.birth_tz),
          native_resolution: formData.get("precision"),
          native_resolution_label: `User-entered ${formData.get("precision")} interval`,
          tolerance: { before_seconds: 0, after_seconds: 0, native_label: "No additional tolerance supplied" },
        },
        recorded_at: new Date().toISOString(),
        supersedes_milestone_id: correcting?.milestone_id ?? null,
      });
      onSaved();
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "Could not save this milestone.");
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/45 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-event-title"
    >
      <form onSubmit={submit} className="max-h-[90vh] w-full max-w-xl space-y-4 overflow-y-auto rounded-2xl border border-hairline bg-card p-5 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="add-event-title" className="text-lg font-semibold">{correcting ? "Correct this milestone" : "Add an observed milestone"}</h2>
            <p className="mt-1 text-xs text-text-muted">
              {correcting
                ? "Your correction is saved as a new version; the original stays in the audit history and disappears from the timeline."
                : "Record what actually happened. This remains separate from predictions and retrospective research."}
            </p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close milestone form" className="rounded-lg p-2 hover:bg-accent/10"><X className="size-4" /></button>
        </div>
        {correcting ? (
          <div className="grid gap-1 text-xs text-text-muted">
            Event family
            <p className="flex min-h-10 items-center rounded-lg border border-dashed border-hairline bg-background/50 px-3 text-sm text-text-main">
              {familyLabel ?? correcting.canonical_event_id}
            </p>
            <span className="text-[10px] leading-relaxed">A correction keeps its event family; add a separate milestone if the event was misclassified.</span>
          </div>
        ) : (
          <label className="grid gap-1 text-xs text-text-muted">Event family<select required name="event_family" value={eventFamily} onChange={(event) => setEventFamily(event.target.value as typeof eventFamily)} className="min-h-10 rounded-lg border border-hairline bg-card px-3 text-sm text-text-main">{EVENT_FAMILIES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><span className="text-[10px] leading-relaxed">Choose the closest precise event. “Other” remains useful history but is deliberately excluded from prediction scoring.</span></label>
        )}
        {!correcting && eventFamily === "relationship.marriage_registered" && <label className="flex items-start gap-2 rounded-xl border border-hairline p-3 text-xs text-text-muted"><input required name="sensitive_event_consent" type="checkbox" className="mt-0.5" /><span>I explicitly choose to record this sensitive relationship milestone in my private timeline.</span></label>}
        <label className="grid gap-1 text-xs text-text-muted">Milestone title<input autoFocus required name="event_title" defaultValue={correcting?.title ?? ""} className="min-h-10 rounded-lg border border-hairline bg-card px-3 text-sm text-text-main" placeholder="For example: Started a new role" /></label>
        <label className="grid gap-1 text-xs text-text-muted">What happened?<textarea required name="description" rows={3} defaultValue={correcting?.description ?? ""} className="rounded-lg border border-hairline bg-card px-3 py-2 text-sm text-text-main" /></label>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="grid gap-1 text-xs text-text-muted">Start<input required name="start" type="date" defaultValue={datePart(correcting?.window.start_at)} className="min-h-10 rounded-lg border border-hairline bg-card px-3 text-sm text-text-main" /></label>
          <label className="grid gap-1 text-xs text-text-muted">Peak, if known<input name="peak" type="date" defaultValue={datePart(correcting?.window.peak_at)} className="min-h-10 rounded-lg border border-hairline bg-card px-3 text-sm text-text-main" /></label>
          <label className="grid gap-1 text-xs text-text-muted">End, if known<input name="end" type="date" defaultValue={datePart(correcting?.window.end_at)} className="min-h-10 rounded-lg border border-hairline bg-card px-3 text-sm text-text-main" /></label>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="grid gap-1 text-xs text-text-muted">Date precision<select name="precision" defaultValue={correcting?.window.native_resolution ?? "day"} className="min-h-10 rounded-lg border border-hairline bg-card px-3 text-sm text-text-main"><option value="day">Day</option><option value="week">Week</option><option value="month">Month</option><option value="year">Year</option></select></label>
          <label className="grid gap-1 text-xs text-text-muted">Direction<select name="direction" defaultValue={correcting?.direction ?? "mixed"} className="min-h-10 rounded-lg border border-hairline bg-card px-3 text-sm text-text-main"><option value="favourable">Favourable</option><option value="unfavourable">Unfavourable</option><option value="mixed">Mixed</option><option value="neutral">Neither / factual</option></select></label>
        </div>
        <div className="flex items-center justify-end gap-2"><button type="button" onClick={onClose} className="min-h-10 rounded-lg border border-hairline px-4 text-xs">Cancel</button><button type="submit" disabled={state === "saving"} className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-accent px-4 text-xs font-semibold text-accent-fg">{state === "saving" && <Loader2 className="size-4 animate-spin" />}{correcting ? "Save correction" : "Save milestone"}</button></div>
        {message && <p role="alert" className="text-xs text-danger">{message}</p>}
      </form>
    </div>
  );
}
