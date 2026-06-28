"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { Clock, ChevronDown, ChevronRight, Loader, Zap } from "lucide-react";
import { clsx } from "clsx";
import { motion, AnimatePresence } from "motion/react";
import type { ChartData, DashaDeepData, DashaNode, DashaLadderRow, DashaPrediction, FructificationResult, FructificationWindow } from "@/lib/types";
import { postCvce } from "@/lib/cvce-client";
import { DashaSeriesChart } from "./DashaSeriesChart";

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

const VERDICT_CFG = {
  shubh:  { bg: "rgba(16,185,129,0.12)", color: "#10b981", label: "Shubh"  },
  ashubh: { bg: "rgba(239,68,68,0.12)",  color: "#ef4444", label: "Ashubh" },
} as const;

// ── Verdict badge ────────────────────────────────────────────────────────────

function VerdictBadge({
  verdict,
  score,
  size = "sm",
}: {
  verdict?: string | null;
  score?: number | null;
  size?: "xs" | "sm";
}) {
  if (!verdict) return null;
  const cfg = VERDICT_CFG[verdict as keyof typeof VERDICT_CFG] ?? VERDICT_CFG.ashubh;
  const scoreStr = score != null ? ` ${score > 0 ? "+" : ""}${score}` : "";
  return (
    <span
      className={clsx(
        "shrink-0 font-mono rounded-md leading-none",
        size === "xs" ? "text-[8px] px-1 py-0.5" : "text-[9px] px-1.5 py-0.5",
      )}
      style={{ backgroundColor: cfg.bg, color: cfg.color }}
    >
      {cfg.label}{scoreStr}
    </span>
  );
}

// ── Fructification (shared with AllDashasPanel) ───────────────────────────────

const STRENGTH_STYLE_V: Record<string, { color: string; label: string }> = {
  exceptional: { color: "#fbbf24", label: "Exceptional" },
  strong:      { color: "#34d399", label: "Strong" },
  moderate:    { color: "#60a5fa", label: "Moderate" },
  limited:     { color: "#94a3b8", label: "Limited" },
};

function FructWindowCard({ w }: { w: FructificationWindow }) {
  const s = STRENGTH_STYLE_V[w.strength] ?? STRENGTH_STYLE_V.moderate;
  return (
    <div className="rounded-lg border px-3 py-2 space-y-1.5"
      style={{ borderColor: `${s.color}30`, backgroundColor: `${s.color}08` }}>
      <div className="flex items-center justify-between flex-wrap gap-1">
        <span className="text-[10px] font-mono font-semibold tabular-nums" style={{ color: s.color }}>
          {w.start.slice(0,7)} → {w.end.slice(0,7)}
        </span>
        <div className="flex items-center gap-1.5">
          <span className="text-[9px] px-1.5 py-0.5 rounded-full font-mono"
            style={{ backgroundColor: `${s.color}22`, color: s.color }}>
            {s.label}
          </span>
          {w.sav_bindus !== null && (
            <span className="text-[9px] font-mono" style={{ color: s.color }}>SAV {w.sav_bindus}</span>
          )}
        </div>
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-0.5">
        <span className="text-[10px] font-mono text-text-muted">♄ {w.saturn.sign} · {w.saturn.house}th</span>
        <span className="text-[10px] font-mono text-text-muted">♃ {w.jupiter.sign} · {w.jupiter.house}th</span>
        <span className="text-[9px] font-mono text-text-muted opacity-60">from {w.ref_label}</span>
      </div>
      <p className="text-[10px] text-text-muted leading-relaxed">{w.narrative}</p>
    </div>
  );
}

function VimsFructPanel({ result }: { result: FructificationResult }) {
  const color = DASHA.main;
  if (result.total_windows === 0) {
    return (
      <div className="rounded-lg border px-3 py-2.5 space-y-1"
        style={{ borderColor: "rgba(255,255,255,0.08)", backgroundColor: "rgba(255,255,255,0.02)" }}>
        <p className="text-[10px] font-mono uppercase tracking-wider flex items-center gap-1.5" style={{ color }}>
          <Zap className="w-3 h-3" /> Fructification Windows
        </p>
        <p className="text-[11px] text-text-muted">
          No Saturn+Jupiter double-transit overlap in this antardasha.
          The dasha promise may still operate through other mechanisms.
        </p>
      </div>
    );
  }
  return (
    <div className="rounded-lg border px-3 py-2.5 space-y-2.5"
      style={{ borderColor: `${color}22`, backgroundColor: `${color}06` }}>
      <div className="flex items-center justify-between flex-wrap gap-1">
        <p className="text-[10px] font-mono uppercase tracking-wider flex items-center gap-1.5" style={{ color }}>
          <Zap className="w-3 h-3" /> Fructification — {result.total_windows} window{result.total_windows > 1 ? "s" : ""}
        </p>
        <div className="flex flex-wrap gap-1">
          {result.reference_points.map((rp) => (
            <span key={rp.label} className="text-[9px] font-mono px-1.5 py-0.5 rounded-full"
              style={{ backgroundColor: `${color}18`, color }}>
              {rp.label}: {rp.sign}
            </span>
          ))}
        </div>
      </div>
      <div className="space-y-2">
        {result.windows.map((w, i) => <FructWindowCard key={i} w={w} />)}
      </div>
      <p className="text-[9px] text-text-muted font-mono opacity-50">
        {result.source.split("|")[0].trim()}
      </p>
    </div>
  );
}

// ── Antardasha expanded panel ─────────────────────────────────────────────────
// Shown when a level-2 (Antardasha) node is expanded.
// Contains: time-series chart + life-domain bullets from dasha_intel.

function AntardashaPanel({
  node,
  level,
  mahaLord,
  antarLord,
  mahaStart,
  mahaEnd,
  chart,
  moonOn,
  lagnaOn,
}: {
  node: DashaNode;
  level: number;
  mahaLord: string;
  antarLord: string;
  mahaStart?: string;
  mahaEnd?: string;
  chart?: ChartData;
  moonOn: boolean;
  lagnaOn: boolean;
}) {
  const pred = node.prediction;
  const domains = pred
    ? (
        [
          { label: "Career",  items: pred.career,  warn: false },
          { label: "Wealth",  items: pred.wealth,  warn: false },
          { label: "Health",  items: pred.health,  warn: false },
          { label: "Family",  items: pred.family,  warn: false },
          { label: "Caution", items: pred.caution, warn: true  },
        ] as const
      ).filter((d) => d.items.length > 0)
    : [];

  const canShowChart =
    !!chart?.meta?.birth_datetime && !!node.start && !!node.end;

  // Fructification — fetch once on mount (panel only renders when expanded)
  const [fructResult, setFructResult] = useState<FructificationResult | null>(null);
  const [fructLoading, setFructLoading] = useState(false);
  const fetchedRef = useRef(false);

  useEffect(() => {
    if (fetchedRef.current || !chart?.meta?.birth_datetime || level !== 2 || !mahaStart || !mahaEnd) return;
    fetchedRef.current = true;
    setFructLoading(true);
    const birth = chart.meta;
    postCvce<FructificationResult>("fructification", {
      birth_datetime: birth.birth_datetime,
      birth_lat: birth.birth_lat,
      birth_lon: birth.birth_lon,
      birth_tz: birth.birth_tz,
      system: "vimshottari",
      maha_lord: mahaLord,
      antar_lord: node.lord,
      maha_start: mahaStart,
      maha_end: mahaEnd,
      antar_start: node.start.slice(0, 10),
      antar_end: (node.end ?? node.start).slice(0, 10),
    }).then(setFructResult).catch(() => {}).finally(() => setFructLoading(false));
  }, [chart?.meta?.birth_datetime, level, mahaLord, mahaStart, mahaEnd, node.lord, node.start, node.end]);

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.22 }}
      className="mx-1 mb-2 mt-0.5 overflow-hidden rounded-xl border p-3.5 space-y-4"
      style={{
        borderColor: "rgba(124, 58, 237, 0.20)",
        backgroundColor: "rgba(124, 58, 237, 0.04)",
      }}
    >
      {/* ── Auspiciousness timeline (full period, not just midpoint) ── */}
      {canShowChart && (
        <DashaSeriesChart
          chart={chart!}
          mahaLord={level === 1 ? node.lord : mahaLord}
          antarLord={level === 1 ? node.lord : level === 2 ? node.lord : antarLord}
          startDate={node.start.slice(0, 10)}
          endDate={(node.end ?? node.start).slice(0, 10)}
          dashaScore={node.score ?? pred?.dasha_score ?? 0}
          title={
            level === 1
              ? `Auspiciousness — ${node.lord} Mahadasha`
              : level === 2
                ? `Auspiciousness — ${mahaLord} Maha / ${node.lord} Antar`
                : `Auspiciousness — ${antarLord} Antar / ${node.lord} Pratyantar`
          }
          moonOn={moonOn}
          lagnaOn={lagnaOn}
        />
      )}

      {/* ── Life domain bullets ── */}
      {domains.length > 0 && (
        <div className="space-y-2">
          <p className="text-[9px] font-mono uppercase tracking-widest text-text-muted">
            Life Domains
          </p>
          <div className="space-y-1.5">
            {domains.map(({ label, items, warn }) => (
              <div key={label} className="flex gap-2">
                <span
                  className="text-[9px] font-mono uppercase tracking-wide shrink-0 w-14 pt-px"
                  style={{ color: warn ? "#ef4444" : DASHA.soft }}
                >
                  {label}
                </span>
                <div className="space-y-0.5">
                  {items.map((item, i) => (
                    <p key={i} className="text-[11px] text-text-main leading-tight">
                      {item}
                    </p>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Fructification windows ── */}
      {level === 2 && fructLoading && (
        <div className="flex items-center gap-2 text-text-muted">
          <Loader className="w-3 h-3 animate-spin" />
          <span className="text-[10px] font-mono">Computing fructification windows…</span>
        </div>
      )}
      {level === 2 && fructResult && (
        <VimsFructPanel result={fructResult} />
      )}
    </motion.div>
  );
}

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
  verdict,
  score,
  onClick,
}: {
  lord: string;
  year: string;
  durationYears: number;
  isCurrent: boolean;
  isExpanded: boolean;
  level: number;
  verdict?: string | null;
  score?: number | null;
  onClick: () => void;
}) {
  const vcfg = verdict ? VERDICT_CFG[verdict as keyof typeof VERDICT_CFG] : null;
  return (
    <button
      onClick={onClick}
      className={clsx(
        "shrink-0 flex flex-col items-center gap-0.5 px-3 py-2 rounded-xl border transition-colors duration-200",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7c3aed]/60",
        isCurrent ? "font-semibold" : "hover:bg-[#7c3aed]/[0.06]",
      )}
      style={{
        backgroundColor: isCurrent
          ? "rgba(124, 58, 237, 0.12)"
          : isExpanded
            ? "rgba(124, 58, 237, 0.06)"
            : "transparent",
        borderColor: isCurrent
          ? "rgba(124, 58, 237, 0.45)"
          : vcfg
            ? `${vcfg.color}55`
            : isExpanded
              ? "rgba(124, 58, 237, 0.25)"
              : "var(--color-hairline)",
      }}
      aria-current={isCurrent ? "true" : undefined}
      aria-expanded={isExpanded}
    >
      <span
        className={clsx("text-xs font-mono tracking-wide", isCurrent ? "font-semibold" : "font-medium")}
        style={{ color: isCurrent ? DASHA.main : "var(--color-text-main)" }}
      >
        {lord}
      </span>
      <span className="text-[10px]" style={{ color: isCurrent ? DASHA.main : "var(--color-text-muted)" }}>
        {year} · {fmtDuration(durationYears)}
      </span>
      {verdict && (
        <span
          className="text-[8px] font-mono px-1.5 py-0.5 rounded-full mt-0.5 leading-none"
          style={{ backgroundColor: vcfg?.bg, color: vcfg?.color }}
        >
          {vcfg?.label}{score != null ? ` ${score > 0 ? "+" : ""}${score}` : ""}
        </span>
      )}
      {isExpanded && (
        <ChevronDown className="w-3 h-3 mt-0.5" style={{ color: DASHA.main }} />
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
            <VerdictBadge verdict={node.verdict} score={node.score} size="xs" />
            <span className="text-[10px] text-text-muted font-mono tabular-nums">
              {pct}%
            </span>
            {canExpand && (
              <span className="text-[9px] font-mono" style={{ color: DASHA.soft }}>
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
  mahaLord,
  antarLord,
  mahaStart,
  mahaEnd,
  chart,
  moonOn = true,
  lagnaOn = false,
}: {
  nodes: DashaNode[];
  mahaStart?: string;
  mahaEnd?: string;
  level: number;
  parentPath: string;
  expanded: Set<string>;
  onToggle: (path: string) => void;
  current: string[];
  currentDepth: number;
  mahaLord?: string;
  antarLord?: string;
  chart?: ChartData;
  moonOn?: boolean;
  lagnaOn?: boolean;
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

          // At level 1, this node IS the Mahadasha — thread its lord and dates down
          const effectiveMahaLord = level === 1 ? node.lord : mahaLord;
          const effectiveMahaStart = level === 1 ? node.start.slice(0, 10) : mahaStart;
          const effectiveMahaEnd   = level === 1 ? (node.end ?? node.start).slice(0, 10) : mahaEnd;

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
              <AnimatePresence>
                {isExpanded && level >= 2 && level <= 3 && (
                  <AntardashaPanel
                    node={node}
                    level={level}
                    mahaLord={effectiveMahaLord ?? ""}
                    antarLord={antarLord ?? ""}
                    mahaStart={effectiveMahaStart}
                    mahaEnd={effectiveMahaEnd}
                    chart={chart}
                    moonOn={moonOn}
                    lagnaOn={lagnaOn}
                  />
                )}
              </AnimatePresence>
              {isExpanded && hasChildren && (
                <DashaLevel
                  nodes={node.subPeriods}
                  level={level + 1}
                  parentPath={nodePath}
                  expanded={expanded}
                  onToggle={onToggle}
                  current={current}
                  currentDepth={currentDepth + 1}
                  mahaLord={effectiveMahaLord}
                  antarLord={level === 2 ? node.lord : antarLord}
                  mahaStart={effectiveMahaStart}
                  mahaEnd={effectiveMahaEnd}
                  chart={chart}
                  moonOn={moonOn}
                  lagnaOn={lagnaOn}
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
  const [loading, setLoading] = useState(() => !externalData && !!chart?.meta?.birth_datetime);
  const [error, setError] = useState<string | null>(null);
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
  const [moonOn, setMoonOn] = useState(true);
  const [lagnaOn, setLagnaOn] = useState(false);

  function toggleMoon(v: boolean) { if (!v && !lagnaOn) return; setMoonOn(v); }
  function toggleLagna(v: boolean) { if (!v && !moonOn) return; setLagnaOn(v); }

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

      {/* ── Moon / Lagna transit perspective toggles ────────────────────── */}
      <div className="flex items-center gap-4 py-1">
        <span className="text-[9px] font-mono uppercase tracking-widest text-text-muted" title="Total transit score of all 9 planets, evaluated from this reference point">View from</span>

        {/* Moon toggle */}
        <label className="flex items-center gap-1.5 cursor-pointer select-none">
          <input type="checkbox" className="sr-only" checked={moonOn} onChange={(e) => toggleMoon(e.target.checked)} />
          <span
            className="relative inline-flex w-7 h-[14px] rounded-full transition-colors duration-200"
            style={{ backgroundColor: moonOn ? "#60a5fa" : "var(--color-hairline)" }}
          >
            <span
              className="absolute top-[2px] w-[10px] h-[10px] rounded-full bg-white transition-transform duration-200"
              style={{ transform: moonOn ? "translateX(14px)" : "translateX(2px)" }}
            />
          </span>
          <span className="text-[10px] font-mono transition-colors" style={{ color: moonOn ? "#60a5fa" : "var(--color-text-muted)" }}>
            Moon
          </span>
        </label>

        {/* Lagna toggle */}
        <label className="flex items-center gap-1.5 cursor-pointer select-none">
          <input type="checkbox" className="sr-only" checked={lagnaOn} onChange={(e) => toggleLagna(e.target.checked)} />
          <span
            className="relative inline-flex w-7 h-[14px] rounded-full transition-colors duration-200"
            style={{ backgroundColor: lagnaOn ? "#f59e0b" : "var(--color-hairline)" }}
          >
            <span
              className="absolute top-[2px] w-[10px] h-[10px] rounded-full bg-white transition-transform duration-200"
              style={{ transform: lagnaOn ? "translateX(14px)" : "translateX(2px)" }}
            />
          </span>
          <span className="text-[10px] font-mono transition-colors" style={{ color: lagnaOn ? "#f59e0b" : "var(--color-text-muted)" }}>
            Ascendant
          </span>
        </label>
      </div>

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
                verdict={node.verdict}
                score={node.score}
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

            // Chips already show the Mahadasha row, so start DashaLevel at
            // level=2 (Antardasha) with parentPath=the real mahadasha index.
            // This keeps paths consistent: antardasha paths are "4-0", "4-1", …
            // matching what buildCurrentPaths and toggleNode produce.
            return (
              <div key={path}>
                {/* Mahadasha-level chart — shown directly, not via DashaLevel */}
                <AntardashaPanel
                  node={mahadasha}
                  level={1}
                  mahaLord={mahadasha.lord}
                  antarLord={mahadasha.lord}
                  chart={chart}
                  moonOn={moonOn}
                  lagnaOn={lagnaOn}
                />

                {/* Antardasha children */}
                {mahadasha.subPeriods.length > 0 && (
                  <DashaLevel
                    nodes={mahadasha.subPeriods}
                    level={2}
                    parentPath={path}
                    expanded={expandedPaths}
                    onToggle={toggleNode}
                    current={current}
                    currentDepth={1}
                    mahaLord={mahadasha.lord}
                    chart={chart}
                    moonOn={moonOn}
                    lagnaOn={lagnaOn}
                  />
                )}
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
