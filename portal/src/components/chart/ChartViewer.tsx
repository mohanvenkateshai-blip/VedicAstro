"use client";

import { useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import { KundaliChart } from "./KundaliChart";
import type { ChartData } from "@/lib/types";
import { RASHIS } from "@/lib/types";

const DIGNITY_COLOR: Record<string, string> = {
  exalted: "text-success",
  own: "text-accent",
  debilitated: "text-danger",
};

export function ChartViewer({ chart }: { chart: ChartData }) {
  const [variant, setVariant] = useState<"south" | "north">("south");
  const [vargaKey, setVargaKey] = useState<string>("D1");
  const [showSav, setShowSav] = useState(false);
  const prefersReduced = useReducedMotion();

  const vargaKeys = Object.keys(chart.vargas ?? {});
  const varga = chart.vargas?.[vargaKey] ?? chart.vargas?.D1;
  const signs = varga?.signs ?? {};
  const sav = chart.ashtakavarga?.sav;

  return (
    <div className="grid gap-6 lg:grid-cols-[auto_1fr]">
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-2">
          <div role="radiogroup" aria-label="Chart orientation" className="inline-flex rounded-lg border border-hairline p-0.5 text-xs">
            {(["south", "north"] as const).map((v) => (
              <button
                key={v}
                onClick={() => setVariant(v)}
                role="radio"
                aria-checked={variant === v}
                aria-label={`${v === "south" ? "South" : "North"} Indian chart style`}
                className={`px-3 py-2 min-h-[44px] rounded-md transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 ${variant === v ? "bg-primary text-primary-fg" : "text-text-muted hover:text-text-main"}`}
              >
                {v === "south" ? "South" : "North"}
              </button>
            ))}
          </div>
          <label htmlFor="sav-toggle" className="flex items-center gap-1.5 text-xs text-text-muted cursor-pointer select-none min-h-[44px]">
            <input id="sav-toggle" type="checkbox" checked={showSav} onChange={(e) => setShowSav(e.target.checked)} className="accent-[var(--color-accent)]" />
            SAV bindus
          </label>
        </div>

        <motion.div
          key={`${variant}-${vargaKey}`}
          initial={prefersReduced ? {} : { opacity: 0, scale: 0.98 }}
          animate={prefersReduced ? {} : { opacity: 1, scale: 1 }}
          transition={{ duration: 0.25 }}
        >
          <KundaliChart
            signs={signs}
            variant={variant}
            sav={showSav && vargaKey === "D1" ? sav : undefined}
            size={340}
          />
        </motion.div>

        <div className="flex flex-wrap gap-1.5">
          {vargaKeys.map((k) => (
            <button
              key={k}
              onClick={() => setVargaKey(k)}
              aria-pressed={vargaKey === k}
              aria-label={`Show ${chart.vargas[k]?.name ?? k} chart`}
              title={chart.vargas[k]?.name}
              className={`px-2.5 py-2 min-h-[44px] rounded-md text-[11px] font-mono border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 ${vargaKey === k ? "border-accent text-accent" : "border-hairline text-text-muted hover:text-text-main"}`}
            >
              {k}
            </button>
          ))}
        </div>
        <p className="text-[11px] text-text-muted">
          {varga?.name} chart ({vargaKey}). Lagna in{" "}
          {RASHIS[signs.Lagna ?? 0]}.
        </p>
      </div>

      <div className="min-w-0">
        <div className="overflow-x-auto rounded-xl border border-hairline">
          <table className="w-full text-sm" aria-label="Planetary positions">
            <caption className="sr-only">Planetary positions table for {chart.meta?.name ?? "chart"}</caption>
            <thead>
              <tr className="text-left text-[10px] uppercase tracking-wider text-text-muted border-b border-hairline">
                <th scope="col" className="px-3 py-2 font-medium">Planet</th>
                <th scope="col" className="px-3 py-2 font-medium">Rāśi</th>
                <th scope="col" className="px-3 py-2 font-medium">Nakṣatra</th>
                <th scope="col" className="px-3 py-2 font-medium">Pada</th>
                <th scope="col" className="px-3 py-2 font-medium">Deg</th>
                <th scope="col" className="px-3 py-2 font-medium">State</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-hairline/60">
                <td className="px-3 py-2 font-medium text-accent">Lagna</td>
                <td className="px-3 py-2">{chart.lagna.rashi}</td>
                <td className="px-3 py-2">{chart.lagna.nakshatra}</td>
                <td className="px-3 py-2">{chart.lagna.pada}</td>
                <td className="px-3 py-2 font-mono text-xs">{chart.lagna.degLabel}</td>
                <td className="px-3 py-2" />
              </tr>
              {chart.planets.map((p) => (
                <tr key={p.planet} className="border-b border-hairline/60 last:border-0 hover:bg-[color-mix(in_srgb,var(--color-accent)_5%,transparent)]">
                  <td className="px-3 py-2 font-medium">{p.planet}</td>
                  <td className="px-3 py-2">{p.rashi}</td>
                  <td className="px-3 py-2">{p.nakshatra}</td>
                  <td className="px-3 py-2">{p.pada}</td>
                  <td className="px-3 py-2 font-mono text-xs">{p.degLabel}</td>
                  <td className="px-3 py-2 text-xs">
                    <span className={DIGNITY_COLOR[p.dignity ?? ""] ?? "text-text-muted"}>
                      {p.dignity && p.dignity !== "neutral" ? p.dignity : ""}
                    </span>
                    {p.retro && <span className="text-text-muted"> ℞</span>}
                    {p.combust && <span className="text-warning"> ☌</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {chart.dashas?.current != null && (
          <p className="mt-3 text-xs text-text-muted">
            Ayanāṁśa: <span className="text-text-main">{chart.ayanamsa}</span>
            {" · "}Engine: <span className="text-text-main">{chart.meta?.engine}</span>
            {chart.ashtakavarga && <> {" · "}SAV total: <span className="text-text-main">{chart.ashtakavarga.sav.reduce((a, b) => a + b, 0)}</span></>}
          </p>
        )}
      </div>
    </div>
  );
}
