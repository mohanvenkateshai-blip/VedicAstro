"use client";

import { useRef, useState } from "react";

interface Chapter {
  id: string;
  title: string;
  sourceLocation?: string;
  nodeIds: string[];
}

interface BookReaderClientProps {
  chapters: Chapter[];
  fullMarkdown: string | null;
  defaultNodesContent: React.ReactNode; // shown when no chapter selected or no full text
  chapterNodes?: Record<string, any[]>; // chapterId -> nodes for that chapter
  sections?: { id: string; title: string; content: string }[] | null; // structured full-text sections for reliable jump nav
}

export function BookReaderClient({ chapters, fullMarkdown, defaultNodesContent, chapterNodes = {}, sections = null }: BookReaderClientProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const [activeIdx, setActiveIdx] = useState<number | null>(null);
  const [selectedChapterId, setSelectedChapterId] = useState<string | null>(null);

  const selectedChapter = selectedChapterId ? chapters.find(c => c.id === selectedChapterId) : null;
  const selectedNodes = selectedChapterId ? (chapterNodes[selectedChapterId] || []) : [];

  const handleChapterClick = (ch: Chapter, idx: number) => {
    setActiveIdx(idx);
    setSelectedChapterId(ch.id);

    // Primary behavior: scroll inside the readable full text to the matching section.
    // We use stable element ids when we have parsed sections (best case).
    if (contentRef.current) {
      const byId = document.getElementById(ch.id);
      if (byId) {
        byId.scrollIntoView({ behavior: "smooth", block: "start" });
        byId.classList.add("!bg-accent/10", "transition-colors", "rounded-md");
        setTimeout(() => byId.classList.remove("!bg-accent/10", "rounded-md"), 1600);
        return;
      }
    }

    // Fallback for raw full text or node-only books
    scrollToChapterInFullText(ch.title, idx);
  };

  const scrollToChapterInFullText = (title: string, idx: number) => {
    if (!contentRef.current) return;

    const container = contentRef.current;
    const lowerTitle = title.toLowerCase().trim();

    // Multiple patterns, including the raw title, numbers, and "1. Foo" style
    const patterns: string[] = [lowerTitle];
    const nums = title.match(/\d+/g) || [];
    nums.forEach((n) => patterns.push(n));
    if (nums.length >= 2) patterns.push(`${nums[0]}-${nums[1]}`);
    // Try to match leading "1." or the whole "1. Foundations..."
    const firstNum = nums[0];
    if (firstNum) patterns.push(`${firstNum}.`);

    // Walk all text nodes directly (works even when content is one big pre-wrap blob)
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
    let node: Node | null;
    while ((node = walker.nextNode())) {
      const txt = (node.textContent || "").toLowerCase();
      for (const p of patterns) {
        if (p && txt.includes(p)) {
          const el = node.parentElement;
          if (el) {
            el.scrollIntoView({ behavior: "smooth", block: "center" });
            el.classList.add("!bg-accent/20", "transition-colors");
            setTimeout(() => el.classList.remove("!bg-accent/20"), 1500);
            return;
          }
        }
      }
    }

    // Last resort: visible movement so it never feels completely dead
    const total = Math.max(1, chapters.length - 1);
    const frac = Math.min(0.92, Math.max(0.04, idx / total));
    container.scrollTo({ top: frac * (container.scrollHeight - container.clientHeight), behavior: "smooth" });
  };

  const renderChapterNodes = (nodes: any[], title: string) => {
    if (!nodes || nodes.length === 0) {
      return (
        <div>
          <div className="font-serif text-xl mb-2">{title}</div>
          <p className="text-text-muted">No structured nodes were extracted for this chapter grouping in the Knowledge Graph.</p>
        </div>
      );
    }
    return (
      <div className="space-y-6">
        <div>
          <div className="text-[10px] uppercase tracking-[3px] text-text-muted">Chapter from Knowledge Graph</div>
          <div className="font-medium text-lg">{title}</div>
        </div>
        {nodes.map((node: any, i: number) => (
          <div key={node.id || i} className="border-l-2 border-accent/40 pl-4">
            {node.source_location && (
              <div className="text-[10px] uppercase tracking-[3px] text-text-muted mb-1">{node.source_location}</div>
            )}
            <div className="font-serif text-xl leading-tight tracking-[-0.3px] text-text-main">
              {node.label || "(no label)"}
            </div>
            {node.properties && Object.keys(node.properties).length > 0 && (
              <div className="mt-3 text-sm text-text-muted">
                {Object.entries(node.properties).slice(0, 8).map(([k, v]: [string, any]) => (
                  <div key={k} className="mb-1">
                    <span className="font-mono text-xs text-accent">{k}:</span> {typeof v === "string" ? v : JSON.stringify(v)}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  const mainContent = () => {
    // If the user explicitly wants the graph nodes for the selected chapter (rare, via the old path)
    // we still support it, but default experience for full-text books is the readable prose.
    if (selectedChapter && !fullMarkdown) {
      return renderChapterNodes(selectedNodes, selectedChapter.title);
    }

    // Best case: we have parsed sections with stable ids → render blocks that are directly targetable by id.
    // This is what makes "click the chapter name on the left" actually land on the right content.
    if (sections && sections.length > 0) {
      return (
        <>
          {sections.map((sec) => (
            <div
              key={sec.id}
              id={sec.id}
              className="mb-6 prose prose-invert max-w-none text-[15px] leading-relaxed text-text-main/90 whitespace-pre-wrap font-light"
            >
              {sec.content}
            </div>
          ))}
        </>
      );
    }

    // Fallback: raw full markdown as one blob (still searchable by the tree walker)
    if (fullMarkdown) {
      return (
        <div className="prose prose-invert max-w-none text-[15px] leading-relaxed text-text-main/90 whitespace-pre-wrap font-light">
          {fullMarkdown}
        </div>
      );
    }

    // Pure node-extracted book with no source text
    return defaultNodesContent;
  };

  return (
    <div className="grid lg:grid-cols-5 gap-6">
      {/* Chapters sidebar */}
      <div className="lg:col-span-2">
        <div className="sticky top-6 rounded-2xl border border-hairline bg-surface p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs uppercase tracking-widest text-text-muted">
              {fullMarkdown || sections ? "Contents" : "Chapters (from graph)"}
            </div>
            {selectedChapterId && (
              <button
                onClick={() => { setSelectedChapterId(null); setActiveIdx(null); }}
                className="text-[10px] px-2 py-0.5 rounded border border-hairline hover:bg-surface/60"
              >
                Top
              </button>
            )}
          </div>
          <div className="space-y-1 text-sm max-h-[60vh] overflow-auto">
            {chapters.length > 0 ? (
              chapters.map((ch, idx) => (
                <a
                  key={ch.id}
                  href={`#ch-${idx}`}
                  onClick={(e) => {
                    e.preventDefault();
                    handleChapterClick(ch, idx);
                  }}
                  className={`block w-full text-left px-3 py-2 rounded-lg border transition no-underline text-inherit ${
                    activeIdx === idx
                      ? "border-accent bg-[color-mix(in_srgb,var(--color-accent)_12%,transparent)]"
                      : "border-hairline/60 hover:border-accent/40 hover:bg-surface/80"
                  }`}
                >
                  <div className="font-medium">{ch.title}</div>
                  <div className="text-[10px] text-text-muted">
                    {ch.nodeIds.length > 0 ? `${ch.nodeIds.length} nodes` : null}
                    {ch.nodeIds.length > 0 && ch.sourceLocation ? " • " : null}
                    {ch.sourceLocation}
                  </div>
                </a>
              ))
            ) : (
              <div className="text-text-muted text-sm">No chapter grouping found. All content in main section.</div>
            )}
          </div>
          <div className="mt-3 text-[10px] text-text-muted">
            Click a section to jump to it in the text.
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="lg:col-span-3">
        <div
          ref={contentRef}
          className="rounded-3xl border border-hairline bg-surface p-8 min-h-[420px] overflow-auto"
        >
          {mainContent()}
        </div>
        {selectedChapter && fullMarkdown && (
          <div className="mt-2 text-[10px] text-text-muted">
            Full source text. The left list jumps inside this document.
          </div>
        )}
      </div>
    </div>
  );
}
