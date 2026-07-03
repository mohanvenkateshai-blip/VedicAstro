"use client";

import { useEffect, useState } from "react";
import { clsx } from "clsx";
import type { KalachakraLeapInfo, KalachakraTimelineEntry } from "@/lib/types";
import { LEAP_STYLES, leapStyle } from "./kalachakraCopy";

const LEVEL_LABELS: Record<number, string> = { 1: "MD", 2: "AD", 3: "PD" };
const LEAP_TYPES: KalachakraLeapInfo["type"][] = ["frog_leap", "lions_leap", "monkey_leap"];

/**
 * Three tabs — one per Gati (Frog / Lion / Monkey) — listing every occurrence of
 * that leap across the person's life. Clicking an entry jumps the tree below to
 * the exact MD/AD/PD node (via `onJump(path)`), so there's a direct path from
 * "what leaps exist" to "where exactly do they sit in the dasha tree."
 */
export function LeapQuickNav({
  entries,
  onJump,
}: {
  entries: KalachakraTimelineEntry[];
  onJump: (path: string) => void;
}) {
  const [active, setActive] = useState<KalachakraLeapInfo["type"]>("frog_leap");

  const grouped = LEAP_TYPES.map((type) => ({
    type,
    items: entries.filter((e) => e.leap.type === type),
  }));

  useEffect(() => {
    const current = grouped.find((g) => g.type === active);
    if (current && current.items.length > 0) return;
    const firstNonEmpty = grouped.find((g) => g.items.length > 0);
    if (firstNonEmpty) setActive(firstNonEmpty.type);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entries]);

  if (entries.length === 0) return null;

  const activeItems = grouped.find((g) => g.type === active)?.items ?? [];

  return (
    <div className="rounded-2xl border border-hairline bg-card p-4">
      <h3 className="text-sm font-medium mb-3">Jump to a Leap</h3>
      <div className="flex items-center gap-1.5 flex-wrap">
        {grouped.map(({ type, items }) => {
          const style = LEAP_STYLES[type];
          const Icon = style.icon;
          const isActive = active === type;
          return (
            <button
              key={type}
              onClick={() => setActive(type)}
              disabled={items.length === 0}
              className={clsx(
                "flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed",
                isActive ? style.bgClass : "hover:bg-hairline/30",
                isActive ? style.colorClass : "text-text-muted",
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {style.shortLabel}
              <span className="rounded-full bg-hairline/40 px-1.5 text-[10px] font-mono">{items.length}</span>
            </button>
          );
        })}
      </div>

      <div className="mt-3 space-y-1.5 max-h-64 overflow-y-auto pr-1">
        {activeItems.length === 0 ? (
          <p className="text-xs text-text-muted py-2">No {leapStyle(active).shortLabel} in this dasha tree.</p>
        ) : (
          activeItems.map((entry, i) => {
            const style = leapStyle(entry.leap.type);
            return (
              <button
                key={i}
                onClick={() => onJump(entry.path)}
                className={clsx(
                  "flex w-full items-center justify-between gap-3 rounded-lg border-l-4 border-y border-r py-2 pl-2.5 pr-3 text-xs text-left transition-colors hover:brightness-110",
                  style.bgClass,
                  style.borderClass,
                )}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="font-mono text-[10px] text-text-muted shrink-0">
                    {LEVEL_LABELS[entry.level] ?? entry.level}
                  </span>
                  <span className="font-medium truncate">{entry.sign}</span>
                  <span
                    className={clsx(
                      "shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-mono uppercase tracking-wide",
                      entry.when === "current"
                        ? "bg-accent/15 text-accent"
                        : "bg-hairline/40 text-text-muted",
                    )}
                  >
                    {entry.when}
                  </span>
                </div>
                <span className="font-mono text-[10px] text-text-muted shrink-0">
                  {entry.start} → {entry.end}
                </span>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
