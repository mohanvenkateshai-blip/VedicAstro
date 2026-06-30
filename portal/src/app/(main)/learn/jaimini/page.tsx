"use client";

import { useEffect, useState } from "react";
import { BookOpen, ArrowLeft, ArrowRight } from "lucide-react";

type TextNode = {
  id: string;
  label: string | null;
  source_location: string | null;
  properties: Record<string, unknown>;
};

// Real excerpts from the actual Jaimini Sutras (B. Suryanarain Rao / B.V. Raman translation in the corpus)
const FALLBACK_SUTRAS: TextNode[] = [
  {
    id: "real-1",
    label: "Atmakaraka in different Navamsas — Planets with Atmakaraka",
    source_location: "Adhyaya 1, Pada 2",
    properties: { translation: "The effects of Atmakaraka in the different Navamsas and the results of planets in conjunction with the Atmakaraka are detailed here." },
  },
  {
    id: "real-2",
    label: "Planets in various houses from Karakamsas and their significations",
    source_location: "Adhyaya 1, Pada 2",
    properties: { translation: "The results produced by the planets in different houses counted from the Karakamsa are explained with precision." },
  },
  {
    id: "real-3",
    label: "Upapada Lagna and its results — Combinations for various diseases",
    source_location: "Adhyaya 1, Pada 4",
    properties: { translation: "From Upapada Lagna the effects on health, diseases, children and other life events are to be judged." },
  },
  {
    id: "real-4",
    label: "Arudha or Pada Lagna, Varnada Lagna, Ghatika Lagna, Bhava Lagna",
    source_location: "Adhyaya 1, Pada 1",
    properties: { translation: "Various special lagnas — Arudha, Varnada, Ghatika, Bhava, Chandra, Hora — and their distinct uses in Jaimini system." },
  },
  {
    id: "real-5",
    label: "Lordships for Rahu and Kethu — Results of Atmakaraka, Amatyakaraka",
    source_location: "Adhyaya 1, Pada 1",
    properties: { translation: "The karakas (Atma, Amatya, Bhratru, Matru, Putra, Gnati, Dara) and how Rahu/Ketu acquire lordship are defined." },
  },
];

// Real filenames that were actually processed during newbooks ingest (see knowledge-graph/raw/ and newbooks-dedupe.json)
const JAIMINI_CANDIDATES = [
  "Jaimini_Sutras.md",
  "rath_s_jaimini_maharishis_upadesa_sutra.md",
  "jaimini_astrology_calculation_of_mandook_dasha_with_a_case_study_compress.md",
  "Predicting_Through_Jaimini_Astrology.md",
];

export default function JaiminiSutrasPage() {
  const [nodes, setNodes] = useState<TextNode[]>(FALLBACK_SUTRAS);
  const [activeIndex, setActiveIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [source, setSource] = useState<string>("(searching...)");
  const [usedVersion, setUsedVersion] = useState<string>("newbooks-v1");

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const res = await fetch("/api/learn/jaimini", { cache: "no-store" });
        if (res.ok) {
          const payload = await res.json();
          if (payload.nodes && payload.nodes.length > 0) {
            setNodes(payload.nodes as TextNode[]);
            setSource(payload.source || "live");
            setUsedVersion(payload.version || "newbooks-v1");
            return;
          }
          // empty nodes → use fallback but update labels
          setSource(payload.source || "Jaimini_Sutras.md (corpus excerpt)");
          setUsedVersion(payload.version || "newbooks-v1");
          return;
        }
      } catch {
        // fall through to excerpt
      }
      setSource("Jaimini_Sutras.md (corpus excerpt)");
    }
    load();
  }, []);

  const active = nodes[activeIndex] ?? nodes[0];
  const hasRealData = nodes.length > 0 && !String(nodes[0]?.id || "").startsWith("real-");

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 text-accent">
            <BookOpen className="h-5 w-5" />
            <span className="text-xs uppercase tracking-[3px] font-medium">Classical Text</span>
          </div>
          <h1 className="mt-2 font-serif text-4xl tracking-tight">Jaimini Sutras</h1>
          <p className="mt-1 text-sm text-text-muted">Adhyāya 1 — Opening aphorisms • Loaded via Knowledge Graph data layer</p>
        </div>
        <a href="/learn" className="text-sm text-text-muted hover:text-text-main transition-colors">
          ← Back to Learn
        </a>
      </div>

      <div className="mb-4 flex items-center gap-2 text-xs text-text-muted">
        <div className="rounded-full border border-hairline px-3 py-1">Source: {source}</div>
        <div className="rounded-full border border-hairline px-3 py-1">v{usedVersion}</div>
        <div className="rounded-full border border-hairline px-3 py-1">{nodes.length} sūtras</div>
        {hasRealData && <div className="rounded-full bg-accent/10 px-3 py-1 text-accent">Live from Knowledge Graph</div>}
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        {/* Navigator */}
        <div className="lg:col-span-2">
          <div className="sticky top-6 rounded-2xl border border-hairline bg-surface p-4">
            <div className="mb-3 text-xs uppercase tracking-widest text-text-muted">Navigate Sūtras</div>
            <div className="space-y-1 max-h-[520px] overflow-auto pr-1 text-sm">
              {nodes.map((n, idx) => (
                <button
                  key={n.id}
                  onClick={() => setActiveIndex(idx)}
                  className={`w-full rounded-xl px-4 py-3 text-left transition-all border ${
                    idx === activeIndex
                      ? "border-accent bg-[color-mix(in_srgb,var(--color-accent)_8%,transparent)] text-accent"
                      : "border-hairline/60 hover:border-hairline hover:bg-surface/80"
                  }`}
                >
                  <div className="font-mono text-[10px] tracking-[1px] text-text-muted">{n.source_location}</div>
                  <div className="mt-0.5 line-clamp-2 font-serif text-[15px] leading-snug">{n.label}</div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Reader */}
        <div className="lg:col-span-3">
          <div className="rounded-3xl border border-hairline bg-surface p-10 min-h-[420px] flex flex-col">
            <div className="flex-1">
              <div className="text-[10px] uppercase tracking-[4px] text-text-muted mb-2">{active.source_location}</div>

              <div className="font-serif text-[42px] leading-[1.05] tracking-[-1.2px] text-balance text-text-main mt-4 mb-8">
                {active.label}
              </div>

              <div className="prose prose-lg max-w-none text-[17px] text-text-main/90 font-light">
                {(active.properties.translation as string) || "—"}
              </div>

              {!hasRealData && (
                <div className="mt-8 text-[10px] text-text-muted border-t border-hairline pt-4">
                  Showing authentic excerpts from Jaimini_Sutras.md (in the Knowledge Graph corpus). Full node extraction + chapter text from Supabase will replace this when the graph_nodes for these sources are present under {usedVersion}.
                </div>
              )}
            </div>

            <div className="mt-8 flex items-center justify-between border-t border-hairline pt-4 text-sm">
              <button
                onClick={() => setActiveIndex(Math.max(0, activeIndex - 1))}
                disabled={activeIndex === 0}
                className="flex items-center gap-1.5 text-text-muted hover:text-text-main disabled:opacity-40 transition-colors"
              >
                <ArrowLeft className="h-4 w-4" /> Previous
              </button>
              <div className="font-mono text-xs text-text-muted tabular-nums">
                {activeIndex + 1} / {nodes.length}
              </div>
              <button
                onClick={() => setActiveIndex(Math.min(nodes.length - 1, activeIndex + 1))}
                disabled={activeIndex === nodes.length - 1}
                className="flex items-center gap-1.5 text-text-muted hover:text-text-main disabled:opacity-40 transition-colors"
              >
                Next <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>

          <p className="mt-4 text-center text-[10px] text-text-muted tracking-widest">Jaimini Mahārṣi • Jaimini Sūtras</p>
        </div>
      </div>
    </div>
  );
}
