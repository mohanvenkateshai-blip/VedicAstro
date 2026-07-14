"use client";

import { useState } from "react";
import { CheckCircle2, Loader2 } from "lucide-react";
import { postCvce } from "@/lib/cvce-client";
import type { TimelineMilestone, TimelineOutcomeStatus } from "@/lib/types";

const STATUSES: Array<{ value: TimelineOutcomeStatus; label: string }> = [
  { value: "hit", label: "Occurred as described" },
  { value: "partial_hit", label: "Partly occurred" },
  { value: "miss", label: "Did not occur" },
  { value: "false_alarm", label: "False alarm" },
  { value: "ambiguous", label: "Unclear" },
  { value: "unresolved", label: "Still unresolved" },
];

export function OutcomeResolutionForm({ milestone, subjectId, observedMilestones, currentResolutionId, onSaved }: { milestone: TimelineMilestone; subjectId: string; observedMilestones: TimelineMilestone[]; currentResolutionId?: string | null; onSaved: () => void }) {
  const [state, setState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [message, setMessage] = useState("");

  async function submit(formData: FormData) {
    setState("saving");
    setMessage("");
    try {
      const status = String(formData.get("status")) as TimelineOutcomeStatus;
      const observedMilestoneId = String(formData.get("observed_milestone_id") || "");
      const observed = observedMilestones.find((item) => item.milestone_id === observedMilestoneId);
      if ((status === "hit" || status === "partial_hit") && !observedMilestoneId) {
        setState("error");
        setMessage("Link the observed milestone that confirms a hit or partial hit.");
        return;
      }
      if ((status === "hit" || status === "partial_hit") && !observed) {
        setState("error");
        setMessage("The linked observed milestone is no longer available. Refresh and try again.");
        return;
      }
      const isMatched = status === "hit" || status === "partial_hit";
      await postCvce(`timeline/milestones/${encodeURIComponent(milestone.milestone_id)}/resolutions`, {
        subject_id: subjectId,
        resolution_id: `resolution:${crypto.randomUUID()}`,
        observed_milestone_id: isMatched ? observedMilestoneId : null,
        status,
        actual_window: isMatched ? observed?.window : null,
        certainty: String(formData.get("date_certainty")),
        resolver_id: "portal-person",
        resolved_at: new Date().toISOString(),
        notes: formData.get("notes") ? [String(formData.get("notes"))] : [],
        supersedes_resolution_id: currentResolutionId ?? null,
        // Matching rules are immutable properties of the sealed prediction.
        // The engine retrieves them from the ledger; outcome knowledge must
        // never be allowed to tailor event IDs or overlap thresholds.
        match_criteria: null,
      });
      setState("saved");
      setMessage(currentResolutionId ? "Correction saved. The earlier resolution remains in the audit history." : "Outcome saved as a new resolution. The original record has not been changed.");
      onSaved();
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "Could not save the outcome.");
    }
  }

  return (
    <form action={submit} className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="grid gap-1 text-xs text-text-muted">
          Outcome
          <select name="status" className="min-h-10 rounded-lg border border-hairline bg-card px-3 text-sm text-text-main" defaultValue="unresolved">
            {STATUSES.map((status) => <option key={status.value} value={status.value}>{status.label}</option>)}
          </select>
        </label>
        <label className="grid gap-1 text-xs text-text-muted sm:col-span-2">
          Linked observed milestone
          <select name="observed_milestone_id" className="min-h-10 rounded-lg border border-hairline bg-card px-3 text-sm text-text-main" defaultValue="">
            <option value="">None / not applicable</option>
            {observedMilestones.map((item) => <option key={item.milestone_id} value={item.milestone_id}>{item.title}</option>)}
          </select>
        </label>
        <label className="grid gap-1 text-xs text-text-muted">
          Date certainty
          <select name="date_certainty" className="min-h-10 rounded-lg border border-hairline bg-card px-3 text-sm text-text-main" defaultValue="exact">
            <option value="exact">Exact</option>
            <option value="approximate">Approximate</option>
            <option value="month_only">Month only</option>
            <option value="year_only">Year only</option>
          </select>
        </label>
      </div>
      <label className="grid gap-1 text-xs text-text-muted">What happened?<textarea name="notes" rows={3} className="rounded-lg border border-hairline bg-card px-3 py-2 text-sm text-text-main" placeholder="Include partial manifestations or context that will help evaluate this window." /></label>
      <button type="submit" disabled={state === "saving"} className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-primary px-4 text-xs font-semibold text-primary-fg disabled:opacity-50">
        {state === "saving" ? <Loader2 className="size-4 animate-spin" /> : <CheckCircle2 className="size-4" />}
        {currentResolutionId ? "Save correction" : "Save outcome"}
      </button>
      {message && <p role="status" className={`text-xs ${state === "error" ? "text-danger" : "text-success"}`}>{message}</p>}
    </form>
  );
}
