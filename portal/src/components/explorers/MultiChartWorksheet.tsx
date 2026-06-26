"use client";

import { useState } from "react";
import { Grid3X3 } from "lucide-react";
import { KundaliChart } from "@/components/chart/KundaliChart";
import type { ChartData } from "@/lib/types";

const VARGAS = [
  { key: "D1", variant: "south" as const },
  { key: "D9", variant: "south" as const },
  { key: "D10", variant: "north" as const },
  { key: "D12", variant: "north" as const },
];

const VARGA_NAMES: Record<string, string> = {
  D1: "Rāśi",
  D9: "Navāṁśa",
  D10: "Daśāṁśa",
  D12: "Dvādaśāṁśa",
};

export function MultiChartWorksheet({ chart }: { chart: ChartData }) {
  const [selected, setSelected] = useState<string[]>(["D1", "D9", "D10", "D12"]);
  const maxCharts = 4;

  const toggleVarga = (key: string) => {
    setSelected((prev) => {
      if (prev.includes(key)) {
        if (prev.length <= 1) return prev;
        return prev.filter((k) => k !== key);
      }
      if (prev.length >= maxCharts) {
        return [...prev.slice(1), key];
      }
      return [...prev, key];
    });
  };

  const vargas = VARGAS.filter((v) => selected.includes(v.key));
  const availableKeys = VARGAS.map((v) => v.key);

  return (
    <div>
      <div className="flex flex-wrap items-center gap-1.5 mb-6">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent/10 text-accent mr-1">
          <Grid3X3 className="h-4 w-4" />
        </span>
        {availableKeys.map((key) => {
          const v = VARGAS.find((v) => v.key === key)!;
          const active = selected.includes(key);
          return (
            <button
              key={key}
              onClick={() => toggleVarga(key)}
              aria-pressed={active}
              className={`px-3 py-2 min-h-[44px] rounded-md text-xs font-mono border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 ${
                active
                  ? "border-accent bg-accent/10 text-accent"
                  : "border-hairline text-text-muted hover:text-text-main"
              }`}
            >
              {key}
            </button>
          );
        })}
        <span className="text-[11px] text-text-muted ml-2">
          {selected.length}/{maxCharts} charts
        </span>
      </div>

      {vargas.length === 0 && (
        <div className="flex flex-col items-center gap-3 py-16 text-text-muted text-sm">
          <Grid3X3 className="h-8 w-8 text-accent/30" />
          <p>Select at least one varga chart to display.</p>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {vargas.map(({ key, variant }) => {
          const varga = chart.vargas?.[key];
          const signs = varga?.signs ?? chart.natalSign ?? {};
          const name = VARGA_NAMES[key] ?? varga?.name ?? key;

          return (
            <div
              key={key}
              className="rounded-2xl border border-hairline bg-card p-5 flex flex-col items-center"
            >
              <div className="flex items-center justify-between w-full mb-3">
                <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">
                  {key}
                </span>
                <span className="text-xs text-text-muted">
                  {variant === "south" ? "South" : "North"} Indian
                </span>
              </div>

              <h3 className="font-display text-base font-semibold text-text-main mb-4">
                {name}
              </h3>

              <div className="flex justify-center">
                <KundaliChart
                  signs={signs}
                  variant={variant}
                  size={260}
                />
              </div>

              <p className="mt-3 text-[11px] text-text-muted">
                Lagna in {varga?.signs?.Lagna != null ? ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"][varga.signs.Lagna] : "—"}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
