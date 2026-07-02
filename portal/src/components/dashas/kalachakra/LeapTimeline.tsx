"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { clsx } from "clsx";
import type { KalachakraTimelineEntry } from "@/lib/types";
import { leapStyle } from "./kalachakraCopy";

const LEVEL_LABELS: Record<number, string> = { 1: "MD", 2: "AD", 3: "PD" };

function TimelineRow({ entry }: { entry: KalachakraTimelineEntry }) {
  const style = leapStyle(entry.leap.type);
  return (
    <div
      className={clsx(
        "flex items-center justify-between gap-3 rounded-lg border px-3 py-2 text-xs",
        style.bgClass,
        style.borderClass,
      )}
    >
      <div className="flex items-center gap-2 min-w-0">
        <span className="font-mono text-[10px] text-text-muted shrink-0">
          {LEVEL_LABELS[entry.level] ?? entry.level}
        </span>
        <span className="font-medium truncate">{entry.sign}</span>
        <span className={clsx("shrink-0 font-mono text-[10px]", style.colorClass)}>
          {style.shortLabel}
        </span>
      </div>
      <span className="font-mono text-[10px] text-text-muted shrink-0">
        {entry.start} → {entry.end}
      </span>
    </div>
  );
}

export function LeapTimeline({ entries }: { entries: KalachakraTimelineEntry[] }) {
  const [open, setOpen] = useState(false);

  const past = entries.filter((e) => e.when === "past");
  const current = entries.filter((e) => e.when === "current");
  const future = entries.filter((e) => e.when === "future");

  if (entries.length === 0) return null;

  return (
    <div className="rounded-2xl border border-hairline bg-card p-4">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between text-left"
      >
        <div>
          <h3 className="text-sm font-medium">Leap Timeline</h3>
          <p className="text-xs text-text-muted mt-0.5">
            {entries.length} Gati across this cycle — {past.length} past, {current.length} current,{" "}
            {future.length} upcoming
          </p>
        </div>
        {open ? (
          <ChevronDown className="h-4 w-4 text-text-muted shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-text-muted shrink-0" />
        )}
      </button>

      {open && (
        <div className="mt-4 space-y-4 max-h-96 overflow-y-auto pr-1">
          {current.length > 0 && (
            <div className="space-y-1.5">
              <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">
                Current
              </div>
              {current.map((e, i) => (
                <TimelineRow key={`c-${i}`} entry={e} />
              ))}
            </div>
          )}
          {future.length > 0 && (
            <div className="space-y-1.5">
              <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">
                Future
              </div>
              {future.map((e, i) => (
                <TimelineRow key={`f-${i}`} entry={e} />
              ))}
            </div>
          )}
          {past.length > 0 && (
            <div className="space-y-1.5">
              <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">
                Past
              </div>
              {past.map((e, i) => (
                <TimelineRow key={`p-${i}`} entry={e} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
