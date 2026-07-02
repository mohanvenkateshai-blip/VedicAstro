"use client";

import { useState } from "react";
import { clsx } from "clsx";
import { Card } from "@/components/ui/Card";
import type { KalachakraDeepData, KalachakraNode } from "@/lib/types";
import { CurrentStateWidget } from "./CurrentStateWidget";
import { LeapTimeline } from "./LeapTimeline";
import { KalachakraWheel } from "./KalachakraWheel";
import { KalachakraTree } from "./KalachakraTree";
import { LeapExplanationSheet } from "./LeapExplanationSheet";
import { PeriodDetailModal } from "./PeriodDetailModal";

export function KalachakraDashboard({ data }: { data: KalachakraDeepData }) {
  const [leapNode, setLeapNode] = useState<KalachakraNode | null>(null);
  const [periodNode, setPeriodNode] = useState<KalachakraNode | null>(null);
  const [method, setMethod] = useState<"primary" | "alternate">("primary");

  if (data.status === "error") {
    return (
      <Card className="p-6 border border-amber-500/40">
        <p className="text-sm text-amber-600">Kalachakra calculation unavailable for this chart.</p>
        {data.error && <p className="text-xs text-text-muted mt-1 font-mono">{data.error}</p>}
      </Card>
    );
  }

  const alt = data.alternateMethod;
  const view =
    method === "alternate" && alt
      ? { currentLadder: alt.currentLadder, activeLeap: alt.activeLeap, dashaTree: alt.dashaTree, leapTimeline: alt.leapTimeline }
      : { currentLadder: data.currentLadder, activeLeap: data.activeLeap, dashaTree: data.dashaTree, leapTimeline: data.leapTimeline };

  const currentSign = view.currentLadder?.[0]?.sign ?? null;

  return (
    <div className="space-y-4">
      {alt && (
        <div className="flex items-center gap-2 rounded-xl border border-hairline bg-card p-1.5 w-fit">
          <button
            onClick={() => setMethod("primary")}
            className={clsx(
              "rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
              method === "primary" ? "bg-accent text-accent-fg" : "text-text-muted hover:text-text-fg",
            )}
          >
            PVR / Book (BPHS Ch.46)
          </button>
          <button
            onClick={() => setMethod("alternate")}
            className={clsx(
              "rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
              method === "alternate" ? "bg-accent text-accent-fg" : "text-text-muted hover:text-text-fg",
            )}
          >
            {alt.methodLabel}
          </button>
        </div>
      )}

      {method === "alternate" && alt && !alt.gatisVerified && (
        <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-600">
          The Frog/Lion/Monkey Gati names shown here are geometric (non-adjacent sign jump) but not
          classically verified for this method — BPHS Vol.2 Ch.46 defines them specifically for the
          PVR/Book model.
        </div>
      )}

      <Card className="p-5">
        <CurrentStateWidget data={{ ...data, activeLeap: view.activeLeap }} />
      </Card>

      {data.cycle && (
        <Card className="p-5">
          <h3 className="text-sm font-medium mb-3">
            {data.birthNakshatra?.kcGroupName} · Pada {data.birthNakshatra?.pada} wheel
          </h3>
          <KalachakraWheel cycle={data.cycle} currentSign={currentSign} />
          <p className="text-xs text-text-muted text-center mt-2">
            Slice width ∝ years allotted · current period pulses · dotted arrows mark Gati leaps
          </p>
        </Card>
      )}

      {view.leapTimeline && <LeapTimeline entries={view.leapTimeline} />}

      {view.dashaTree && view.dashaTree.length > 0 && (
        <Card className="p-5">
          <h3 className="text-sm font-medium mb-3">Mahadasha → Antardasha → Pratyantardasha</h3>
          <KalachakraTree
            tree={view.dashaTree}
            onSelectPeriod={setPeriodNode}
            onSelectLeap={setLeapNode}
          />
        </Card>
      )}

      {data.balanceOfFirstDasha && (
        <p className="text-[10px] px-1 font-mono text-text-muted">
          Balance of first dasha: {data.balanceOfFirstDasha.actual ?? "—"}y (simplified estimate:{" "}
          {data.balanceOfFirstDasha.simplifiedEstimate ?? "—"}y) · ke:{data.ke_version ?? "—"}
        </p>
      )}

      <LeapExplanationSheet node={leapNode} onClose={() => setLeapNode(null)} />
      <PeriodDetailModal node={periodNode} cycle={data.cycle} onClose={() => setPeriodNode(null)} />
    </div>
  );
}
