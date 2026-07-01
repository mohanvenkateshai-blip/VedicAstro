"use client";

import { useRef, useState, useEffect } from "react";
import { ArrowUp } from "lucide-react";

interface Chapter {
  id: string;
  title: string;
  sourceLocation?: string;
  nodeIds: string[];
  properties?: Record<string, unknown>;
}

export type NodeProvenance = {
  hierarchy_path?: string;
  method?: string;
  confidence?: number;
  chapter_id?: string;
  section_id?: string | null;
};

interface BookReaderClientProps {
  chapters: Chapter[];
  fullMarkdown: string | null;
  defaultNodesContent: React.ReactNode;
  chapterNodes?: Record<string, unknown[]>;
  sections?: { id: string; title: string; content: string }[] | null;
  // Deep link support: auto-activate + scroll on mount
  initialChapter?: string | null;
  initialSection?: string | null;
  // Per-node provenance from the node-chapter-map patch for "Sourced from" UI
  nodeProvenance?: Record<string, NodeProvenance>;
}

export function BookReaderClient({
  chapters,
  fullMarkdown,
  defaultNodesContent,
  chapterNodes = {},
  sections = null,
  initialChapter = null,
  initialSection = null,
  nodeProvenance = {},
}: BookReaderClientProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const [activeIdx, setActiveIdx] = useState<number | null>(null);
  const [selectedChapterId, setSelectedChapterId] = useState<string | null>(null);
  const [visibleChapterId, setVisibleChapterId] = useState<string | null>(null);
  const [showScrollTop, setShowScrollTop] = useState(false);

  const selectedChapter = selectedChapterId ? chapters.find(c => c.id === selectedChapterId) : null;
  const selectedNodes = (selectedChapterId ? (chapterNodes[selectedChapterId] || []) : []) as unknown[];

  const scrollToChapterInFullText = (title: string, idx: number) => {
    if (!contentRef.current) return;

    const container = contentRef.current;
    const lowerTitle = title.toLowerCase().trim();

    const patterns: string[] = [lowerTitle];
    const nums = title.match(/\d+/g) || [];
    nums.forEach((n) => patterns.push(n));
    if (nums.length >= 2) patterns.push(`${nums[0]}-${nums[1]}`);
    const firstNum = nums[0];
    if (firstNum) patterns.push(`${firstNum}.`);

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

    const total = Math.max(1, chapters.length - 1);
    const frac = Math.min(0.92, Math.max(0.04, idx / total));
    container.scrollTo({ top: frac * (container.scrollHeight - container.clientHeight), behavior: "smooth" });
  };

  // Scroll-spy: keep active + visible in sync as user scrolls the content blocks.
  // This powers the mini chapter progress / "reading" breadcrumb.
  useEffect(() => {
    const container = contentRef.current;
    if (!container) return;
    // Observe section/chapter blocks when we have them (from prop or client-sliced fullMarkdown using start_line)
    const blockIds = (sections && sections.length > 0) ? sections.map((s) => s.id) : chapters.map((c) => c.id);
    if (blockIds.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        let best: IntersectionObserverEntry | null = null;
        for (const entry of entries) {
          if (entry.isIntersecting && (!best || (entry.intersectionRatio || 0) > (best.intersectionRatio || 0))) {
            best = entry;
          }
        }
        if (best?.target?.id) {
          const id = best.target.id;
          setVisibleChapterId(id);
          const found = chapters.findIndex((c) => c.id === id);
          if (found >= 0) {
            setActiveIdx(found);
          }
        }
      },
      { root: container, threshold: [0.05, 0.25, 0.5, 0.75] }
    );

    // Observe after paint; the blocks are rendered by mainContent (supports both passed sections and <section id> from slice)
    const raf = requestAnimationFrame(() => {
      blockIds.forEach((id) => {
        const el = document.getElementById(id);
        if (el && container.contains(el)) {
          observer.observe(el);
        }
      });
    });

    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
    };
  }, [sections, chapters, fullMarkdown]);

  // Deep link activation: if initialChapter or initialSection provided, select and scroll to it.
  useEffect(() => {
    const targetId = initialSection || initialChapter;
    if (!targetId) return;
    // Defer to allow sections to paint
    const t = setTimeout(() => {
      const ch = chapters.find((c) => c.id === targetId) || (initialChapter ? chapters.find((c) => c.id === initialChapter) : null);
      if (ch) {
        const idx = chapters.findIndex((c) => c.id === ch.id);
        setActiveIdx(idx >= 0 ? idx : null);
        setSelectedChapterId(ch.id);
        setVisibleChapterId(ch.id);

        const el = document.getElementById(ch.id) || (initialSection ? document.getElementById(initialSection) : null);
        if (el) {
          el.scrollIntoView({ behavior: "smooth", block: "start" });
          el.classList.add("!bg-accent/10", "transition-colors", "rounded-md");
          setTimeout(() => el.classList.remove("!bg-accent/10", "rounded-md"), 1600);
        } else {
          // fall back to fuzzy title match using the title of the target
          scrollToChapterInFullText(ch.title, idx >= 0 ? idx : 0);
        }
      }
    }, 60);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialChapter, initialSection]);

  // FAB: show "scroll to top" button when user has scrolled down the page or the internal reader pane
  useEffect(() => {
    const check = () => {
      const winScrolled = window.scrollY > 400;
      const pane = contentRef.current;
      const paneScrolled = pane ? pane.scrollTop > 300 : false;
      setShowScrollTop(winScrolled || paneScrolled);
    };
    window.addEventListener("scroll", check, { passive: true });
    // also watch the content pane (some books scroll inside this container)
    const pane = contentRef.current;
    if (pane) pane.addEventListener("scroll", check, { passive: true });
    // initial
    check();
    return () => {
      window.removeEventListener("scroll", check);
      if (pane) pane.removeEventListener("scroll", check);
    };
  }, []);

  const handleChapterClick = (ch: Chapter, idx: number) => {
    setActiveIdx(idx);
    setSelectedChapterId(ch.id);
    setVisibleChapterId(ch.id);

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

  // Strip the leading raw heading line from a sliced block so we can show our clean structured title instead.
  // Never strip a leading image line (we want to render media at the top of a chapter/section).
  const getDisplayBody = (content: string, title: string): string => {
    if (!content) return "";
    const lines = content.split("\n");
    const first = (lines[0] || "").trim();
    if (/^!\[/.test(first)) return content; // preserve leading media
    const titleNorm = title.toLowerCase().replace(/[^\w]/g, "").slice(0, 40);
    const firstNorm = first.toLowerCase().replace(/[^\w]/g, "").slice(0, 40);
    const looksLikeHeading = /^(\d+[\.\)]?\s+|#{1,6}\s*)/.test(first) || first.length < 160;
    if (looksLikeHeading && (firstNorm.includes(titleNorm) || titleNorm.includes(firstNorm) || firstNorm.length < 8)) {
      return lines.slice(1).join("\n").trim();
    }
    return content;
  };

  const getNodeProvenance = (node: unknown): NodeProvenance | undefined => {
    if (!node) return undefined;
    const rec = node as Record<string, unknown>;
    if (rec._provenance) return rec._provenance as NodeProvenance;
    const nid = rec.id as string | undefined;
    if (nid && nodeProvenance && nodeProvenance[nid]) return nodeProvenance[nid];
    return undefined;
  };

  // Resolve an image src from prose (or future structured media) to a fetchable URL.
  // - Absolute http(s) and site-absolute "/" paths are used as-is.
  // - Bare or relative paths (e.g. "images/foo.png", "corpus-vault:foo/bar.jpg") are routed
  //   through the corpus asset proxy which returns short-lived signed URLs from corpus-vault.
  const resolveImageSrc = (src: string): string => {
    if (!src) return src;
    if (/^https?:\/\//i.test(src) || src.startsWith("/") || src.startsWith("data:")) return src;
    const clean = src.replace(/^corpus-vault:\/?/i, "").replace(/^\.\/?/, "");
    return `/api/corpus/asset?path=${encodeURIComponent(clean)}`;
  };

  // Lightweight prose + image renderer.
  // Supports standard markdown images: ![alt](src "optional title") inside chapter/section bodies.
  // Text runs are preserved with basic paragraph splitting. No full markdown parser to stay minimal.
  // On image error we show a graceful fallback card (still shows alt/caption + attempted src).
  const renderContentWithMedia = (raw: string, keyPrefix: string): React.ReactNode => {
    if (!raw) return null;
    const imgRe = /!\[([^\]]*)\]\(([^)]+?)(?:\s+"([^"]+)")?\)/g;
    const parts: Array<
      | { type: "text"; text: string }
      | { type: "image"; alt: string; src: string; title?: string }
    > = [];
    let last = 0;
    let m: RegExpExecArray | null;
    // eslint-disable-next-line no-cond-assign
    while ((m = imgRe.exec(raw)) !== null) {
      if (m.index > last) parts.push({ type: "text", text: raw.slice(last, m.index) });
      parts.push({ type: "image", alt: m[1] || "", src: m[2], title: m[3] });
      last = imgRe.lastIndex;
    }
    if (last < raw.length) parts.push({ type: "text", text: raw.slice(last) });

    if (parts.length === 0) {
      return <div className="whitespace-pre-wrap">{raw}</div>;
    }

    return parts.map((p, i) => {
      if (p.type === "text") {
        const t = (p.text || "").trim();
        if (!t) return null;
        return (
          <div key={`${keyPrefix}-t-${i}`} className="whitespace-pre-wrap mb-4 last:mb-0">
            {t}
          </div>
        );
      }
      const resolved = resolveImageSrc(p.src);
      return (
        <figure key={`${keyPrefix}-img-${i}`} className="my-6">
          <img
            src={resolved}
            alt={p.alt}
            className="rounded-xl border border-hairline max-w-full h-auto"
            loading="lazy"
            onError={(e) => {
              const img = e.currentTarget as HTMLImageElement;
              img.style.display = "none";
              const fb = img.nextElementSibling as HTMLElement | null;
              if (fb) fb.style.display = "block";
            }}
          />
          {/* Fallback card (shown via onError) */}
          <div className="hidden mt-2 rounded-lg border border-hairline bg-surface/70 p-3 text-xs text-text-muted">
            Image unavailable
            <div className="mt-0.5 font-mono text-[10px] opacity-70 break-all">{p.src}</div>
          </div>
          {(p.alt || p.title) && (
            <figcaption className="mt-1.5 text-[12px] text-text-muted text-center">
              {p.title || p.alt}
            </figcaption>
          )}
        </figure>
      );
    });
  };

  const renderChapterNodes = (nodes: unknown[], title: string) => {
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
          {/* Show chapter-level From/mapped info if nodeProvenance indicates patch data for it */}
          {(() => {
            const chProv = Object.values(nodeProvenance || {}).find((p: any) => p && (nodes as any[]).some((n: any) => getNodeProvenance(n)?.chapter_id === p.chapter_id)); // eslint-disable-line @typescript-eslint/no-explicit-any
            return chProv?.hierarchy_path ? (
              <div className="text-[10px] text-text-muted mt-0.5">
                From: {chProv.hierarchy_path}
                {chProv.method ? ` (mapped via ${chProv.method}${typeof chProv.confidence === "number" ? ` conf ${chProv.confidence}` : ""})` : ""}
              </div>
            ) : null;
          })()}
        </div>
        {(nodes as any[]).map((node: any, i: number) => { // eslint-disable-line @typescript-eslint/no-explicit-any
          const prov = getNodeProvenance(node);
          return (
            <div key={node.id || i} className="border-l-2 border-accent/40 pl-4">
              {node.source_location && (
                <div className="text-[10px] uppercase tracking-[3px] text-text-muted mb-1">{node.source_location}</div>
              )}
              <div className="font-serif text-xl leading-tight tracking-[-0.3px] text-text-main">
                {node.label || "(no label)"}
              </div>
              {prov?.hierarchy_path && (
                <div className="mt-1 text-[11px] text-accent/90">
                  From: <span className="font-medium">{prov.hierarchy_path}</span>
                  {prov.method ? ` (mapped via ${prov.method}` : ""}
                  {typeof prov.confidence === "number" ? ` conf ${prov.confidence})` : prov.method ? ")" : ""}
                </div>
              )}
              {node.properties && Object.keys(node.properties).length > 0 && (
                <div className="mt-3 text-sm text-text-muted">
                  {Object.entries(node.properties).slice(0, 8).map(([k, v]: [string, any]) => ( // eslint-disable-line @typescript-eslint/no-explicit-any
                    <div key={k} className="mb-1">
                      <span className="font-mono text-xs text-accent">{k}:</span> {typeof v === "string" ? v : JSON.stringify(v)}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  const mainContent = () => {
    // If the user explicitly wants the graph nodes for the selected chapter (rare, via the old path)
    // we still support it, but default experience for full-text books is the readable prose.
    if (selectedChapter && !fullMarkdown) {
      return renderChapterNodes(selectedNodes, selectedChapter.title);
    }

    // Best case: we have parsed sections (from structured line ranges or markdown headings).
    // Render as clean, titled, scroll-targetable chapter/section blocks.
    if (sections && sections.length > 0) {
      const total = sections.length;
      return (
        <>
          {sections.map((sec, i) => {
            const body = getDisplayBody(sec.content, sec.title);
            const isActive = visibleChapterId === sec.id || activeIdx === i;
            const isSection = /-sec-/.test(sec.id) || /^sec-/.test(sec.id);
            const kind = isSection ? "Section" : "Chapter";
            return (
              <div
                key={sec.id}
                id={sec.id}
                className={`mb-8 rounded-2xl border transition-colors scroll-mt-4 ${
                  isActive
                    ? "border-accent/60 bg-[color-mix(in_srgb,var(--color-accent)_6%,transparent)]"
                    : "border-hairline/60 bg-surface/20"
                }`}
              >
                <div className="px-6 pt-5 pb-2 border-b border-hairline/50 flex items-center justify-between">
                  <div>
                    <div className="text-[10px] uppercase tracking-[2.5px] text-accent">{kind} {i + 1} of {total}</div>
                    <div className="font-display text-xl tracking-[-0.3px] leading-tight text-text-main mt-1">
                      {sec.title}
                    </div>
                  </div>
                  <div className="text-[10px] text-text-muted tabular-nums self-start mt-1">{i + 1}/{total}</div>
                </div>
                <div className="px-6 py-5 prose prose-invert max-w-none text-[15px] leading-relaxed text-text-main/90 font-light">
                  {renderContentWithMedia(body || sec.content, sec.id)}
                </div>
              </div>
            );
          })}
        </>
      );
    }

    // Fallback: raw full markdown as one blob (still searchable by the tree walker)
    // But if chapters carry structured start_line, slice fullMarkdown into <section id=...> blocks for reliable id jumps.
    if (fullMarkdown) {
      const hasLineInfo = chapters.some((c) => {
        const p = (c.properties || {}) as any; // eslint-disable-line @typescript-eslint/no-explicit-any
        return typeof p.start_line === "number";
      });
      if (hasLineInfo) {
        const lines = fullMarkdown.split(/\r?\n/);
        const blocks = chapters
          .map((ch) => {
            const p = (ch.properties || {}) as any; // eslint-disable-line @typescript-eslint/no-explicit-any
            const start = typeof p.start_line === "number" ? p.start_line : 0;
            const endEx = typeof p.end_line === "number" ? p.end_line + 1 : lines.length;
            const content = lines.slice(Math.max(0, start), Math.min(lines.length, endEx)).join("\n").trim();
            return { id: ch.id, title: ch.title, content };
          })
          .filter((b) => b.content.length > 0);
        if (blocks.length > 0) {
          const total = blocks.length;
          return (
            <>
              {blocks.map((blk, i) => {
                const body = getDisplayBody(blk.content, blk.title);
                const isActive = visibleChapterId === blk.id || activeIdx === i;
                const chProv = Object.values(nodeProvenance || {}).find((p) => p.chapter_id === blk.id);
                const isSection = /-sec-/.test(blk.id) || /^sec-/.test(blk.id);
                const kind = isSection ? "Section" : "Chapter";
                return (
                  <section
                    key={blk.id}
                    id={blk.id}
                    className={`mb-8 rounded-2xl border transition-colors scroll-mt-4 ${
                      isActive
                        ? "border-accent/60 bg-[color-mix(in_srgb,var(--color-accent)_6%,transparent)]"
                        : "border-hairline/60 bg-surface/20"
                    }`}
                  >
                    <div className="px-6 pt-5 pb-2 border-b border-hairline/50 flex items-center justify-between">
                      <div>
                        <div className="text-[10px] uppercase tracking-[2.5px] text-accent">{kind} {i + 1} of {total}</div>
                        <div className="font-display text-xl tracking-[-0.3px] leading-tight text-text-main mt-1">{blk.title}</div>
                        {chProv?.hierarchy_path && <div className="text-[10px] text-text-muted mt-0.5">From: {chProv.hierarchy_path}</div>}
                        {chProv?.method && (
                          <div className="text-[10px] text-text-muted/80"> (mapped via {chProv.method}{typeof chProv.confidence === "number" ? ` conf ${chProv.confidence}` : ""})</div>
                        )}
                      </div>
                      <div className="text-[10px] text-text-muted tabular-nums self-start mt-1">{i + 1}/{total}</div>
                    </div>
                    <div className="px-6 py-5 prose prose-invert max-w-none text-[15px] leading-relaxed text-text-main/90 font-light">
                      {renderContentWithMedia(body || blk.content, blk.id)}
                    </div>
                  </section>
                );
              })}
            </>
          );
        }
      }
      return (
        <div className="prose prose-invert max-w-none text-[15px] leading-relaxed text-text-main/90 font-light">
          {renderContentWithMedia(fullMarkdown, "raw-full")}
        </div>
      );
    }

    // Pure node-extracted book with no source text
    return defaultNodesContent;
  };

  return (
    <>
      <div className="grid lg:grid-cols-5 gap-6">
      {/* Chapters sidebar */}
      <div className="lg:col-span-2">
        <div className="sticky top-6 rounded-2xl border border-hairline bg-surface p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs uppercase tracking-widest text-text-muted">
              Structured contents
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
              chapters.map((ch, idx) => {
                const level = (ch.properties?.level as number) || 1;
                const isSection = level > 1;
                const indent = Math.min(3, Math.max(0, level - 1)) * 12;
                return (
                  <a
                    key={ch.id}
                    href={`#${ch.id}`}
                    onClick={(e) => {
                      e.preventDefault();
                      handleChapterClick(ch, idx);
                    }}
                    className={`block w-full text-left px-3 py-1.5 rounded-lg border transition no-underline text-inherit ${
                      activeIdx === idx
                        ? "border-accent bg-[color-mix(in_srgb,var(--color-accent)_12%,transparent)]"
                        : "border-hairline/60 hover:border-accent/40 hover:bg-surface/80"
                    }`}
                    style={{ paddingLeft: indent ? `${12 + indent}px` : undefined }}
                  >
                    <div className={`font-medium flex items-center gap-1.5 ${isSection ? "text-[13px]" : ""}`}>
                      {Boolean((ch.properties as Record<string, unknown> | undefined)?.structured) && (
                        <span className="inline-block h-1 w-1 rounded-full bg-accent" aria-hidden="true" />
                      )}
                      {ch.title}
                    </div>
                    <div className="text-[10px] text-text-muted">
                      {ch.properties?.structured ? "Structured • " : ""}
                      {ch.nodeIds && ch.nodeIds.length > 0 ? `${ch.nodeIds.length} nodes` : null}
                      {ch.sourceLocation ? ` • ${ch.sourceLocation}` : ""}
                    </div>
                    {(() => {
                      const chProv = Object.values(nodeProvenance || {}).find((p: any) => p?.chapter_id === ch.id);
                      return chProv?.hierarchy_path ? (
                        <div className="text-[9px] text-text-muted/70 truncate mt-0.5">From: {chProv.hierarchy_path}</div>
                      ) : null;
                    })()}
                  </a>
                );
              })
            ) : (
              <div className="text-text-muted text-sm">No chapter grouping found. All content in main section.</div>
            )}
          </div>
          <div className="mt-3 text-[10px] text-text-muted">
            Click a chapter to jump + highlight the exact block on the right.
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="lg:col-span-3">
        <div
          ref={contentRef}
          className="rounded-3xl border border-hairline bg-surface p-8 min-h-[420px] overflow-auto relative"
        >
          {/* Mini chapter progress / breadcrumb (visible when we have split structured sections) */}
          {sections && sections.length > 0 && (
            <div className="sticky top-0 z-10 -mx-2 mb-4 -mt-2 rounded-t-3xl bg-surface/95 backdrop-blur border-b border-hairline px-3 py-2 text-[11px] flex items-center justify-between">
              <div className="flex items-center gap-2 text-text-muted">
                <span className="uppercase tracking-widest">Reading</span>
                {(() => {
                  const idx = activeIdx != null ? activeIdx : (visibleChapterId ? chapters.findIndex(c => c.id === visibleChapterId) : -1);
                  const ch = idx >= 0 ? chapters[idx] : null;
                  if (ch) {
                    const isSec = /-sec-/.test(ch.id) || /^sec-/.test(ch.id) || ((ch.properties?.level as number) || 1) > 1;
                    const kind = isSec ? "Section" : "Chapter";
                    const bp = Object.values(nodeProvenance || {}).find((p: any) => p?.chapter_id === ch.id);
                    const mapNote = bp?.method ? ` (mapped via ${bp.method}${typeof bp.confidence === "number" ? ` conf ${bp.confidence}` : ""})` : "";
                    return (
                      <>
                        <span className="text-accent font-medium truncate max-w-[28ch]">{ch.title}{mapNote}</span>
                        <span className="tabular-nums text-text-muted/70">· {kind.toLowerCase()} {idx + 1} / {chapters.length}</span>
                      </>
                    );
                  }
                  return <span className="text-text-muted/70">—</span>;
                })()}
              </div>
              {activeIdx != null && (
                <button
                  onClick={() => { setActiveIdx(null); setSelectedChapterId(null); setVisibleChapterId(null); contentRef.current?.scrollTo({ top: 0, behavior: "smooth" }); }}
                  className="text-[10px] px-2 py-0.5 rounded border border-hairline hover:bg-surface/60"
                >
                  Top
                </button>
              )}
            </div>
          )}
          {mainContent()}
        </div>
        {selectedChapter && fullMarkdown && (
          <div className="mt-2 text-[10px] text-text-muted">
            Full source text (images supported). The left list jumps inside this document.
          </div>
        )}
        {sections && sections.length > 0 && (
          <div className="mt-2 text-[10px] text-text-muted">
            Full chapter content (via structured ranges) or focused sections. Images in prose render with corpus-vault / local fallbacks.
          </div>
        )}
      </div>
      </div>

      {/* Floating Action Button: scroll to top of page */}
      {showScrollTop && (
        <button
          onClick={() => {
            // Scroll the internal content container if present (used by the reader)
            if (contentRef.current) {
              contentRef.current.scrollTo({ top: 0, behavior: "smooth" });
            }
            // Also scroll the window (for full page scroll cases)
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
          className="fixed bottom-6 right-6 z-[60] flex h-11 w-11 items-center justify-center rounded-full border border-hairline bg-card text-accent transition-all hover:bg-accent hover:text-white focus:outline-none focus:ring-2 focus:ring-accent/60"
          aria-label="Scroll to top"
        >
          <ArrowUp className="h-5 w-5" />
        </button>
      )}
    </>
  );
}
