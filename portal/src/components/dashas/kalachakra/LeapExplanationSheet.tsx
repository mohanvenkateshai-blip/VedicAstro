"use client";

import { clsx } from "clsx";
import { Overlay } from "@/components/ui/Overlay";
import type { KalachakraNode } from "@/lib/types";
import { leapStyle } from "./kalachakraCopy";

export function LeapExplanationSheet({
  node,
  onClose,
}: {
  node: KalachakraNode | null;
  onClose: () => void;
}) {
  const leap = node?.leapFromPrevious;
  const style = leap ? leapStyle(leap.type) : null;

  return (
    <Overlay open={!!node && !!leap} onClose={onClose} slideFrom="bottom" ariaLabel="Leap explanation">
      {node && leap && style && (
        <div className="p-6">
          <div className={clsx("inline-flex items-center gap-2 rounded-full border px-3 py-1 mb-4", style.bgClass, style.borderClass)}>
            <span className={clsx("text-sm font-medium", style.colorClass)}>{leap.label}</span>
          </div>
          <p className="text-sm leading-relaxed text-text-fg">{style.explanation}</p>
          <div className="mt-4 flex items-center justify-between rounded-xl border border-hairline bg-surface px-3 py-2 text-xs font-mono text-text-muted">
            <span>{node.sign}</span>
            <span>{node.start} → {node.end}</span>
          </div>
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
