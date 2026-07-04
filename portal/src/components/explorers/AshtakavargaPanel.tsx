"use client";

import * as React from "react";
import { clsx } from "clsx";
import { Card } from "@/components/ui/Card";
import type { ChartData } from "@/lib/types";
import { RASHIS, RASHI_SHORT, PLANET_SHORT } from "@/lib/types";
import { planetColor, elementColor } from "@/lib/astroColors";
import { KundaliChart } from "@/components/chart/KundaliChart";

const BAV_ROWS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Lagna"];

function band(bindus: number): { color: string; bg: string; label: string } {
  if (bindus >= 30) return { color: "text-success", bg: "bg-success/10", label: "Strong" };
  if (bindus >= 28) return { color: "text-teal-400", bg: "bg-teal-400/10", label: "Good" };
  if (bindus >= 22) return { color: "text-accent", bg: "bg-accent/10", label: "Neutral" };
  return { color: "text-danger", bg: "bg-danger/10", label: "Weak" };
}

export function AshtakavargaPanel({ chart }: { chart: ChartData }) {
  const akv = chart.ashtakavarga;
  const [showTransit, setShowTransit] = React.useState(false);
  const [superimpose, setSuperimpose] = React.useState(false);

  if (!akv) {
    return (
      <Card className="p-6 border border-hairline">
        <p className="text-sm text-text-muted">Ashtakavarga data not available for this chart.</p>
      </Card>
    );
  }

  const total = akv.sav.reduce((a, b) => a + b, 0);
  const transitSav = (akv as any).transit_sav as number[] | undefined;
  const [chartVariant, setChartVariant] = React.useState<"south" | "north">("south");

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

        {/* Classical House Group Totals (Kendra, Trikona, Dustana, Upachaya) */}
        <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-xs font-mono">
          {[
            { label: "Kendra", houses: [0,3,6,9] },
            { label: "Trikona", houses: [0,4,8] },
            { label: "Dustana", houses: [5,7,11] },
            { label: "Upachaya", houses: [2,5,9,10] },
          ].map((g) => {
            const sum = g.houses.reduce((acc, h) => acc + akv.sav[h], 0);
            return (
              <span key={g.label}>
                {g.label}: <span className="font-semibold text-accent">{sum}</span>
              </span>
            );
          })}
        </div>

        {/* Visual Kundali Chart with SAV bindus */}
        <div className="mt-4 border border-hairline rounded-xl p-3 bg-[#0a0a0a]">
          <div className="flex gap-2 mb-2">
            {(["south", "north"] as const).map((v) => (
              <button
                key={v}
                onClick={() => setChartVariant(v)}
                className={clsx("px-3 py-1 text-xs rounded border", chartVariant === v ? "bg-accent text-accent-fg border-accent" : "border-hairline")}
              >
                {v === "south" ? "South" : "North"} Indian
              </button>
            ))}
          </div>
          <KundaliChart
            signs={(() => {
              const v = chart.vargas?.D1?.signs;
              if (v && Object.keys(v).length > 0) return v;
              // Fallback: build from planets + Lagna
              const s: Record<string, number> = {};
              (chart.planets || []).forEach((p: any) => { if (p.planet && p.signIdx != null) s[p.planet] = p.signIdx; });
              if ((chart as any).lagna?.signIdx != null) s.Lagna = (chart as any).lagna.signIdx;
              return s;
            })()}
            variant={chartVariant}
            sav={akv.sav}
            size={380}
          />
        </div>
      </Card>

      <Card className="p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium">Sarvashtakavarga (SAV) — combined strength per sign</h3>
          <div className="flex gap-2 text-xs">
            {transitSav && (
              <button
                onClick={() => setShowTransit(!showTransit)}
                className={clsx("px-2 py-0.5 rounded border", showTransit ? "bg-accent text-accent-fg border-accent" : "border-hairline")}
              >
                Transit SAV
              </button>
            )}
            {transitSav && showTransit && (
              <button
                onClick={() => setSuperimpose(!superimpose)}
                className={clsx("px-2 py-0.5 rounded border", superimpose ? "bg-accent text-accent-fg border-accent" : "border-hairline")}
              >
                Superimpose
              </button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
          {akv.sav.map((bindus, i) => {
            const b = band(bindus);
            const isLagna = i === akv.lagnaSignIdx;
            const tBindus = transitSav?.[i];
            const tBand = tBindus != null ? band(tBindus) : null;
            return (
              <div
                key={i}
                className={clsx(
                  "rounded-xl border p-3 text-center relative",
                  b.bg,
                  isLagna ? "border-accent" : "border-hairline",
                )}
              >
                <div className="text-[10px] font-mono uppercase tracking-wider font-semibold" style={{ color: elementColor(i) }}>
                  {RASHIS[i]}
                  {isLagna && <span className="text-accent"> · Lg</span>}
                </div>
                <div className={clsx("text-2xl font-bold mt-1", b.color)}>{bindus}</div>
                <div className={clsx("text-[10px] font-mono mt-0.5", b.color)}>{b.label}</div>

                {showTransit && tBindus != null && (
                  <div className={clsx("mt-1 text-[10px] font-mono", tBand?.color)}>
                    T: {tBindus} {tBand?.label}
                  </div>
                )}
                {superimpose && tBindus != null && (
                  <div className="absolute -top-1 -right-1 text-[9px] px-1 rounded bg-black/70 text-white">
                    Δ{tBindus - bindus}
                  </div>
                )}
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
                  className="font-mono text-[10px] font-semibold pb-2 px-1"
                  style={{ color: i === akv.lagnaSignIdx ? "var(--color-accent)" : elementColor(i) }}
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
                  <td className="py-1.5 pr-2 font-semibold whitespace-nowrap" style={{ color: planet === "Lagna" ? "var(--color-accent)" : planetColor(planet) }}>
                    {PLANET_SHORT[planet] ?? planet.slice(0, 2)} <span className="opacity-70 hidden sm:inline">{planet}</span>
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

      {showTransit && transitSav && (
        <Card className="p-5">
          <h3 className="text-sm font-medium mb-3">Transit Ashtakavarga — Predictions (with / without superimpose)</h3>
          <div className="grid gap-3 md:grid-cols-2">
            {transitSav.map((b, i) => {
              const bb = band(b);
              const delta = b - akv.sav[i];
              return (
                <div key={i} className="rounded-lg border border-hairline p-3 text-xs">
                  <div className="font-mono flex justify-between">
                    <span>{RASHIS[i]}</span>
                    <span className={bb.color}>{b} bindus</span>
                  </div>
                  <div className="mt-1 text-[10px] text-text-muted">
                    {delta >= 0 ? "Strengthened" : "Weakened"} by {Math.abs(delta)} vs natal
                  </div>
                  <div className={clsx("mt-1 text-[10px]", bb.color)}>{bb.label} transit influence</div>
                </div>
              );
            })}
          </div>
          <p className="mt-3 text-[10px] text-text-muted">
            Superimpose mode shows combined natal + transit bindu activation. High bindus in a sign during transit = favorable window for that house's matters.
          </p>
        </Card>
      )}
    </div>
  );
}
