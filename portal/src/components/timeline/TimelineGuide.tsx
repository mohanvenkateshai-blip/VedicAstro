import { HelpCircle } from "lucide-react";

const LANES = [
  {
    name: "Life events",
    now: "Empty until you add them",
    meaning: "Things that actually happened — marriage, job change, move, health event. You record these; the chart does not invent them. Open one and press Correct to save a fixed version.",
  },
  {
    name: "Windows",
    now: "Yoga research candidates (e.g. Harsha Yoga)",
    meaning: "Engine output labelled as research — not proof an event occurred. Colour is valence (green supportive, red challenging, amber mixed); dotted borders mark research candidates.",
  },
  {
    name: "Dasha clock",
    now: "Vimshottari Mahadasha ribbon (+ Antardasha when zoomed in)",
    meaning: "The planetary period rhythm of the chart in each planet's colour. Hover for exact dates; the milestone detail links into the Dasha explorer.",
  },
] as const;

export function TimelineGuide() {
  return (
    <details className="mx-5 my-4 rounded-xl border border-accent/25 bg-accent/5 open:pb-4">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-medium text-text-main [&::-webkit-details-marker]:hidden">
        <HelpCircle aria-hidden="true" className="size-4 shrink-0 text-accent" />
        How to read this timeline
        <span className="ml-1 text-xs font-normal text-text-muted">(orientation and controls)</span>
      </summary>
      <div className="space-y-4 px-4 pt-1 text-xs leading-relaxed text-text-muted">
        <p className="text-sm text-text-main">
          Start at the top: <strong className="font-medium">Recently behind · Active now · Opening ahead</strong> is the
          five-second skim. The narrow strip below the controls is your <strong className="font-medium">whole life</strong> —
          click anywhere on it to travel there; the gold line is today. The canvas underneath is the detailed instrument:
          drag it sideways, or switch to <strong className="font-medium">List</strong> for a readable table of every record.
        </p>
        <ol className="grid gap-2 sm:grid-cols-3">
          <li className="rounded-lg border border-hairline bg-card p-3">
            <span className="font-mono text-[9px] uppercase tracking-wide text-primary">Starts filled</span>
            <p className="mt-1 text-text-main">Engine research candidates + the dasha ribbon from your birth chart.</p>
          </li>
          <li className="rounded-lg border border-hairline bg-card p-3">
            <span className="font-mono text-[9px] uppercase tracking-wide text-accent">You add</span>
            <p className="mt-1 text-text-main">Observed milestones via <strong>Add event</strong> — corrections keep full history.</p>
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
                <th className="pb-2 pr-3 font-semibold">Lane</th>
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
          <strong className="font-medium text-text-main">Locating good and bad:</strong> the <strong>Show</strong> chips filter
          by valence — turn everything else off to see only challenging windows, for example. Diamonds on the life strip use the
          same colours, so clusters of red or green are visible across the whole life at once.
        </p>
      </div>
    </details>
  );
}
