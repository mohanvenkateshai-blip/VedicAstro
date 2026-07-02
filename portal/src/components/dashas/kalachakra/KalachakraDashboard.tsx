"use client";

import { useState } from "react";
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

  if (data.status === "error") {
    return (
      <Card className="p-6 border border-amber-500/40">
        <p className="text-sm text-amber-600">Kalachakra calculation unavailable for this chart.</p>
        {data.error && <p className="text-xs text-text-muted mt-1 font-mono">{data.error}</p>}
      </Card>
    );
  }

  const currentSign = data.currentLadder?.[0]?.sign ?? null;

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <CurrentStateWidget data={data} />
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

      {data.leapTimeline && <LeapTimeline entries={data.leapTimeline} />}

      {data.dashaTree && data.dashaTree.length > 0 && (
        <Card className="p-5">
          <h3 className="text-sm font-medium mb-3">Mahadasha → Antardasha → Pratyantardasha</h3>
          <KalachakraTree
            tree={data.dashaTree}
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
