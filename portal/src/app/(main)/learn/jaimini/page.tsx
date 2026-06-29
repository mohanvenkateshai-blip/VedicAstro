"use client";

import { useEffect, useState } from "react";
import { BookOpen, ArrowLeft, ArrowRight } from "lucide-react";
import { getBookTextNodes, DEFAULT_GRAPH_VERSION } from "@/lib/corpus";

type TextNode = {
  id: string;
  label: string | null;
  source_location: string | null;
  properties: Record<string, unknown>;
};

const FALLBACK_SUTRAS: TextNode[] = [
  {
    id: "j1.1.1",
    label: "ॐ अथातः परं ज्योतिषम्",
    source_location: "Ch.1 · Sutra 1",
    properties: { translation: "Now, therefore, the supreme science of light (Jyotisha)." },
  },
  {
    id: "j1.1.2",
    label: "तस्य ज्ञानं व्याख्यास्यामः",
    source_location: "Ch.1 · Sutra 2",
    properties: { translation: "We shall now explain its knowledge." },
  },
  {
    id: "j1.1.3",
    label: "लग्नाद् द्वादशभावानां फलानि वक्ष्यामि",
    source_location: "Ch.1 · Sutra 3",
    properties: { translation: "From the Lagna I shall declare the results of the twelve houses." },
  },
];

// Candidate source_file names that may exist under newbooks-v1 in corpus_sources / graph_nodes
const JAIMINI_CANDIDATES = [
  "Jaimini_Sutras.md",
  "Jaimini Sutras.md",
  "jaimini_sutras.md",
  "Jaimini.md",
  "jaimini.md",
];

export default function JaiminiSutrasPage() {
  const [nodes, setNodes] = useState<TextNode[]>(FALLBACK_SUTRAS);
  const [activeIndex, setActiveIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [source, setSource] = useState<string>("(searching...)");
  const [usedVersion, setUsedVersion] = useState<string>(DEFAULT_GRAPH_VERSION);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        for (const candidate of JAIMINI_CANDIDATES) {
          try {
            const data = await getBookTextNodes(candidate);
            if (data && data.length > 0) {
              setNodes(data as TextNode[]);
              setSource(candidate);
              setUsedVersion(DEFAULT_GRAPH_VERSION);
              return;
            }
          } catch {
            // try next candidate
          }
        }
        // nothing found — keep fallback, record attempted source
        setSource(JAIMINI_CANDIDATES[0]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const active = nodes[activeIndex] ?? nodes[0];
  const hasRealData = nodes.length > 0 && nodes[0]?.id !== FALLBACK_SUTRAS[0]?.id;

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
        <a href="/learn/nakshatras" className="text-sm text-text-muted hover:text-text-main transition-colors">
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
                  Using curated excerpt. Real nodes for Jaimini will appear when the source file is present under graph_version={usedVersion} in Supabase graph_nodes.
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
