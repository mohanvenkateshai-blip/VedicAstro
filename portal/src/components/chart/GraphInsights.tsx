"use client";

import { useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import type { GraphEnhancements, PlanetTransitAnalysis, TransitIntelligence } from "@/lib/types";

function ordinal(n: number): string {
  if (n === 1) return "1st";
  if (n === 2) return "2nd";
  if (n === 3) return "3rd";
  if (n >= 11 && n <= 13) return `${n}th`;
  const v = n % 10;
  if (v === 1) return `${n}st`;
  if (v === 2) return `${n}nd`;
  if (v === 3) return `${n}rd`;
  return `${n}th`;
}

function verdictClass(v: string): string {
  if (v === "shubh") return "bg-success/15 text-success";
  if (v === "ashubh") return "bg-danger/15 text-danger";
  return "bg-warning/15 text-warning";
}

function verdictLabel(v: string): string {
  if (v === "shubh") return "Favourable";
  if (v === "ashubh") return "Unfavourable";
  if (v === "mixed") return "Mixed";
  return v;
}

export function GraphInsights({ data }: { data: GraphEnhancements }) {
  const intel = data.transit_intelligence;
  if (intel?.planets?.length) {
    return <TransitIntelligencePanel intel={intel} />;
  }
  return (
    <p className="mt-8 text-sm text-text-muted rounded-2xl border border-hairline bg-card p-5">
      Transit analysis unavailable for this chart. Check birth Moon sign is present.
    </p>
  );
}

function TransitIntelligencePanel({ intel }: { intel: TransitIntelligence }) {
  const prefersReduced = useReducedMotion();
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="mt-8 rounded-2xl border border-hairline bg-card">
      <div className="px-5 py-4 border-b border-hairline">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="grid h-7 w-7 place-items-center rounded-lg bg-accent/15 text-accent text-xs" aria-hidden="true">◎</span>
              <span className="text-sm font-medium">Transit Intelligence</span>
              <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded ${verdictClass(intel.overall_verdict)}`}>
                {verdictLabel(intel.overall_verdict)}
              </span>
            </div>
            <p className="mt-2 text-xs text-text-muted leading-relaxed max-w-2xl">{intel.day_summary}</p>
          </div>
          <span className="text-[11px] font-mono text-text-muted">score {intel.overall_score}</span>
        </div>

        {(intel.dasha_context || intel.moorthy_note || intel.tara_note) && (
          <div className="mt-3 flex flex-wrap gap-2">
            {intel.dasha_context && (
              <span className="text-[10px] px-2 py-1 rounded-full border border-hairline text-text-muted">{intel.dasha_context}</span>
            )}
            {intel.moorthy_note && (
              <span className="text-[10px] px-2 py-1 rounded-full border border-hairline text-text-muted max-w-md truncate" title={intel.moorthy_note}>
                {intel.moorthy_note}
              </span>
            )}
            {intel.tara_note && (
              <span className="text-[10px] px-2 py-1 rounded-full border border-hairline text-text-muted">{intel.tara_note}</span>
            )}
          </div>
        )}

        {intel.top_drivers.length > 0 && (
          <div className="mt-3">
            <p className="text-[10px] uppercase tracking-wide text-text-muted mb-1">Key drivers today</p>
            <ul className="text-xs text-text-main space-y-0.5">
              {intel.top_drivers.map((d, i) => (
                <li key={i}>· {d}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="p-5 grid gap-3">
        {intel.planets.map((p, i) => (
          <PlanetCard
            key={p.planet}
            planet={p}
            index={i}
            open={expanded === p.planet}
            onToggle={() => setExpanded(expanded === p.planet ? null : p.planet)}
            prefersReduced={prefersReduced}
          />
        ))}
      </div>
    </div>
  );
}

function PlanetCard({
  planet: p,
  index,
  open,
  onToggle,
  prefersReduced,
}: {
  planet: PlanetTransitAnalysis;
  index: number;
  open: boolean;
  onToggle: () => void;
  prefersReduced: boolean | null;
}) {
  return (
    <motion.div
      initial={prefersReduced ? {} : { opacity: 0, y: 6 }}
      animate={prefersReduced ? {} : { opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03 }}
      className="rounded-xl border border-hairline overflow-hidden"
    >
      <button
        type="button"
        onClick={onToggle}
        className="w-full text-left p-3 hover:bg-[color-mix(in_srgb,var(--color-accent)_4%,transparent)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
        aria-expanded={open}
      >
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium">{p.planet}</span>
          <span className="text-xs text-text-muted font-mono">{p.rashi}</span>
          {p.house_from_janma != null && (
            <span className="text-xs text-text-muted font-mono">· {ordinal(p.house_from_janma)} from Moon</span>
          )}
          {p.retrograde && (
            <span className="text-[10px] font-mono text-text-muted">Rx</span>
          )}
          <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded ${verdictClass(p.final_verdict)}`}>
            {verdictLabel(p.final_verdict)}
          </span>
          <span className="ml-auto text-[10px] font-mono text-text-muted">{p.score > 0 ? "+" : ""}{p.score}</span>
        </div>
        <p className="mt-2 text-xs text-text-muted leading-relaxed line-clamp-2">{p.summary}</p>
        <p className="mt-1 text-[11px] text-accent/90 font-medium">{p.primary_driver}</p>
      </button>

      {open && (
        <div className="px-3 pb-3 pt-0 border-t border-hairline/60 space-y-3">
          <Section title="Root cause" items={[p.root_cause]} />
          {p.aggravating.length > 0 && (
            <Section title="Aggravating factors" items={p.aggravating} tone="danger" />
          )}
          {p.mitigating.length > 0 && (
            <Section title="Mitigating factors" items={p.mitigating} tone="success" />
          )}
          {p.negative_impact.length > 0 && (
            <Section title="What to watch" items={p.negative_impact} />
          )}
          {p.positive_impact.length > 0 && (
            <Section title="Possible support" items={p.positive_impact} tone="success" />
          )}
          {p.factors.length > 0 && (
            <div>
              <p className="text-[10px] uppercase tracking-wide text-text-muted mb-1.5">Judgment trail</p>
              <ul className="space-y-1">
                {p.factors.map((f, i) => (
                  <li key={i} className="text-[11px] text-text-muted flex gap-2">
                    <span className={`shrink-0 font-mono ${f.weight > 0 ? "text-success" : f.weight < 0 ? "text-danger" : ""}`}>
                      {f.weight > 0 ? "+" : ""}{f.weight}
                    </span>
                    <span>{f.summary}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {p.classical_basis.length > 0 && (
            <p className="text-[10px] text-text-muted font-mono">
              Basis: {p.classical_basis.join(" · ")}
            </p>
          )}
        </div>
      )}
    </motion.div>
  );
}

function Section({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone?: "danger" | "success";
}) {
  const color = tone === "danger" ? "text-danger/90" : tone === "success" ? "text-success/90" : "text-text-muted";
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wide text-text-muted mb-1">{title}</p>
      <ul className={`text-xs space-y-1 ${color}`}>
        {items.map((item, i) => (
          <li key={i}>· {item}</li>
        ))}
      </ul>
    </div>
  );
}
