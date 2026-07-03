"use client";

import { clsx } from "clsx";
import { Overlay } from "@/components/ui/Overlay";
import type { KalachakraNode } from "@/lib/types";
import { leapStyle, strengthStyle } from "./kalachakraCopy";

export function LeapExplanationSheet({
  node,
  onClose,
}: {
  node: KalachakraNode | null;
  onClose: () => void;
}) {
  const leap = node?.leapFromPrevious;
  const style = leap ? leapStyle(leap.type) : null;
  const Icon = style?.icon;

  return (
    <Overlay open={!!node && !!leap} onClose={onClose} slideFrom="bottom" ariaLabel="Leap explanation">
      {node && leap && style && Icon && (
        <div className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <span className={clsx("grid h-11 w-11 shrink-0 place-items-center rounded-xl", style.bgClass)}>
              <Icon className={clsx("h-5 w-5", style.colorClass)} />
            </span>
            <div>
              <div className={clsx("text-base font-semibold", style.colorClass)}>{leap.label}</div>
              <div className="text-xs text-text-muted font-mono">
                {node.sign} · {node.start} → {node.end}
              </div>
            </div>
          </div>

          <p className="text-sm leading-relaxed text-text-fg">{style.explanation}</p>

          {leap.strength && (() => {
            const sStyle = strengthStyle(leap.strength!);
            return (
              <div className={clsx("mt-3 flex items-center justify-between rounded-xl border px-3 py-2.5", sStyle.bgClass)}>
                <div>
                  <div className={clsx("text-sm font-semibold", sStyle.colorClass)}>{sStyle.label}</div>
                  <div className="text-[11px] text-text-muted">
                    Ashtakavarga: {leap.strength.bindus} bindus in {leap.strength.sign} (D1 SAV)
                  </div>
                </div>
                <div className={clsx("text-2xl font-bold", sStyle.colorClass)}>{leap.strength.bindus}</div>
              </div>
            );
          })()}

          <div className="mt-3 grid gap-2.5">
            <div className="rounded-xl border border-hairline bg-surface px-3 py-2.5">
              <div className="text-[10px] font-mono uppercase tracking-wider text-text-muted mb-1">
                Classical effects
              </div>
              <p className="text-xs text-text-fg leading-relaxed">{style.classicEffects}</p>
            </div>
            <div className={clsx("rounded-xl border px-3 py-2.5", style.borderClass, style.bgClass)}>
              <div className={clsx("text-[10px] font-mono uppercase tracking-wider mb-1", style.colorClass)}>
                Positive potential
              </div>
              <p className="text-xs text-text-fg leading-relaxed">{style.positivePotential}</p>
            </div>
          </div>
          <p className="mt-3 text-[11px] text-text-muted leading-relaxed">
            {leap.strength
              ? "30+ bindus generally lean toward the positive potential; below 22 leans toward the classical warning effects. Also weigh planets aspecting/occupying this sign and the dasha lord's own condition."
              : "Outcome depends on chart strength — Ashtakavarga bindus in this sign, planets aspecting or occupying it, and the overall dasha lord's condition."}
          </p>

          {leap.verified === false && (
            <p className="mt-3 text-xs text-amber-600">
              Note: this name is geometric (non-adjacent sign jump), not classically verified for the
              method used to compute this period — BPHS Vol.2 Ch.46 defines these three Gatis
              specifically for the PVR/Book model.
            </p>
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
