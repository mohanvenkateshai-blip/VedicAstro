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
  nodesContent: React.ReactNode; // fallback when no full markdown
}

export function BookReaderClient({ chapters, fullMarkdown, nodesContent }: BookReaderClientProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const [activeIdx, setActiveIdx] = useState<number | null>(null);

  const scrollToChapter = (title: string, idx: number) => {
    if (!contentRef.current) return;

    setActiveIdx(idx);

    const container = contentRef.current;
    const lowerTitle = title.toLowerCase().trim();

    // 1. Try precise text match first (for when titles appear in content)
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
    let node;
    while ((node = walker.nextNode())) {
      const text = (node.textContent || "").toLowerCase().trim();
      if (text.includes(lowerTitle) || lowerTitle.includes(text) || lowerTitle.split(/[\s,-]+/).some(part => text.includes(part))) {
        const el = node.nodeType === 3 ? node.parentElement : (node as Element);
        if (el) {
          el.scrollIntoView({ behavior: "smooth", block: "center" });
          el.classList.add("!bg-accent/20", "transition-colors");
          setTimeout(() => el.classList.remove("!bg-accent/20"), 1500);
          return;
        }
      }
    }

    // 2. Reliable fallback: scroll proportionally based on chapter index
    // This guarantees visible movement even for page-based or verse-based extractions
    if (chapters.length > 1) {
      const scrollableHeight = container.scrollHeight - container.clientHeight;
      const target = Math.max(0, Math.min(scrollableHeight, (idx / (chapters.length - 1)) * scrollableHeight));
      container.scrollTo({ top: target, behavior: "smooth" });
    } else {
      container.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  return (
    <div className="grid lg:grid-cols-5 gap-6">
      {/* Chapters sidebar */}
      <div className="lg:col-span-2">
        <div className="sticky top-6 rounded-2xl border border-hairline bg-surface p-4">
          <div className="text-xs uppercase tracking-widest text-text-muted mb-3">Chapters (from graph)</div>
          <div className="space-y-1 text-sm max-h-[60vh] overflow-auto">
            {chapters.length > 0 ? (
              chapters.map((ch, idx) => (
                <a
                  key={ch.id}
                  href={`#ch-${idx}`}
                  onClick={(e) => {
                    e.preventDefault();
                    scrollToChapter(ch.title, idx);
                  }}
                  className={`block w-full text-left px-3 py-2 rounded-lg border transition no-underline text-inherit ${
                    activeIdx === idx
                      ? "border-accent bg-[color-mix(in_srgb,var(--color-accent)_12%,transparent)]"
                      : "border-hairline/60 hover:border-accent/40 hover:bg-surface/80"
                  }`}
                >
                  <div className="font-medium">{ch.title}</div>
                  <div className="text-[10px] text-text-muted">
                    {ch.nodeIds.length} nodes • {ch.sourceLocation}
                  </div>
                </a>
              ))
            ) : (
              <div className="text-text-muted text-sm">No chapter grouping found. All content in main section.</div>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="lg:col-span-3">
        <div
          ref={contentRef}
          className="rounded-3xl border border-hairline bg-surface p-8 min-h-[420px] overflow-auto"
        >
          {fullMarkdown ? (
            <div className="prose prose-invert max-w-none text-[15px] leading-relaxed text-text-main/90 whitespace-pre-wrap font-light">
              {fullMarkdown}
            </div>
          ) : (
            nodesContent
          )}
        </div>
      </div>
    </div>
  );
}
