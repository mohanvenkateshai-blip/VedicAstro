"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { Clock, ChevronDown, ChevronRight, Loader } from "lucide-react";
import { clsx } from "clsx";
import { motion, AnimatePresence } from "motion/react";
import type { ChartData, DashaDeepData, DashaNode, DashaLadderRow } from "@/lib/types";
import { postCvce } from "@/lib/cvce-client";

// Re-export for consumers that previously imported from here
export type { DashaDeepData, DashaNode, DashaLadderRow };

export interface DashaDeepProps {
  chart?: ChartData;
  dashaData?: DashaDeepData;
}

// ── Constants ───────────────────────────────────────────────────────────────

const MAX_DEPTH = 5;

const LEVEL_LABELS: Record<number, string> = {
  1: "Mahadasha",
  2: "Antardasha",
  3: "Pratyantar",
  4: "Sookshma",
  5: "Prana",
};

const DASHA = {
  main: "#7c3aed",
  soft: "#8b5cf6",
} as const;

// ── Helpers ─────────────────────────────────────────────────────────────────

function calcPercent(startISO: string, durationYears: number): number {
  const startMs = new Date(startISO).getTime();
  const nowMs = Date.now();
  const durationMs = durationYears * 365.25 * 24 * 60 * 60 * 1000;
  const endMs = startMs + durationMs;
  if (nowMs >= endMs) return 100;
  if (nowMs <= startMs) return 0;
  return Math.round(((nowMs - startMs) / durationMs) * 100);
}

function yearFromISO(iso: string): string {
  return new Date(iso).getFullYear().toString();
}

function fmtRange(start: string, end?: string) {
  const sy = start.slice(0, 10);
  const ey = end?.slice(0, 10);
  return ey ? `${sy} → ${ey}` : sy;
}

function CurrentLadder({ ladder }: { ladder: DashaLadderRow[] }) {
  if (!ladder.length) return null;
  return (
    <div
      className="rounded-xl border p-4 space-y-2"
      style={{
        borderColor: "rgba(124, 58, 237, 0.30)",
        backgroundColor: "rgba(124, 58, 237, 0.06)",
      }}
    >
      <p
        className="text-[11px] font-mono uppercase tracking-wider"
        style={{ color: DASHA.main }}
      >
        Running now
      </p>
      {ladder.map((row) => (
        <div
          key={row.level}
          className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm"
        >
          <span
            className="text-[10px] font-mono uppercase tracking-wide shrink-0"
            style={{ color: DASHA.soft }}
          >
            {row.levelLabel}
          </span>
          <span className="font-semibold" style={{ color: DASHA.main }}>
            {row.lord}
          </span>
          <span className="text-xs font-mono text-text-muted tabular-nums">
            {fmtRange(row.start, row.end)}
          </span>
        </div>
      ))}
    </div>
  );
}

function fmtDuration(years: number): string {
  if (years >= 1) return `${years.toFixed(1)}y`;
  const months = years * 12;
  if (months >= 1) return `${months.toFixed(0)}m`;
  const days = years * 365;
  return `${Math.round(days)}d`;
}

function buildCurrentPaths(
  nodes: DashaNode[],
  current: string[],
): string[] {
  const paths: string[] = [];
  let cursor = nodes;
  for (let i = 0; i < current.length && i < MAX_DEPTH; i++) {
    const idx = cursor.findIndex((n) => n.lord === current[i]);
    if (idx === -1) break;
    const path = i === 0 ? `${idx}` : `${paths[i - 1]}-${idx}`;
    paths.push(path);
    cursor = cursor[idx].subPeriods ?? [];
  }
  return paths;
}

// ── Sub-components ──────────────────────────────────────────────────────────

function ProgressBar({ pct, level }: { pct: number; level: number }) {
  return (
    <div className="h-1 rounded-full bg-[color-mix(in_srgb,var(--color-hairline)_60%,transparent)] mt-1 overflow-hidden">
      <motion.div
        className="h-full rounded-full"
        style={{ backgroundColor: level === 1 ? DASHA.main : DASHA.soft }}
        initial={{ width: 0 }}
        animate={{ width: `${Math.max(pct, 2)}%` }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      />
    </div>
  );
}

function MahadashaChip({
  lord,
  year,
  durationYears,
  isCurrent,
  isExpanded,
  level,
  onClick,
}: {
  lord: string;
  year: string;
  durationYears: number;
  isCurrent: boolean;
  isExpanded: boolean;
  level: number;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        "shrink-0 flex flex-col items-center gap-0.5 px-3 py-2 rounded-xl border transition-colors duration-200",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7c3aed]/60",
        isCurrent
          ? "font-semibold"
          : "hover:bg-[#7c3aed]/[0.06]",
      )}
      style={{
        backgroundColor: isCurrent
          ? "rgba(124, 58, 237, 0.12)"
          : isExpanded
            ? "rgba(124, 58, 237, 0.06)"
            : "transparent",
        borderColor: isCurrent
          ? "rgba(124, 58, 237, 0.45)"
          : isExpanded
            ? "rgba(124, 58, 237, 0.25)"
            : "var(--color-hairline)",
      }}
      aria-current={isCurrent ? "true" : undefined}
      aria-expanded={isExpanded}
    >
      <span
        className={clsx(
          "text-xs font-mono tracking-wide",
          isCurrent ? "font-semibold" : "font-medium",
        )}
        style={{ color: isCurrent ? DASHA.main : "var(--color-text-main)" }}
      >
        {lord}
      </span>
      <span
        className="text-[10px]"
        style={{
          color: isCurrent ? DASHA.main : "var(--color-text-muted)",
        }}
      >
        {year} · {fmtDuration(durationYears)}
      </span>
      {isExpanded && (
        <ChevronDown
          className="w-3 h-3 mt-0.5"
          style={{ color: DASHA.main }}
        />
      )}
    </button>
  );
}

interface DashaNodeCardProps {
  node: DashaNode;
  level: number;
  path: string;
  isCurrent: boolean;
  isExpanded: boolean;
  canExpand: boolean;
  onToggle: (path: string) => void;
}

function DashaNodeCard({
  node,
  level,
  path,
  isCurrent,
  isExpanded,
  canExpand,
  onToggle,
}: DashaNodeCardProps) {
  const pct = calcPercent(node.start, node.durationYears);
  const depthLabel =
    level >= MAX_DEPTH
      ? `Level ${level} — max depth`
      : `Level ${level} of ${MAX_DEPTH}`;

  return (
    <div className="mb-1.5">
      <button
        onClick={() => canExpand && onToggle(path)}
        disabled={!canExpand}
        className={clsx(
          "w-full text-left rounded-xl border px-3 py-2.5 transition-colors duration-200",
          canExpand
            ? "cursor-pointer hover:bg-[#7c3aed]/[0.06] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7c3aed]/60"
            : "cursor-default",
        )}
        style={{
          backgroundColor: isCurrent
            ? "rgba(124, 58, 237, 0.10)"
            : level % 2 === 0
              ? "rgba(139, 92, 246, 0.04)"
              : "transparent",
          borderColor: isCurrent
            ? "rgba(124, 58, 237, 0.35)"
            : level <= 2
              ? "rgba(139, 92, 246, 0.18)"
              : "var(--color-hairline)",
          paddingLeft: `${8 + (level - 1) * 6}px`,
        }}
        aria-expanded={canExpand ? isExpanded : undefined}
      >
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 min-w-0">
            {canExpand ? (
              isExpanded ? (
                <ChevronDown
                  className="w-3.5 h-3.5 shrink-0"
                  style={{ color: DASHA.main }}
                />
              ) : (
                <ChevronRight
                  className="w-3.5 h-3.5 shrink-0"
                  style={{ color: DASHA.soft }}
                />
              )
            ) : (
              <span className="w-3.5 shrink-0" />
            )}
            <span
              className={clsx(
                "text-sm truncate",
                level === 1 ? "font-semibold" : "font-medium",
              )}
              style={{
                color: isCurrent
                  ? DASHA.main
                  : level === 1
                    ? DASHA.main
                    : "var(--color-text-main)",
              }}
            >
              {node.lord}
            </span>
            {isCurrent && (
              <span
                className="shrink-0 text-[10px] font-mono px-1.5 py-0.5 rounded-md"
                style={{
                  backgroundColor: "rgba(124, 58, 237, 0.15)",
                  color: DASHA.main,
                }}
              >
                now
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-[10px] text-text-muted font-mono tabular-nums">
              {pct}%
            </span>
            {canExpand && (
              <span
                className="text-[9px] font-mono"
                style={{ color: DASHA.soft }}
              >
                {node.subPeriods.length}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 mt-1 text-[11px] flex-wrap">
          <span className="flex items-center gap-1 text-text-muted font-mono tabular-nums">
            <Clock className="w-3 h-3" />
            {fmtRange(node.start, node.end)}
          </span>
          <span className="text-text-muted font-mono">
            {fmtDuration(node.durationYears)}
          </span>
          <span
            className="text-[10px] font-mono ml-auto"
            style={{ color: DASHA.soft }}
          >
            {LEVEL_LABELS[level]}
          </span>
        </div>

        <ProgressBar pct={pct} level={level} />
      </button>

      {isExpanded && level >= MAX_DEPTH && (
        <p
          className="text-[10px] font-mono px-2 mt-1"
          style={{ color: DASHA.soft, paddingLeft: `${8 + level * 6}px` }}
        >
          {depthLabel} &middot; no deeper periods available
        </p>
      )}
    </div>
  );
}

function DashaLevel({
  nodes,
  level,
  parentPath,
  expanded,
  onToggle,
  current,
  currentDepth,
}: {
  nodes: DashaNode[];
  level: number;
  parentPath: string;
  expanded: Set<string>;
  onToggle: (path: string) => void;
  current: string[];
  currentDepth: number;
}) {
  if (!nodes || nodes.length === 0) return null;

  return (
    <AnimatePresence initial={false}>
      <motion.div
        key={parentPath || "root"}
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: "auto" }}
        exit={{ opacity: 0, height: 0 }}
        transition={{ duration: 0.2 }}
        className={clsx(
          level > 1 && "ml-4 pl-3",
          level > 1 && "border-l",
        )}
        style={{
          borderColor:
            level > 1
              ? level <= 3
                ? "rgba(124, 58, 237, 0.25)"
                : "rgba(139, 92, 246, 0.12)"
              : undefined,
        }}
      >
        {level > 1 && (
          <div className="flex items-center gap-2 mb-1.5">
            <span
              className="text-[10px] font-mono tracking-wider uppercase px-2 py-0.5 rounded-md"
              style={{
                backgroundColor: "rgba(124, 58, 237, 0.08)",
                color: DASHA.main,
              }}
            >
              {LEVEL_LABELS[level]}
            </span>
            {level >= MAX_DEPTH && (
              <span
                className="text-[9px] font-mono"
                style={{ color: DASHA.soft }}
              >
                max depth
              </span>
            )}
          </div>
        )}
        {nodes.map((node, i) => {
          const nodePath = parentPath ? `${parentPath}-${i}` : `${i}`;
          const isExpanded = expanded.has(nodePath);
          const isCurrentNode =
            currentDepth < current.length && current[currentDepth] === node.lord;
          const hasChildren = node.subPeriods && node.subPeriods.length > 0;
          const canExpand = hasChildren && level < MAX_DEPTH;

          return (
            <div key={nodePath}>
              <DashaNodeCard
                node={node}
                level={level}
                path={nodePath}
                isCurrent={isCurrentNode}
                isExpanded={isExpanded}
                canExpand={canExpand}
                onToggle={onToggle}
              />
              {isExpanded && hasChildren && (
                <DashaLevel
                  nodes={node.subPeriods}
                  level={level + 1}
                  parentPath={nodePath}
                  expanded={expanded}
                  onToggle={onToggle}
                  current={current}
                  currentDepth={currentDepth + 1}
                />
              )}
            </div>
          );
        })}
      </motion.div>
    </AnimatePresence>
  );
}

// ── Main component ──────────────────────────────────────────────────────────

export function DashaDeepTree({ chart, dashaData: externalData }: DashaDeepProps) {
  const [fetchedData, setFetchedData] = useState<DashaDeepData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());

  const data = externalData ?? fetchedData;
  const mahadashas = data?.dashaTree ?? [];
  const current = data?.current ?? [];
  const ladder = data?.currentLadder ?? [];
  const balance = data?.balanceAtBirth;

  // ── Auto-fetch from CVCE when chart is provided without dashaData ─────────

  useEffect(() => {
    if (externalData || !chart?.meta?.birth_datetime) return;

    let cancelled = false;

    async function fetchDasha() {
      setLoading(true);
      setError(null);

      try {
        const json = await postCvce<DashaDeepData>("dasha-deep", {
          birth_datetime: chart!.meta!.birth_datetime,
          birth_lat: chart!.meta!.birth_lat,
          birth_lon: chart!.meta!.birth_lon,
          birth_tz: chart!.meta!.birth_tz,
        });

        if (!cancelled) {
          setFetchedData(json);
        }
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof Error ? e.message : "Failed to load dasha data",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchDasha();
    return () => {
      cancelled = true;
    };
  }, [externalData, chart]);

  // ── Auto-expand the current running dasha path ────────────────────────────

  useEffect(() => {
    if (!data || current.length === 0) return;
    const paths = buildCurrentPaths(mahadashas, current);
    if (paths.length === 0) return;
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      for (const p of paths) next.add(p);
      return next;
    });
    // Reset the set identity when data changes — our Set-mutation above works
    // because expandedPaths starts empty on first render, but for subsequent
    // data swaps we need a fresh Set.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  // ── Toggle a node's children ──────────────────────────────────────────────

  const toggleNode = useCallback((path: string) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, []);

  // ── Derived: expanded mahadasha indices ───────────────────────────────────

  const expandedMahadashas = useMemo(() => {
    return mahadashas
      .map((_, i) => `${i}`)
      .filter((p) => expandedPaths.has(p));
  }, [mahadashas, expandedPaths]);

  // ── Rendering ─────────────────────────────────────────────────────────────

  // Loading
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16 text-text-muted">
        <Loader
          className="w-6 h-6 animate-spin"
          style={{ color: DASHA.main }}
        />
        <span className="text-sm font-mono">computing dasha periods...</span>
      </div>
    );
  }

  // Error
  if (error && !data) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-16 text-text-muted">
        <span className="text-sm font-mono">Could not load dasha data</span>
        <span className="text-xs font-mono text-[color-mix(in_srgb,var(--color-danger)_80%,transparent)]">
          {error}
        </span>
      </div>
    );
  }

  // Empty / no data
  if (!data || mahadashas.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-16 text-text-muted">
        <Clock className="w-5 h-5" />
        <span className="text-sm font-mono">
          No dasha periods available
        </span>
        <span className="text-xs text-text-muted">
          {chart
            ? "The calculation engine returned no dasha data for this chart."
            : "Provide a chart or dasha data to explore periods."}
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {balance ? (
        <p className="text-xs font-mono text-text-muted">
          Balance at birth:{" "}
          <span style={{ color: DASHA.main }}>{balance.label}</span>
        </p>
      ) : null}

      {ladder.length > 0 ? <CurrentLadder ladder={ladder} /> : null}

      {/* ── Mahadasha timeline ─────────────────────────────────────────── */}
      <div className="overflow-x-auto -mx-1 px-1 pb-1">
        <div className="flex gap-2 min-w-min">
          {mahadashas.map((node, i) => {
            const path = `${i}`;
            const isCurrent = current[0] === node.lord;
            const isExpanded = expandedPaths.has(path);

            return (
              <MahadashaChip
                key={path}
                lord={node.lord}
                year={yearFromISO(node.start)}
                durationYears={node.durationYears}
                isCurrent={isCurrent}
                isExpanded={isExpanded}
                level={node.level}
                onClick={() => toggleNode(path)}
              />
            );
          })}
        </div>
      </div>

      {/* ── Expanded tree ──────────────────────────────────────────────── */}
      {expandedMahadashas.length > 0 && (
        <div className="space-y-3">
          {expandedMahadashas.map((path) => {
            const idx = parseInt(path, 10);
            const mahadasha = mahadashas[idx];
            if (!mahadasha) return null;

            return (
              <div key={path}>
                <DashaLevel
                  nodes={[mahadasha]}
                  level={1}
                  parentPath=""
                  expanded={expandedPaths}
                  onToggle={toggleNode}
                  current={current}
                  currentDepth={0}
                />
              </div>
            );
          })}
        </div>
      )}

      {expandedMahadashas.length === 0 && (
        <p className="text-center text-xs text-text-muted py-6">
          Tap a Mahadasha above to explore its sub-periods
        </p>
      )}
    </div>
  );
}
