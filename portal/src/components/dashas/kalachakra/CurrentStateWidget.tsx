"use client";

import { clsx } from "clsx";
import type { KalachakraDeepData } from "@/lib/types";
import { leapStyle } from "./kalachakraCopy";
import { narrateTeaser } from "./kalachakraNarrative";

function SignPill({ label, sign }: { label: string; sign: string }) {
  return (
    <div className="flex items-center gap-2 rounded-xl border border-hairline bg-card px-3 py-2">
      <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">
        {label}
      </span>
      <span className="text-sm font-medium">{sign}</span>
    </div>
  );
}

export function CurrentStateWidget({ data }: { data: KalachakraDeepData }) {
  const cycle = data.cycle;
  const leap = data.activeLeap;
  const deepest = data.currentLadder?.[data.currentLadder.length - 1];
  const teaser = deepest ? narrateTeaser(deepest.signIndex, data.signInterpretations) : null;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        {cycle && <SignPill label="Deha (Body)" sign={cycle.dehaRasi} />}
        {cycle && <SignPill label="Jeeva (Soul)" sign={cycle.jeevaRasi} />}
        {data.birthNakshatra && (
          <div className="flex items-center gap-2 rounded-xl border border-hairline bg-card px-3 py-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">
              Pada Wheel
            </span>
            <span className="text-sm font-medium">
              {data.birthNakshatra.nakshatra} · Pada {data.birthNakshatra.pada} ·{" "}
              {data.birthNakshatra.direction}
            </span>
          </div>
        )}
      </div>

      {teaser && (
        <p className="text-xs text-text-muted leading-relaxed px-1">{teaser}</p>
      )}

      {leap && (() => {
        const style = leapStyle(leap.type);
        const Icon = style.icon;
        return (
          <div className={clsx("flex items-start gap-3 rounded-xl border-l-4 border-y border-r p-4", style.bgClass, style.borderClass)}>
            <span className={clsx("grid h-9 w-9 shrink-0 place-items-center rounded-lg", style.bgClass)}>
              <Icon className={clsx("h-5 w-5", style.colorClass)} />
            </span>
            <div>
              <div className={clsx("text-sm font-semibold", style.colorClass)}>
                Active {leap.label}
              </div>
              <p className="text-xs text-text-muted mt-1 leading-relaxed">{style.explanation}</p>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
