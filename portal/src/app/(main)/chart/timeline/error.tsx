"use client";

export default function TimelineError({ reset }: { error: Error; reset: () => void }) {
  return <div className="rounded-2xl border border-danger/40 bg-card p-6"><h2 className="text-base font-semibold text-danger">The timeline could not be displayed</h2><p className="mt-1 text-sm text-text-muted">The chart is safe. Retry the read-only timeline request.</p><button type="button" onClick={reset} className="mt-4 min-h-10 rounded-lg bg-primary px-4 text-xs font-semibold text-primary-fg">Retry</button></div>;
}
