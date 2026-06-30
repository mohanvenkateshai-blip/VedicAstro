"use client";

import { useEffect, useState } from "react";
import { BookOpen, ArrowLeft, ArrowRight } from "lucide-react";

type TextNode = {
  id: string;
  label: string | null;
  source_location: string | null;
  properties: Record<string, unknown>;
};

export default function JaiminiSutrasPage() {
  const [nodes, setNodes] = useState<TextNode[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [source, setSource] = useState<string>("loading...");

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const res = await fetch("/api/learn/jaimini", { cache: "no-store" });
        if (res.ok) {
          const payload = await res.json();
          if (payload.nodes && payload.nodes.length > 0) {
            setNodes(payload.nodes);
            setSource(payload.source || "Knowledge Graph");
            setLoading(false);
            return;
          }
        }
      } catch {
        // ignore
      }
      setNodes([]);
      setSource("no real nodes returned");
      setLoading(false);
    }
    load();
  }, []);

  const active = nodes[activeIndex] ?? null;

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 text-accent">
            <BookOpen className="h-5 w-5" />
            <span className="text-xs uppercase tracking-[3px] font-medium">Classical Text • Direct from Knowledge Graph</span>
          </div>
          <h1 className="mt-2 font-serif text-4xl tracking-tight">Jaimini Sūtras</h1>
          <p className="mt-1 text-sm text-text-muted">
            Nodes loaded live from the Knowledge Graph. No fake fallbacks.
          </p>
        </div>
        <a href="/learn" className="text-sm text-text-muted hover:text-text-main transition-colors">
          ← Back to all texts
        </a>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2 text-xs text-text-muted">
        <div className="rounded-full border border-hairline px-3 py-1">Source: {source}</div>
        <div className="rounded-full border border-hairline px-3 py-1">newbooks-v1</div>
        <div className="rounded-full border border-hairline px-3 py-1">{nodes.length} nodes</div>
      </div>

      {loading && <div className="text-text-muted">Loading from Knowledge Graph...</div>}

      {!loading && nodes.length === 0 && (
        <div className="rounded-2xl border border-hairline bg-surface p-8 text-text-muted">
          No usable Jaimini nodes were returned by the graph for the core sources.
          This is the current state of the extraction in the Knowledge Graph.
        </div>
      )}

      {nodes.length > 0 && (
        <div className="grid gap-6 lg:grid-cols-5">
          <div className="lg:col-span-2">
            <div className="sticky top-6 rounded-2xl border border-hairline bg-surface p-4 max-h-[70vh] overflow-auto">
              <div className="mb-2 text-[10px] uppercase tracking-widest text-text-muted">Nodes</div>
              {nodes.map((n, idx) => (
                <button
                  key={n.id}
                  onClick={() => setActiveIndex(idx)}
                  className={`block w-full text-left mb-1 rounded-xl border px-3 py-2 text-sm transition ${
                    idx === activeIndex ? "border-accent bg-accent/5 text-accent" : "border-hairline/60 hover:border-hairline"
                  }`}
                >
                  <div className="font-mono text-[10px] text-text-muted">{n.source_location || ""}</div>
                  <div className="line-clamp-2">{n.label || "(no label)"}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="lg:col-span-3">
            <div className="rounded-3xl border border-hairline bg-surface p-10 min-h-[420px]">
              {active ? (
                <>
                  <div className="text-[10px] uppercase tracking-[3px] text-text-muted mb-1">{active.source_location}</div>
                  <div className="font-serif text-3xl leading-tight tracking-[-0.5px] mt-3 mb-6">
                    {active.label || "(empty label in node)"}
                  </div>

                  {active.properties && Object.keys(active.properties).length > 0 && (
                    <div className="mt-6 text-sm border-t border-hairline pt-4 text-text-muted">
                      {Object.entries(active.properties).map(([k, v]) => (
                        <div key={k} className="mb-1">
                          <span className="font-mono text-xs text-accent">{k}:</span> {String(v)}
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="mt-8 text-[11px] text-text-muted">
                    Exact content from the Knowledge Graph node. If this looks thin or page-based, that is what was extracted and stored.
                  </div>
                </>
              ) : (
                <div>Select a node.</div>
              )}
            </div>

            <div className="mt-4 flex items-center justify-between text-sm text-text-muted">
              <button onClick={() => setActiveIndex(Math.max(0, activeIndex - 1))} disabled={activeIndex === 0} className="flex items-center gap-1 disabled:opacity-40">
                <ArrowLeft className="h-4 w-4" /> Previous
              </button>
              <div>{activeIndex + 1} / {nodes.length}</div>
              <button onClick={() => setActiveIndex(Math.min(nodes.length - 1, activeIndex + 1))} disabled={activeIndex === nodes.length - 1} className="flex items-center gap-1 disabled:opacity-40">
                Next <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
