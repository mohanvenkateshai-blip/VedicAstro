import { HelpCircle } from "lucide-react";

const LANES = [
  {
    name: "Observed events",
    now: "Empty until you add them",
    meaning: "Things that actually happened — marriage, job change, move, health event. You record these; the chart does not invent them.",
  },
  {
    name: "Predictions & research",
    now: "Yoga research candidates (e.g. Harsha Yoga)",
    meaning: "Engine output labelled as research — not proof an event occurred. Click a band to see dasha evidence and classical citations.",
  },
  {
    name: "Timing periods",
    now: "Dasha ladder (MD / AD / PD …)",
    meaning: "Standard Vimshottari (and related) periods for this chart. Always shown; use Lifetime zoom to see the full span.",
  },
  {
    name: "Activation windows",
    now: "Same yoga windows, timing-focused view",
    meaning: "When a yoga’s ruling planet is active in dasha. Helpful for “when might this theme be louder?” — still not a sealed forecast.",
  },
  {
    name: "Outcomes",
    now: "Empty until predictions are sealed and scored",
    meaning: "Hit / miss / partial results after a sealed prediction window closes. Not available yet for most charts.",
  },
] as const;

export function TimelineGuide() {
  return (
    <details className="mx-5 mb-4 rounded-xl border border-accent/25 bg-accent/5 open:pb-4">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-medium text-text-main [&::-webkit-details-marker]:hidden">
        <HelpCircle aria-hidden="true" className="size-4 shrink-0 text-accent" />
        How to read this timeline
        <span className="ml-1 text-xs font-normal text-text-muted">(what to expect on first open)</span>
      </summary>
      <div className="space-y-4 px-4 pt-1 text-xs leading-relaxed text-text-muted">
        <p className="text-sm text-text-main">
          Think of it as <strong className="font-medium">three layers</strong>: (1) what you know happened, (2) what the engine
          suggests as timing research, (3) whether sealed forecasts later matched reality. On a new chart, only layer 2 auto-loads.
        </p>
        <ol className="grid gap-2 sm:grid-cols-3">
          <li className="rounded-lg border border-hairline bg-card p-3">
            <span className="font-mono text-[9px] uppercase tracking-wide text-primary">Starts filled</span>
            <p className="mt-1 text-text-main">Engine inferences + dasha periods from your birth chart.</p>
          </li>
          <li className="rounded-lg border border-hairline bg-card p-3">
            <span className="font-mono text-[9px] uppercase tracking-wide text-accent">You add</span>
            <p className="mt-1 text-text-main">Observed milestones via <strong>Add observed milestone</strong>.</p>
          </li>
          <li className="rounded-lg border border-dashed border-hairline bg-card p-3">
            <span className="font-mono text-[9px] uppercase tracking-wide text-text-muted">Coming later</span>
            <p className="mt-1 text-text-main">Sealing forecasts, importing history, scoring outcomes.</p>
          </li>
        </ol>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-left">
            <thead>
              <tr className="border-b border-hairline font-mono text-[9px] uppercase tracking-wide text-text-muted">
                <th className="pb-2 pr-3 font-semibold">Row</th>
                <th className="pb-2 pr-3 font-semibold">On your chart now</th>
                <th className="pb-2 font-semibold">What it means</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {LANES.map((lane) => (
                <tr key={lane.name}>
                  <td className="py-2 pr-3 align-top font-medium text-text-main">{lane.name}</td>
                  <td className="py-2 pr-3 align-top">{lane.now}</td>
                  <td className="py-2 align-top">{lane.meaning}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p>
          <strong className="font-medium text-text-main">Tip:</strong> use <strong>Lifetime</strong> zoom first — Day/Week views
          squash multi-year dasha bars into a sliver. Click any yellow yoga band to open evidence and a link to Dasha.
        </p>
      </div>
    </details>
  );
}
