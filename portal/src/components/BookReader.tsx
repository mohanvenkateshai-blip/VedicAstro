"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, BookOpen } from "lucide-react";
import { Card } from "@/components/ui/Card";

interface Artifact {
  type: "image";
  src: string;
  alt: string;
  caption?: string;
}

interface Chapter {
  id: string;
  title: string;
  body: React.ReactNode;
  artifacts?: Artifact[];
}

interface BookReaderProps {
  bookTitle: string;
  chapters: Chapter[];
  className?: string;
}

export function BookReader({ bookTitle, chapters, className }: BookReaderProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const currentChapter = chapters[currentIndex];

  const goTo = (index: number) => {
    if (index >= 0 && index < chapters.length) {
      setCurrentIndex(index);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const prev = () => goTo(currentIndex - 1);
  const next = () => goTo(currentIndex + 1);

  if (!currentChapter) return null;

  return (
    <div className={`flex flex-col lg:flex-row gap-8 lg:gap-12 ${className ?? ""}`}>
      {/* Table of Contents */}
      <aside className="lg:w-72 lg:shrink-0 lg:sticky lg:top-8 self-start">
        <div className="flex items-center gap-2 mb-4 text-text-muted">
          <BookOpen className="w-4 h-4" />
          <span className="font-mono text-xs uppercase tracking-[0.14em]">Contents</span>
        </div>

        <nav className="space-y-px">
          {chapters.map((chapter, idx) => {
            const isActive = idx === currentIndex;
            return (
              <button
                key={chapter.id}
                onClick={() => goTo(idx)}
                className={`w-full text-left px-4 py-3 rounded-xl border transition-all text-sm ${
                  isActive
                    ? "bg-card border-accent text-text-main font-medium"
                    : "border-transparent hover:bg-[color-mix(in_srgb,var(--color-text-main)_4%,transparent)] text-text-muted hover:text-text-main"
                }`}
              >
                {chapter.title}
              </button>
            );
          })}
        </nav>

        <div className="mt-6 pt-6 border-t border-hairline text-[10px] text-text-muted font-mono tracking-[0.14em] uppercase">
          {currentIndex + 1} / {chapters.length}
        </div>
      </aside>

      {/* Reading Pane */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-8">
          <div>
            <div className="font-mono text-xs uppercase tracking-[0.14em] text-text-muted mb-1">
              {bookTitle}
            </div>
            <h1 className="font-display text-4xl tracking-[-0.02em] text-text-main">
              {currentChapter.title}
            </h1>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={prev}
              disabled={currentIndex === 0}
              className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-hairline disabled:opacity-40 hover:bg-card transition"
              aria-label="Previous chapter"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={next}
              disabled={currentIndex === chapters.length - 1}
              className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-hairline disabled:opacity-40 hover:bg-card transition"
              aria-label="Next chapter"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Chapter Body */}
        <div className="max-w-[68ch] text-[15px] leading-[1.78] text-text-main space-y-6">
          {currentChapter.body}
        </div>

        {/* Artifacts / Figures */}
        {currentChapter.artifacts && currentChapter.artifacts.length > 0 && (
          <div className="mt-12 space-y-10">
            {currentChapter.artifacts.map((artifact, i) => (
              <figure key={i} className="border border-hairline rounded-2xl overflow-hidden bg-card">
                <div className="relative aspect-[16/9] bg-[color-mix(in_srgb,var(--color-background)_60%,transparent)] flex items-center justify-center">
                  <img
                    src={artifact.src}
                    alt={artifact.alt}
                    className="max-h-full max-w-full object-contain"
                  />
                </div>
                {artifact.caption && (
                  <figcaption className="px-6 py-4 text-xs text-text-muted border-t border-hairline font-mono tracking-[0.02em]">
                    {artifact.caption}
                  </figcaption>
                )}
              </figure>
            ))}
          </div>
        )}

        {/* Chapter Footer Nav */}
        <div className="mt-16 pt-8 border-t border-hairline flex items-center justify-between text-sm">
          <button
            onClick={prev}
            disabled={currentIndex === 0}
            className="inline-flex items-center gap-2 text-text-muted hover:text-text-main disabled:opacity-40 transition"
          >
            <ChevronLeft className="w-4 h-4" /> Previous
          </button>

          <button
            onClick={next}
            disabled={currentIndex === chapters.length - 1}
            className="inline-flex items-center gap-2 text-text-muted hover:text-text-main disabled:opacity-40 transition"
          >
            Next <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
