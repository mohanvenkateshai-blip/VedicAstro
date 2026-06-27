"use client";

import { useState } from "react";
import type { ChartData } from "@/lib/types";
import { Card } from "@/components/ui/Card";

const SIGN_LORDS = [
  "Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
  "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter",
];

const HOUSE_THEMES: Record<number, string> = {
  1: "Self, body, personality, vitality",
  2: "Wealth, speech, family, values",
  3: "Siblings, courage, communication, short travel",
  4: "Home, mother, property, inner peace",
  5: "Children, creativity, intelligence, romance",
  6: "Enemies, disease, service, obstacles",
  7: "Spouse, partnerships, contracts",
  8: "Longevity, transformation, occult, inheritance",
  9: "Dharma, fortune, guru, long travel",
  10: "Career, status, authority, karma",
  11: "Gains, networks, aspirations, elder siblings",
  12: "Loss, moksha, foreign lands, expenditure",
};

function houseOf(signIdx: number, lagnaIdx: number): number {
  return ((signIdx - lagnaIdx + 12) % 12) + 1;
}

export function BhavaExplorer({ chart }: { chart: ChartData }) {
  const [house, setHouse] = useState(1);
  const lagnaIdx = chart.lagna.signIndex;
  const signIdx = (lagnaIdx + house - 1) % 12;
  const signName = chart.lagna.rashi
    ? ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
       "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"][signIdx]
    : "";
  const lord = SIGN_LORDS[signIdx];
  const sav = chart.ashtakavarga?.sav?.[house - 1];

  const occupants = chart.planets.filter(
    (p) => houseOf(p.signIndex, lagnaIdx) === house,
  );

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 12 }, (_, i) => i + 1).map((h) => (
            <button
              key={h}
              type="button"
              onClick={() => setHouse(h)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                house === h
                  ? "bg-accent text-[#1a1206]"
                  : "bg-white/5 text-text-muted hover:text-text-main"
              }`}
            >
              {h}
            </button>
          ))}
        </div>
      </Card>

      <Card className="p-5 space-y-4">
        <div>
          <h3 className="font-semibold text-lg">House {house}</h3>
          <p className="text-sm text-text-muted mt-1">{HOUSE_THEMES[house]}</p>
        </div>

        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-text-muted">Sign on cusp</dt>
            <dd className="font-medium">{signName}</dd>
          </div>
          <div>
            <dt className="text-text-muted">House lord</dt>
            <dd className="font-medium">{lord}</dd>
          </div>
          {sav != null && (
            <div>
              <dt className="text-text-muted">SAV bindus</dt>
              <dd className="font-medium">{sav}</dd>
            </div>
          )}
          <div>
            <dt className="text-text-muted">Occupants</dt>
            <dd className="font-medium">
              {occupants.length
                ? occupants.map((p) => p.planet).join(", ")
                : "—"}
            </dd>
          </div>
        </dl>

        {occupants.length > 0 && (
          <div className="border-t border-hairline pt-4">
            <h4 className="text-sm font-medium mb-2">Planets in this bhava</h4>
            <ul className="space-y-2 text-sm">
              {occupants.map((p) => (
                <li key={p.planet} className="flex justify-between gap-4">
                  <span>{p.planet}</span>
                  <span className="text-text-muted">
                    {p.rashi} · {p.nakshatra} P{p.pada}
                    {p.retro ? " · R" : ""}
                    {p.dignity ? ` · ${p.dignity}` : ""}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>
    </div>
  );
}
