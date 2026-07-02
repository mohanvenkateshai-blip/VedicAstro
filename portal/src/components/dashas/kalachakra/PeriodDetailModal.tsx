"use client";

import { clsx } from "clsx";
import { Overlay } from "@/components/ui/Overlay";
import type { KalachakraCycle, KalachakraNode } from "@/lib/types";
import { leapStyle } from "./kalachakraCopy";

const LEVEL_LABELS: Record<number, string> = { 1: "Mahadasha", 2: "Antardasha", 3: "Pratyantardasha" };

export function PeriodDetailModal({
  node,
  cycle,
  onClose,
}: {
  node: KalachakraNode | null;
  cycle: KalachakraCycle | undefined;
  onClose: () => void;
}) {
  const leap = node?.leapFromPrevious;
  const isDeha = cycle && node && node.sign === cycle.dehaRasi;
  const isJeeva = cycle && node && node.sign === cycle.jeevaRasi;

  return (
    <Overlay open={!!node} onClose={onClose} slideFrom="center" ariaLabel="Period details">
      {node && (
        <div className="p-6">
          <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">
            {LEVEL_LABELS[node.level] ?? `Level ${node.level}`}
          </div>
          <h3 className="text-lg font-semibold mt-1">{node.sign}</h3>

          <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
            <div className="rounded-xl border border-hairline bg-surface px-3 py-2">
              <div className="text-text-muted font-mono text-[10px] uppercase">Start</div>
              <div className="mt-0.5 font-mono">{node.start}</div>
            </div>
            <div className="rounded-xl border border-hairline bg-surface px-3 py-2">
              <div className="text-text-muted font-mono text-[10px] uppercase">End</div>
              <div className="mt-0.5 font-mono">{node.end ?? "—"}</div>
            </div>
            <div className="col-span-2 rounded-xl border border-hairline bg-surface px-3 py-2">
              <div className="text-text-muted font-mono text-[10px] uppercase">Duration</div>
              <div className="mt-0.5 font-mono">{node.durationYears.toFixed(2)} years</div>
            </div>
          </div>

          {(isDeha || isJeeva) && (
            <div className="mt-3 flex gap-2">
              {isDeha && (
                <span className="rounded-full border border-accent/40 bg-accent/10 px-2.5 py-1 text-[11px] font-medium text-accent">
                  Deha Rasi
                </span>
              )}
              {isJeeva && (
                <span className="rounded-full border border-accent/40 bg-accent/10 px-2.5 py-1 text-[11px] font-medium text-accent">
                  Jeeva Rasi
                </span>
              )}
            </div>
          )}

          {leap && (
            <div className={clsx("mt-4 rounded-xl border p-3", leapStyle(leap.type).bgClass, leapStyle(leap.type).borderClass)}>
              <div className={clsx("text-sm font-medium", leapStyle(leap.type).colorClass)}>{leap.label}</div>
              <p className="text-xs text-text-muted mt-1 leading-relaxed">{leapStyle(leap.type).explanation}</p>
            </div>
          )}

          <button
            onClick={onClose}
            className="mt-5 w-full rounded-xl border border-hairline py-2.5 text-sm font-medium hover:bg-surface"
          >
            Close
          </button>
        </div>
      )}
    </Overlay>
  );
}
