"use client";

import { useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import type { GraphEnhancements, TransitCitation, YogaCitation, GodNodeInsight } from "@/lib/types";

const SOURCE_ICONS: Record<string, string> = {
  "raw/Gochar_Phaladeepika_Pulippani.md": "Pulippani",
  "raw/Brihat_Parasara_Hora_Sastra_Vol_1.md": "BPHS",
  "raw/Phaladeepika_Mantreswara.md": "PD",
  "raw/Activity_Mapping.md": "Activity Map",
};

function sourceLabel(f: string) {
  for (const [k, v] of Object.entries(SOURCE_ICONS)) {
    if (f.includes(k) || f.includes(k.replace("raw/", ""))) return v;
  }
  return f.split("/").pop()?.replace(".md", "") ?? f;
}

export function GraphInsights({ data }: { data: GraphEnhancements }) {
  const [tab, setTab] = useState<"transit" | "yoga" | "god" | "conflicts">("transit");
  const prefersReduced = useReducedMotion();

  const tabs = [
    { key: "transit" as const, label: "Transits", count: data.transit_citations?.length ?? 0 },
    { key: "yoga" as const, label: "Yogas", count: data.yoga_citations?.length ?? 0 },
    { key: "god" as const, label: "Key Concepts", count: data.god_node_insights?.length ?? 0 },
    { key: "conflicts" as const, label: "Conflicts", count: data.text_conflicts?.length ?? 0 },
  ].filter((t) => t.count > 0);

  if (tabs.length === 0) return null;

  return (
    <div className="mt-8 rounded-2xl border border-hairline bg-card">
      <div className="flex items-center justify-between gap-3 px-5 py-4 border-b border-hairline">
        <div className="flex items-center gap-2">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-accent/15 text-accent text-xs" aria-hidden="true">⚛</span>
          <div>
            <span className="text-sm font-medium">Knowledge Graph Insights</span>
            <span className="ml-2 text-[11px] text-text-muted font-mono">
              {data.graph_stats?.nodes ?? 0} nodes · {data.graph_stats?.links ?? 0} links · 4 texts
            </span>
          </div>
        </div>
        <div role="tablist" aria-label="Insights sections" className="inline-flex rounded-lg border border-hairline p-0.5 text-[11px]">
          {tabs.map((t) => (
            <button
              key={t.key}
              role="tab"
              aria-selected={tab === t.key}
              aria-controls={`panel-${t.key}`}
              onClick={() => setTab(t.key)}
              className={`px-3 py-2 min-h-[44px] rounded-md transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 ${tab === t.key ? "bg-accent text-accent-fg" : "text-text-muted hover:text-text-main"}`}
            >
              {t.label} {t.count}
            </button>
          ))}
        </div>
      </div>

      <div className="p-5">
        <div role="tabpanel" id="panel-transit" hidden={tab !== "transit"}>
          {tab === "transit" && <TransitTab citations={data.transit_citations ?? []} prefersReduced={prefersReduced} />}
        </div>
        <div role="tabpanel" id="panel-yoga" hidden={tab !== "yoga"}>
          {tab === "yoga" && <YogaTab citations={data.yoga_citations ?? []} prefersReduced={prefersReduced} />}
        </div>
        <div role="tabpanel" id="panel-god" hidden={tab !== "god"}>
          {tab === "god" && <GodNodeTab insights={data.god_node_insights ?? []} prefersReduced={prefersReduced} />}
        </div>
        <div role="tabpanel" id="panel-conflicts" hidden={tab !== "conflicts"}>
          {tab === "conflicts" && <ConflictTab conflicts={data.text_conflicts ?? []} prefersReduced={prefersReduced} />}
        </div>
      </div>
    </div>
  );
}

function TransitTab({ citations, prefersReduced }: { citations: TransitCitation[]; prefersReduced: boolean | null }) {
  return (
    <div className="grid gap-3">
      {citations.map((c, i) => {
        const effects = c.classical_effects ?? [];
        // Categorize: meaningful effects vs house listing data
        const meaningfulEffects = effects.filter(e => {
          const txt = (e.effect || e.description || "").toLowerCase();
          return !txt.includes("transit houses from moon") 
            && !txt.includes("gochara vedha pairs")
            && !txt.includes("life-area effect");
        });
        const housePills = effects.filter(e => {
          const txt = (e.effect || e.description || "");
          return txt.match(/^\d+(st|nd|rd|th) house from Moon/i);
        });
        const effectDescriptions = effects.filter(e => {
          const txt = (e.effect || e.description || "").toLowerCase();
          return txt.includes("life-area effect") || txt.includes("benefic effect") || txt.includes("malefic effect");
        });
        
        return (
        <motion.div
          key={c.planet}
          initial={prefersReduced ? {} : { opacity: 0, y: 6 }}
          animate={prefersReduced ? {} : { opacity: 1, y: 0 }}
          transition={{ delay: i * 0.04 }}
          className="rounded-xl border border-hairline p-3 hover:bg-[color-mix(in_srgb,var(--color-accent)_3%,transparent)] transition-colors"
        >
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-medium">{c.planet}</span>
            {c.rashi && <span className="text-xs text-text-muted font-mono">in {c.rashi}</span>}
            {c.house_from_janma != null && (
              <span className="text-xs text-text-muted font-mono">· {c.house_from_janma}th from Moon</span>
            )}
            {c.verdict && (
              <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded ${c.verdict === "shubh" ? "bg-success/15 text-success" : c.verdict === "ashubh" ? "bg-danger/15 text-danger" : "bg-warning/15 text-warning"}`}>
                {c.verdict}
              </span>
            )}
          </div>
          {effectDescriptions.length > 0 && (
            <div className="mb-2">
              {effectDescriptions.slice(0, 3).map((e, j) => (
                <p key={j} className="text-xs text-text-muted leading-relaxed">
                  {(e.effect || e.description || "").replace(/Life-area effect: /i, "").replace(/: .*effect: /i, ": ")}
                </p>
              ))}
            </div>
          )}
          <div className="flex flex-wrap gap-1">
            {housePills.slice(0, 4).map((e, j) => (
              <span key={j} className="text-[10px] px-2 py-0.5 rounded-full border border-hairline text-text-muted">
                {e.effect || e.description || ""}
              </span>
            ))}
            {meaningfulEffects.length === 0 && housePills.length === 0 && effects.slice(0, 3).map((e, j) => (
              <span key={j} className="text-[10px] px-2 py-0.5 rounded-full border border-hairline text-text-muted">
                {(e.effect || e.description || "").substring(0, 60)}
              </span>
            ))}
          </div>
          {c.vedha_pairs && (
            <p className="mt-2 text-[11px] text-warning">
              {c.vedha_pairs.split(";")[0]}
            </p>
          )}
        </motion.div>
      )})}
    </div>
  );
}

function YogaTab({ citations, prefersReduced }: { citations: YogaCitation[]; prefersReduced: boolean | null }) {
  return (
    <div className="grid gap-3">
      {citations.map((y, i) => (
        <motion.div
          key={y.yoga ?? i}
          initial={prefersReduced ? {} : { opacity: 0, y: 6 }}
          animate={prefersReduced ? {} : { opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05 }}
          className="rounded-xl border border-hairline p-3"
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium">{y.label ?? y.yoga}</span>
            {y.source_file && (
              <span className="text-[10px] text-text-muted font-mono">{sourceLabel(y.source_file)}</span>
            )}
          </div>
          {(y.required_planets ?? []).length > 0 && (
            <p className="text-xs text-text-muted">
              Requires: {y.required_planets!.join(", ")}
            </p>
          )}
          {(y.hyperedge_groups ?? []).length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {y.hyperedge_groups!.map((hg, j) => (
                <span key={j} className="text-[10px] px-2 py-0.5 rounded-full border border-hairline text-text-muted">
                  {hg.label} ({hg.members.length} members)
                </span>
              ))}
            </div>
          )}
        </motion.div>
      ))}
    </div>
  );
}

function GodNodeTab({ insights, prefersReduced }: { insights: GodNodeInsight[]; prefersReduced: boolean | null }) {
  return (
    <div className="grid gap-2.5 sm:grid-cols-2">
      {insights.map((g, i) => (
        <motion.div
          key={g.god_node}
          initial={prefersReduced ? {} : { opacity: 0, y: 6 }}
          animate={prefersReduced ? {} : { opacity: 1, y: 0 }}
          transition={{ delay: i * 0.04 }}
          className="rounded-xl border border-hairline p-3"
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-sm font-medium truncate">{g.god_node}</span>
            <span className="text-[10px] font-mono text-accent">{g.degree} links</span>
          </div>
          {(g.connected_concepts ?? []).length > 0 && (
            <div className="flex flex-wrap gap-1">
              {g.connected_concepts!.slice(0, 8).map((c, j) => (
                <span key={j} className="text-[10px] px-1.5 py-0.5 rounded bg-[color-mix(in_srgb,var(--color-accent)_8%,transparent)] text-text-muted">
                  {c.length > 40 ? c.slice(0, 40) + "…" : c}
                </span>
              ))}
            </div>
          )}
        </motion.div>
      ))}
    </div>
  );
}

function ConflictTab({ conflicts, prefersReduced }: { conflicts: { source: string; target: string; source_file?: string }[]; prefersReduced: boolean | null }) {
  return (
    <div className="space-y-3">
      <p className="text-xs text-text-muted">
        Known contradictions between classical authorities. The graph tracks these to avoid presenting a single
        dogmatic interpretation where the texts themselves disagree.
      </p>
      {conflicts.map((c, i) => (
        <motion.div
          key={i}
          initial={prefersReduced ? {} : { opacity: 0, y: 6 }}
          animate={prefersReduced ? {} : { opacity: 1, y: 0 }}
          transition={{ delay: i * 0.06 }}
          className="flex items-start gap-3 rounded-xl border border-hairline p-3"
        >
          <span className="text-warning shrink-0 text-sm mt-0.5">⇄</span>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-medium">{c.source}</span>
              <span className="text-[10px] text-warning">vs</span>
              <span className="text-xs font-medium">{c.target}</span>
            </div>
            {c.source_file && (
              <p className="mt-1 text-[10px] text-text-muted">{sourceLabel(c.source_file)}</p>
            )}
          </div>
        </motion.div>
      ))}
    </div>
  );
}
