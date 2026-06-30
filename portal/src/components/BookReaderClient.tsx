"use client";

import { useRef } from "react";

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

  const scrollToChapter = (title: string) => {
    if (!contentRef.current) return;

    // Try to find a heading or text that matches the chapter title
    const container = contentRef.current;
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
    let node;
    const lowerTitle = title.toLowerCase();

    while ((node = walker.nextNode())) {
      const text = (node.textContent || "").toLowerCase();
      if (text.includes(lowerTitle) || lowerTitle.includes(text.trim())) {
        const element = node.nodeType === 3 ? node.parentElement : (node as Element);
        if (element) {
          element.scrollIntoView({ behavior: "smooth", block: "start" });
          // brief highlight
          element.classList.add("!bg-accent/10");
          setTimeout(() => element.classList.remove("!bg-accent/10"), 1200);
          return;
        }
      }
    }

    // Fallback: scroll to top of content
    container.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="grid lg:grid-cols-5 gap-6">
      {/* Chapters sidebar */}
      <div className="lg:col-span-2">
        <div className="sticky top-6 rounded-2xl border border-hairline bg-surface p-4">
          <div className="text-xs uppercase tracking-widest text-text-muted mb-3">Chapters (from graph)</div>
          <div className="space-y-1 text-sm max-h-[60vh] overflow-auto">
            {chapters.length > 0 ? (
              chapters.map((ch, idx) => {
                const slug = ch.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
                return (
                  <a
                    key={ch.id}
                    href={`#ch-${idx}`}
                    onClick={(e) => {
                      e.preventDefault();
                      scrollToChapter(ch.title);
                    }}
                    className="block w-full text-left px-3 py-2 rounded-lg border border-hairline/60 hover:border-accent/40 hover:bg-surface/80 transition no-underline text-inherit"
                  >
                    <div className="font-medium">{ch.title}</div>
                    <div className="text-[10px] text-text-muted">
                      {ch.nodeIds.length} nodes • {ch.sourceLocation}
                    </div>
                  </a>
                );
              })
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
