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
}

export function BookReaderClient({ chapters, fullMarkdown, defaultNodesContent, chapterNodes = {} }: BookReaderClientProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const [activeIdx, setActiveIdx] = useState<number | null>(null);
  const [selectedChapterId, setSelectedChapterId] = useState<string | null>(null);
  const [showFullText, setShowFullText] = useState(true);

  const selectedChapter = selectedChapterId ? chapters.find(c => c.id === selectedChapterId) : null;
  const selectedNodes = selectedChapterId ? (chapterNodes[selectedChapterId] || []) : [];

  const handleChapterClick = (ch: Chapter, idx: number) => {
    setActiveIdx(idx);
    setSelectedChapterId(ch.id);
    // When user explicitly picks a chapter, prefer showing the KG chapter content
    setShowFullText(false);

    // Also attempt scroll in case full text is visible
    scrollToChapterInFullText(ch.title, idx);
  };

  const scrollToChapterInFullText = (title: string, idx: number) => {
    if (!contentRef.current || !fullMarkdown) return;

    const container = contentRef.current;
    const lowerTitle = title.toLowerCase().trim();

    // Build multiple search patterns
    const patterns: string[] = [lowerTitle];
    const nums = title.match(/\d+/g) || [];
    nums.forEach(n => patterns.push(n));
    if (nums.length >= 2) patterns.push(`${nums[0]}-${nums[1]}`);
    const romanMap: Record<string, string> = { '1':'i','2':'ii','3':'iii','4':'iv','5':'v','6':'vi','7':'vii','8':'viii','9':'ix','10':'x','11':'xi','12':'xii','13':'xiii','14':'xiv','15':'xv' };
    nums.forEach(n => { if (romanMap[n]) patterns.push(`chapter ${romanMap[n]}`); });

    const allElements = Array.from(container.querySelectorAll('p, div, pre, h1, h2, h3, h4, span, li'));
    for (const pat of patterns) {
      const match = allElements.find(el => (el.textContent || '').toLowerCase().includes(pat));
      if (match) {
        match.scrollIntoView({ behavior: 'smooth', block: 'center' });
        match.classList.add('!bg-accent/20', 'transition-colors');
        setTimeout(() => match.classList.remove('!bg-accent/20'), 1600);
        return;
      }
    }

    const total = Math.max(1, chapters.length - 1);
    const roughFraction = Math.min(0.95, Math.max(0.05, idx / total));
    const target = roughFraction * (container.scrollHeight - container.clientHeight);
    container.scrollTo({ top: target, behavior: 'smooth' });
  };

  const renderChapterNodes = (nodes: any[], title: string) => {
    if (!nodes || nodes.length === 0) {
      return (
        <div>
          <div className="font-serif text-xl mb-2">{title}</div>
          <p className="text-text-muted">No structured nodes were extracted for this chapter grouping in the Knowledge Graph.</p>
          {fullMarkdown && (
            <button onClick={() => setShowFullText(true)} className="mt-4 text-sm underline text-accent">
              View full original text instead
            </button>
          )}
        </div>
      );
    }
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[10px] uppercase tracking-[3px] text-text-muted">Chapter from Knowledge Graph</div>
            <div className="font-medium text-lg">{title}</div>
          </div>
          {fullMarkdown && (
            <button
              onClick={() => setShowFullText(true)}
              className="text-xs px-3 py-1 rounded border border-hairline hover:bg-surface/60"
            >
              View full source text
            </button>
          )}
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
    // If user selected a specific chapter, show its KG nodes (unless they explicitly want full text)
    if (selectedChapter && !showFullText) {
      return renderChapterNodes(selectedNodes, selectedChapter.title);
    }

    // Default: prefer full original text when available (rich prose)
    if (fullMarkdown) {
      return (
        <div className="prose prose-invert max-w-none text-[15px] leading-relaxed text-text-main/90 whitespace-pre-wrap font-light">
          {fullMarkdown}
        </div>
      );
    }

    // Fallback to the default (all) nodes view passed from server
    return defaultNodesContent;
  };

  return (
    <div className="grid lg:grid-cols-5 gap-6">
      {/* Chapters sidebar */}
      <div className="lg:col-span-2">
        <div className="sticky top-6 rounded-2xl border border-hairline bg-surface p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs uppercase tracking-widest text-text-muted">Chapters (from graph)</div>
            {selectedChapterId && (
              <button
                onClick={() => { setSelectedChapterId(null); setActiveIdx(null); setShowFullText(true); }}
                className="text-[10px] px-2 py-0.5 rounded border border-hairline hover:bg-surface/60"
              >
                Show all
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
                    {ch.nodeIds.length} nodes • {ch.sourceLocation}
                  </div>
                </a>
              ))
            ) : (
              <div className="text-text-muted text-sm">No chapter grouping found. All content in main section.</div>
            )}
          </div>
          <div className="mt-3 text-[10px] text-text-muted">
            Click any chapter to view its Knowledge Graph nodes.
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
        {selectedChapter && showFullText && (
          <div className="mt-2 text-[10px] text-text-muted">
            Full source shown. Click a chapter again to see only that chapter&apos;s extracted nodes.
          </div>
        )}
      </div>
    </div>
  );
}
