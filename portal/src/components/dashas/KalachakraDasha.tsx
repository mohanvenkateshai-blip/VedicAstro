"use client";

import React from "react";
import { Card } from "@/components/ui/Card";
import type { SignDashaBlock } from "@/lib/types";

interface KalachakraDashaProps {
  data: SignDashaBlock | null;
}

export function KalachakraDasha({ data }: KalachakraDashaProps) {
  const d = data as any;
  if (!d) {
    return (
      <Card className="p-5 border border-hairline">
        <h3 className="font-semibold text-lg mb-2">Kalachakra Dasha</h3>
        <p className="text-sm text-text-muted">No Kalachakra data available for this chart.</p>
      </Card>
    );
  }

  const periods = d.periods || [];
  const current = d.maha ? { maha: d.maha, antara: d.antara, start: d.mahaStart, end: d.mahaEnd } : null;

  return (
    <Card className="p-5 space-y-4 border border-hairline">
      <div className="flex items-center justify-between">
        <h3 className="font-[family-name:var(--font-display)] font-semibold text-lg">Kalachakra Dasha</h3>
        <span className="text-[10px] font-mono text-text-muted">86y cycle · BPHS Vol.2 / Phaladeepika / Deva Keralam</span>
      </div>

      {current && (
        <div className="rounded-lg border border-accent/30 bg-accent/5 p-3 text-sm">
          <div className="font-mono text-accent font-semibold">
            Current: {current.maha} / {current.antara}
          </div>
          <div className="text-xs text-text-muted mt-0.5">
            {current.start} → {current.end}
          </div>
          {(data as any).dehaJeeva?.note && (
            <p className="text-[11px] text-text-muted mt-1 italic">{(data as any).dehaJeeva.note}</p>
          )}
        </div>
      )}

      {periods.length > 0 && (
        <div>
          <h4 className="text-xs font-mono uppercase text-text-muted mb-2">Upcoming Periods (first 8)</h4>
          <div className="space-y-1 text-xs font-mono">
            {periods.slice(0, 8).map((p: any, i: number) => (
              <div key={i} className={`flex justify-between border-l-2 pl-2 ${p.isCurrent ? "border-accent text-accent" : "border-hairline"}`}>
                <span>{p.maha} / {p.antara}</span>
                <span>{p.start} → {p.end} ({p.years}y)</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {(data as any).graph_citations && (data as any).graph_citations.length > 0 && (
        <div className="pt-2 border-t border-hairline text-[10px] text-text-muted">
          Sources: {(data as any).graph_citations.map((c: any) => c.label || c.id).join(" · ")}
        </div>
      )}

      <p className="text-[10px] text-text-muted font-mono">Deha/Jeeva from Moon nakshatra-pada wheel (BPHS Vol.2 Ch.49) · ke:{(data as any).ke_version || "—"}</p>
    </Card>
  );
}
