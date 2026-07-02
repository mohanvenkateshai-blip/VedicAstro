"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { clsx } from "clsx";
import type { KalachakraNode } from "@/lib/types";
import { leapStyle } from "./kalachakraCopy";

function fmtRange(start: string, end?: string) {
  return end ? `${start} → ${end}` : start;
}

function calcPercent(startISO: string, endISO?: string): number {
  const startMs = new Date(startISO).getTime();
  const endMs = endISO ? new Date(endISO).getTime() : startMs;
  const nowMs = Date.now();
  if (nowMs >= endMs) return 100;
  if (nowMs <= startMs) return 0;
  return Math.round(((nowMs - startMs) / (endMs - startMs)) * 100);
}

function isRunning(node: KalachakraNode): boolean {
  const today = new Date().toISOString().slice(0, 10);
  return node.start <= today && today <= (node.end ?? node.start);
}

function buildCurrentPaths(nodes: KalachakraNode[]): Set<string> {
  const paths = new Set<string>();
  let cursor = nodes;
  let prefix = "";
  for (let level = 0; level < 3; level++) {
    const idx = cursor.findIndex(isRunning);
    if (idx === -1) break;
    prefix = prefix ? `${prefix}-${idx}` : `${idx}`;
    paths.add(prefix);
    cursor = cursor[idx].subPeriods ?? [];
  }
  return paths;
}

interface TreeRowProps {
  node: KalachakraNode;
  path: string;
  expanded: Set<string>;
  onToggle: (path: string) => void;
  onSelectPeriod: (node: KalachakraNode) => void;
  onSelectLeap: (node: KalachakraNode) => void;
}

function TreeRow({ node, path, expanded, onToggle, onSelectPeriod, onSelectLeap }: TreeRowProps) {
  const isOpen = expanded.has(path);
  const running = isRunning(node);
  const pct = calcPercent(node.start, node.end);
  const leap = node.leapFromPrevious;
  const hasChildren = (node.subPeriods?.length ?? 0) > 0;
  const style = leap ? leapStyle(leap.type) : null;

  return (
    <div>
      <div
        className={clsx(
          "flex items-center gap-2 rounded-lg border px-3 py-2 cursor-pointer transition-colors",
          running ? "border-accent/50 bg-accent/5" : style ? style.borderClass : "border-hairline",
          style && !running ? style.bgClass : "",
        )}
        style={{ marginLeft: `${(node.level - 1) * 16}px` }}
        onClick={() => hasChildren && onToggle(path)}
      >
        {hasChildren ? (
          isOpen ? (
            <ChevronDown className="h-3.5 w-3.5 text-text-muted shrink-0" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-text-muted shrink-0" />
          )
        ) : (
          <span className="w-3.5 shrink-0" />
        )}

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium">{node.sign}</span>
            {running && (
              <span className="rounded-full bg-accent/15 px-1.5 py-0.5 text-[10px] font-mono text-accent">
                now
              </span>
            )}
            {leap && style && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectLeap(node);
                }}
                className={clsx("rounded-full px-1.5 py-0.5 text-[10px] font-mono", style.colorClass, style.bgClass)}
              >
                {style.shortLabel}
              </button>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onSelectPeriod(node);
              }}
              className="text-[10px] font-mono text-text-muted hover:text-accent underline underline-offset-2"
            >
              details
            </button>
          </div>
          <div className="text-xs font-mono text-text-muted mt-0.5">
            {fmtRange(node.start, node.end)} · {node.durationYears.toFixed(2)}y
          </div>
          <div className="h-1 rounded-full bg-hairline/40 mt-1.5 overflow-hidden">
            <motion.div
              className={clsx("h-full rounded-full", running ? "bg-accent" : "bg-text-muted/40")}
              initial={{ width: 0 }}
              animate={{ width: `${Math.max(pct, 2)}%` }}
              transition={{ duration: 0.6, ease: "easeOut" }}
            />
          </div>
        </div>
      </div>

      <AnimatePresence>
        {isOpen && hasChildren && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-1.5 space-y-1.5">
              {node.subPeriods.map((child, i) => (
                <TreeRow
                  key={`${path}-${i}`}
                  node={child}
                  path={`${path}-${i}`}
                  expanded={expanded}
                  onToggle={onToggle}
                  onSelectPeriod={onSelectPeriod}
                  onSelectLeap={onSelectLeap}
                />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function KalachakraTree({
  tree,
  onSelectPeriod,
  onSelectLeap,
}: {
  tree: KalachakraNode[];
  onSelectPeriod: (node: KalachakraNode) => void;
  onSelectLeap: (node: KalachakraNode) => void;
}) {
  const initialExpanded = useMemo(() => buildCurrentPaths(tree), [tree]);
  const [expanded, setExpanded] = useState<Set<string>>(initialExpanded);

  const toggle = (path: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  return (
    <div className="space-y-1.5">
      {tree.map((node, i) => (
        <TreeRow
          key={i}
          node={node}
          path={`${i}`}
          expanded={expanded}
          onToggle={toggle}
          onSelectPeriod={onSelectPeriod}
          onSelectLeap={onSelectLeap}
        />
      ))}
    </div>
  );
}
