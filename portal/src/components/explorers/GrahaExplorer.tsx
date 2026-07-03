"use client";

import { useState } from "react";
import type { ChartData } from "@/lib/types";
import { Card } from "@/components/ui/Card";
import { planetColor, elementColor } from "@/lib/astroColors";
import { RASHIS } from "@/lib/types";

const GRAHAS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"];

function houseOf(signIdx: number, lagnaIdx: number): number {
  return ((signIdx - lagnaIdx + 12) % 12) + 1;
}

export function GrahaExplorer({ chart }: { chart: ChartData }) {
  const [selected, setSelected] = useState("Moon");
  const lagnaIdx = chart.lagna.signIndex;
  const body = chart.planets.find((p) => p.planet === selected);
  const shadbala = chart.shadbala as Record<string, { total?: number }> | undefined;
  const strength = shadbala?.[selected]?.total;

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <div className="flex flex-wrap gap-2">
          {GRAHAS.map((g) => (
            <button
              key={g}
              type="button"
              onClick={() => setSelected(g)}
              className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors ${
                selected === g ? "bg-accent text-[#1a1206]" : "bg-white/5 hover:brightness-125"
              }`}
              style={selected === g ? undefined : { color: planetColor(g) }}
            >
              {g}
            </button>
          ))}
        </div>
      </Card>

      {body ? (
        <Card className="p-5 space-y-4">
          <h3 className="font-semibold text-lg" style={{ color: planetColor(body.planet) }}>{body.planet}</h3>
          <dl className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
            <div>
              <dt className="text-text-muted">Sign</dt>
              <dd className="font-semibold" style={{ color: elementColor(RASHIS.indexOf(body.rashi as (typeof RASHIS)[number])) }}>{body.rashi}</dd>
            </div>
            <div>
              <dt className="text-text-muted">House from Lagna</dt>
              <dd className="font-medium">{houseOf(body.signIndex, lagnaIdx)}</dd>
            </div>
            <div>
              <dt className="text-text-muted">Nakshatra</dt>
              <dd className="font-medium">{body.nakshatra} P{body.pada}</dd>
            </div>
            <div>
              <dt className="text-text-muted">Degree</dt>
              <dd className="font-medium">{body.degLabel ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-text-muted">Dignity</dt>
              <dd className="font-medium">{body.dignity ?? "neutral"}</dd>
            </div>
            <div>
              <dt className="text-text-muted">Motion</dt>
              <dd className="font-medium">
                {body.retro ? "Retrograde" : "Direct"}
                {body.combust ? " · Combust" : ""}
              </dd>
            </div>
            {strength != null && (
              <div>
                <dt className="text-text-muted">Shadbala (total)</dt>
                <dd className="font-medium">{strength.toFixed(1)}</dd>
              </div>
            )}
          </dl>
        </Card>
      ) : (
        <Card className="p-5 text-sm text-text-muted">Planet not found in chart.</Card>
      )}
    </div>
  );
}
