"use client";

import { AlertTriangle } from "lucide-react";
import { clsx } from "clsx";
import type { KalachakraDeepData } from "@/lib/types";
import { leapStyle } from "./kalachakraCopy";

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

      {leap && (
        <div
          className={clsx(
            "flex items-start gap-3 rounded-xl border p-4",
            leapStyle(leap.type).bgClass,
            leapStyle(leap.type).borderClass,
          )}
        >
          <AlertTriangle className={clsx("h-5 w-5 shrink-0 mt-0.5", leapStyle(leap.type).colorClass)} />
          <div>
            <div className={clsx("text-sm font-medium", leapStyle(leap.type).colorClass)}>
              Active {leap.label}
            </div>
            <p className="text-xs text-text-muted mt-1 leading-relaxed">
              {leapStyle(leap.type).explanation}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
