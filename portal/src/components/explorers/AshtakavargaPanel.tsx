"use client";

import { clsx } from "clsx";
import { Card } from "@/components/ui/Card";
import type { ChartData } from "@/lib/types";
import { RASHIS, RASHI_SHORT, PLANET_SHORT } from "@/lib/types";

const BAV_ROWS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Lagna"];

function band(bindus: number): { color: string; bg: string; label: string } {
  if (bindus >= 30) return { color: "text-success", bg: "bg-success/10", label: "Strong" };
  if (bindus >= 28) return { color: "text-teal-400", bg: "bg-teal-400/10", label: "Good" };
  if (bindus >= 22) return { color: "text-accent", bg: "bg-accent/10", label: "Neutral" };
  return { color: "text-danger", bg: "bg-danger/10", label: "Weak" };
}

export function AshtakavargaPanel({ chart }: { chart: ChartData }) {
  const akv = chart.ashtakavarga;

  if (!akv) {
    return (
      <Card className="p-6 border border-hairline">
        <p className="text-sm text-text-muted">Ashtakavarga data not available for this chart.</p>
      </Card>
    );
  }

  const total = akv.sav.reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <h3 className="text-sm font-medium mb-2">What is Ashtakavarga?</h3>
        <p className="text-xs text-text-muted leading-relaxed">
          Ashtakavarga scores each sign's strength by counting benefic bindus (points) contributed by
          the 7 planets and the Lagna, per BPHS Ch.67-72. <strong>Sarvashtakavarga (SAV)</strong> is the
          combined total per sign (always 337 across all 12); <strong>Bhinnashtakavarga (BAV)</strong> is
          each contributor's individual 12-sign board. Rashis with <strong>30+ bindus</strong> during
          their dasha or transit generally give strong positive results — this is a major prerequisite
          for interpreting Vimshottari, Kalachakra, and Gochara predictions accurately.
        </p>
        <div className="flex items-center gap-4 mt-4 text-xs">
          <span className="font-mono text-text-muted">
            Total SAV: <span className={clsx("font-semibold", total === 337 ? "text-success" : "text-danger")}>{total}</span>
            {total === 337 ? " ✓ (invariant)" : " ⚠ (expected 337)"}
          </span>
          <span className="font-mono text-text-muted">
            Lagna: <span className="text-text-fg font-semibold">{RASHIS[akv.lagnaSignIdx]}</span>
          </span>
        </div>
      </Card>

      <Card className="p-5">
        <h3 className="text-sm font-medium mb-3">Sarvashtakavarga (SAV) — combined strength per sign</h3>
        <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
          {akv.sav.map((bindus, i) => {
            const b = band(bindus);
            const isLagna = i === akv.lagnaSignIdx;
            return (
              <div
                key={i}
                className={clsx(
                  "rounded-xl border p-3 text-center",
                  b.bg,
                  isLagna ? "border-accent" : "border-hairline",
                )}
              >
                <div className="text-[10px] font-mono uppercase tracking-wider text-text-muted">
                  {RASHIS[i]}
                  {isLagna && <span className="text-accent"> · Lg</span>}
                </div>
                <div className={clsx("text-2xl font-bold mt-1", b.color)}>{bindus}</div>
                <div className={clsx("text-[10px] font-mono mt-0.5", b.color)}>{b.label}</div>
              </div>
            );
          })}
        </div>
      </Card>

      <Card className="p-5 overflow-x-auto">
        <h3 className="text-sm font-medium mb-3">Bhinnashtakavarga (BAV) — per-contributor boards</h3>
        <table className="w-full text-xs min-w-[640px]">
          <thead>
            <tr>
              <th className="text-left font-mono text-[10px] uppercase tracking-wider text-text-muted pb-2 pr-2">
                Contributor
              </th>
              {RASHI_SHORT.map((r, i) => (
                <th
                  key={i}
                  className={clsx(
                    "font-mono text-[10px] text-text-muted pb-2 px-1",
                    i === akv.lagnaSignIdx && "text-accent",
                  )}
                >
                  {r}
                </th>
              ))}
              <th className="font-mono text-[10px] text-text-muted pb-2 pl-2">Total</th>
            </tr>
          </thead>
          <tbody>
            {BAV_ROWS.map((planet) => {
              const row = akv.bav[planet];
              if (!row) return null;
              const rowTotal = row.reduce((a, b) => a + b, 0);
              return (
                <tr key={planet} className="border-t border-hairline">
                  <td className="py-1.5 pr-2 font-medium whitespace-nowrap">
                    {PLANET_SHORT[planet] ?? planet.slice(0, 2)} <span className="text-text-muted hidden sm:inline">{planet}</span>
                  </td>
                  {row.map((bindus, i) => {
                    const b = band(bindus);
                    return (
                      <td key={i} className={clsx("text-center py-1.5 px-1 font-mono", b.color)}>
                        {bindus}
                      </td>
                    );
                  })}
                  <td className="text-center py-1.5 pl-2 font-mono font-semibold">{rowTotal}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
