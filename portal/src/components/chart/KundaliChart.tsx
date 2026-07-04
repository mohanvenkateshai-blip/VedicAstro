"use client";

import { useMemo, useState } from "react";
import { RASHI_SHORT, PLANET_SHORT, type SignIndex } from "@/lib/types";
import { planetColor, elementColor } from "@/lib/astroColors";

/**
 * Professional Vedic Kundali — prop-driven, renders real planet placements.
 *
 * `signs` maps each planet name (+ "Lagna") to a sign index 0..11. This is
 * exactly the shape of any varga's `.signs` (D1 Rasi, D9 Navamsa, …), so the
 * same component renders every divisional chart.
 *
 * South Indian: signs fixed in a 4×4 ring (Pisces top-left, clockwise).
 * North Indian: houses fixed (diamond); H1 = Lagna at top, signs rotate CCW.
 */

type Variant = "south" | "north";

interface Props {
  signs: Record<string, SignIndex>;
  variant?: Variant;
  sav?: number[]; // optional Sarvashtakavarga bindus per sign (overlay)
  /** Optional formatted degree-in-sign label per planet/"Lagna" (e.g. "12°34'"),
   * shown when its house is hovered or focused — keeps the default grid
   * compact while still surfacing exact degree on demand. */
  degrees?: Record<string, string>;
  size?: number;
  className?: string;
}

const PLANET_ORDER = [
  "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu",
];

interface Occupant {
  short: string;
  deg?: string;
  color: string;
}

function occupantsBySign(signs: Record<string, SignIndex>, degrees?: Record<string, string>) {
  const map: Record<number, Occupant[]> = {};
  for (const p of PLANET_ORDER) {
    const s = signs[p];
    if (s == null) continue;
    (map[s] ??= []).push({ short: PLANET_SHORT[p] ?? p.slice(0, 2), deg: degrees?.[p], color: planetColor(p) });
  }
  return map;
}

function savColor(b: number | undefined): string {
  if (b == null) return "var(--color-text-muted)";
  if (b >= 30) return "var(--color-success)";
  if (b >= 28) return "#2dd4bf";
  if (b >= 22) return "var(--color-accent)";
  return "var(--color-danger)";
}

export function KundaliChart({
  signs,
  variant = "south",
  sav,
  degrees,
  size = 340,
  className,
}: Props) {
  const lagnaSign = signs.Lagna ?? signs.Ascendant ?? 0;
  const occ = useMemo(() => occupantsBySign(signs, degrees), [signs, degrees]);
  const lagnaDeg = degrees?.Lagna ?? degrees?.Ascendant;
  const [hover, setHover] = useState<number | null>(null);
  const [focus, setFocus] = useState<number | null>(null);

  const props: InnerProps = {
    size, occ, lagnaSign, lagnaDeg, sav, hover, setHover, focus, setFocus, className,
  };

  return (
    <div className="relative">
      {variant === "south" ? <SouthChart {...props} /> : <NorthChart {...props} />}
      {sav && <SavLegend />}
    </div>
  );
}

function SavLegend() {
  return (
    <div className="absolute bottom-2 right-2 z-10 rounded-md border border-hairline bg-surface/90 px-2 py-1 text-[10px] text-text-muted shadow-sm">
      <div className="flex items-center gap-3 font-mono">
        <span><span className="text-success">●</span> 30+ Excellent</span>
        <span><span className="text-[#2dd4bf]">●</span> 28–29 Good</span>
        <span><span className="text-accent">●</span> 22–27 Standard</span>
        <span><span className="text-danger">●</span> &lt;22 Depleted</span>
      </div>
    </div>
  );
}

interface InnerProps {
  size: number;
  occ: Record<number, Occupant[]>;
  lagnaSign: number;
  lagnaDeg?: string;
  sav?: number[];
  hover: number | null;
  setHover: (n: number | null) => void;
  focus: number | null;
  setFocus: (n: number | null) => void;
  className?: string;
}

const GRID = "var(--color-hairline)";
// The chart itself should read as the brightest surface on the page — a
// visible step up from the (deliberately duller) tile it sits in — so
// planets/signs/ascendant pop instead of blending into a flat dark card.
const CHART_SURFACE = "color-mix(in srgb, var(--color-card) 80%, var(--color-card-fg) 20%)";

function PlanetStack({
  planets, expanded, x, y, w, fontSize,
}: { planets: Occupant[]; expanded?: boolean; x: number; y: number; w: number; fontSize: number }) {
  if (!planets.length) return null;

  // Expanded (hovered/focused) — one line per planet with its exact degree,
  // e.g. "Su 12°34'", in that planet's own classical color. Only ever one
  // house expanded at a time, so there's room even in smaller grid sizes.
  if (expanded && planets.some((p) => p.deg)) {
    return (
      <>
        {planets.map((p, i) => (
          <text
            key={i}
            x={x}
            y={y + i * (fontSize + 3)}
            textAnchor="middle"
            fontSize={fontSize * 0.95}
            fontWeight={700}
            fill={p.color}
            className="font-mono"
          >
            {p.short}
            {p.deg ? ` ${p.deg}` : ""}
          </text>
        ))}
      </>
    );
  }

  // Compact default view: each planet keeps its own classical color even
  // when several share a line — real color signal, not decoration, since
  // it's the same association used in the degree/hover view and elsewhere.
  const perRow = Math.max(2, Math.floor(w / (fontSize * 1.6)));
  const rows: Occupant[][] = [];
  for (let i = 0; i < planets.length; i += perRow) rows.push(planets.slice(i, i + perRow));
  return (
    <>
      {rows.map((row, ri) => (
        <text
          key={ri}
          x={x}
          y={y + ri * (fontSize + 2)}
          textAnchor="middle"
          fontSize={fontSize}
          fontWeight={700}
          className="font-mono"
        >
          {row.map((p, i) => (
            <tspan key={i} fill={p.color}>
              {i > 0 ? " " : ""}
              {p.short}
            </tspan>
          ))}
        </text>
      ))}
    </>
  );
}

function SouthChart({ size, occ, lagnaSign, lagnaDeg, sav, hover, setHover, focus, setFocus, className }: InnerProps) {
  const CS = size / 4;
  const layout = [
    [11, 0, 1, 2],
    [10, -1, -1, 3],
    [9, -1, -1, 4],
    [8, 7, 6, 5],
  ];
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className={className} role="img" aria-label={`South Indian kundali, Lagna in ${RASHI_SHORT[lagnaSign]}`}>
      <rect width={size} height={size} rx={10} fill={CHART_SURFACE} />
      {[1, 2, 3].map((i) => (
        <g key={i}>
          <line x1={i * CS} y1={0} x2={i * CS} y2={size} stroke={GRID} />
          <line x1={0} y1={i * CS} x2={size} y2={i * CS} stroke={GRID} />
        </g>
      ))}
      <rect x={CS} y={CS} width={CS * 2} height={CS * 2} fill="var(--color-background)" opacity={0.5} />
      <text x={CS * 2} y={CS * 2 - 6} textAnchor="middle" fontSize={CS * 0.16} fill="var(--color-text-muted)" className="font-mono" opacity={0.8}>RĀŚI</text>
      <text x={CS * 2} y={CS * 2 + CS * 0.18} textAnchor="middle" fontSize={CS * 0.12} fill="var(--color-text-muted)" className="font-mono" opacity={0.65}>D1</text>
      {layout.flatMap((row, ri) =>
        row.map((si, ci) => {
          if (si < 0) return null;
          const x = ci * CS;
          const y = ri * CS;
          const isLagna = si === lagnaSign;
          const planets = occ[si] ?? [];
          const house = ((si - lagnaSign + 12) % 12) + 1;
          const bindu = sav?.[si];
          const expanded = hover === si || focus === si;
          return (
            <g
              key={si}
              tabIndex={0}
              role="button"
              aria-label={`${RASHI_SHORT[si]}, house ${house}${isLagna ? ", Lagna" + (lagnaDeg ? " " + lagnaDeg : "") : ""}${planets.length ? ", " + planets.map((p) => p.short + (p.deg ? " " + p.deg : "")).join(", ") : ""}${bindu != null ? ", " + bindu + " bindus" : ""}`}
              onMouseEnter={() => setHover(si)}
              onMouseLeave={() => setHover(null)}
              onFocus={() => setFocus(si)}
              onBlur={() => setFocus(null)}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setFocus(focus === si ? null : si); }}}
            >
              <rect
                x={x + 1} y={y + 1} width={CS - 2} height={CS - 2} rx={4}
                fill={expanded ? "color-mix(in srgb, var(--color-accent) 16%, transparent)" : isLagna ? "color-mix(in srgb, var(--color-accent) 9%, transparent)" : "transparent"}
                stroke={isLagna ? "var(--color-accent)" : expanded ? "color-mix(in srgb, var(--color-accent) 50%, transparent)" : "transparent"}
                strokeWidth={isLagna ? 1.5 : expanded ? 1 : 0}
              />
              {/* Elemental accent (Fire/Earth/Air/Water) — a quiet color
                  signal along each box's top edge, independent of the
                  Lagna/hover highlight above. */}
              <rect x={x + 5} y={y + 3} width={CS - 10} height={2.5} rx={1.25} fill={elementColor(si)} opacity={0.65} />
              <text x={x + 6} y={y + CS * 0.24} fontSize={CS * 0.16} fill={isLagna ? "var(--color-accent)" : "var(--color-text-main)"} className="font-mono" fontWeight={isLagna ? 700 : 500}>
                {RASHI_SHORT[si]}
              </text>
              <text x={x + CS - 5} y={y + CS * 0.2} textAnchor="end" fontSize={CS * 0.135} fill="var(--color-text-muted)" className="font-mono">{house}</text>
              <PlanetStack planets={planets} expanded={expanded} x={x + CS / 2} y={y + CS * 0.55} w={CS - 8} fontSize={CS * 0.155} />
              {isLagna && !expanded && (
                <text x={x + CS / 2} y={y + CS - 7} textAnchor="middle" fontSize={CS * 0.12} fill="var(--color-accent)" className="font-mono" letterSpacing="0.06em">LAGNA</text>
              )}
              {isLagna && expanded && lagnaDeg && (
                <text x={x + CS / 2} y={y + CS - 7} textAnchor="middle" fontSize={CS * 0.11} fill="var(--color-accent)" className="font-mono" letterSpacing="0.03em">ASC {lagnaDeg}</text>
              )}
              {bindu != null && (
                <text x={x + 6} y={y + CS - 7} fontSize={CS * 0.13} fill={savColor(bindu)} className="font-mono" fontWeight={700}>{bindu}</text>
              )}
            </g>
          );
        }),
      )}
      <rect width={size} height={size} rx={10} fill="none" stroke="var(--color-hairline)" strokeWidth={1.5} />
    </svg>
  );
}

function NorthChart({ size, occ, lagnaSign, lagnaDeg, sav, hover, setHover, focus, setFocus, className }: InnerProps) {
  const S = size;
  const q = S / 4;
  const h = S / 2;
  const hs = (house: number) => (lagnaSign + house - 1) % 12;

  const ct: [number, number] = [h, 0];
  const cr: [number, number] = [S, h];
  const cb: [number, number] = [h, S];
  const cl: [number, number] = [0, h];
  const ctr: [number, number] = [h, h];
  const tl: [number, number] = [q, q];
  const tr: [number, number] = [3 * q, q];
  const br: [number, number] = [3 * q, 3 * q];
  const bl: [number, number] = [q, 3 * q];

  // [houseNum, polygon points, centroidX, centroidY]
  const houses: [number, [number, number][], number, number][] = [
    [1, [ct, tr, ctr, tl], h, q],
    [4, [cl, tl, ctr, bl], q, h],
    [7, [cb, bl, ctr, br], h, 3 * q],
    [10, [cr, br, ctr, tr], 3 * q, h],
    [2, [[0, 0], ct, tl], q, q / 3],
    [3, [[0, 0], tl, cl], q / 3, q],
    [5, [[0, S], cl, bl], q / 3, 3 * q],
    [6, [[0, S], bl, cb], q, S - q / 3],
    [8, [[S, S], cb, br], 3 * q, S - q / 3],
    [9, [[S, S], br, cr], S - q / 3, 3 * q],
    [11, [[S, 0], cr, tr], S - q / 3, q],
    [12, [[S, 0], tr, ct], 3 * q, q / 3],
  ];

  const isKendra = (hn: number) => [1, 4, 7, 10].includes(hn);

  return (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`} className={className} role="img" aria-label={`North Indian kundali, Lagna in ${RASHI_SHORT[lagnaSign]}`}>
      <rect width={S} height={S} rx={10} fill="var(--color-card)" />
      <polygon points={[ct, cr, cb, cl].map((p) => p.join(",")).join(" ")} fill="none" stroke={GRID} />
      <line x1={0} y1={0} x2={S} y2={S} stroke={GRID} />
      <line x1={S} y1={0} x2={0} y2={S} stroke={GRID} />
      {houses.map(([hn, pts, cx, cy]) => {
        const si = hs(hn);
        const isLagna = hn === 1;
        const planets = occ[si] ?? [];
        const bindu = sav?.[si];
        const kendra = isKendra(hn);
        const fSign = S * (kendra ? 0.05 : 0.042);
        const fPl = S * (kendra ? 0.052 : 0.044);
        const expanded = hover === si || focus === si;
        return (
          <g
            key={hn}
            tabIndex={0}
            role="button"
            aria-label={`House ${hn}, ${RASHI_SHORT[si]}${isLagna ? ", Lagna" + (lagnaDeg ? " " + lagnaDeg : "") : ""}${planets.length ? ", " + planets.map((p) => p.short + (p.deg ? " " + p.deg : "")).join(", ") : ""}${bindu != null ? ", " + bindu + " bindus" : ""}`}
            onMouseEnter={() => setHover(si)}
            onMouseLeave={() => setHover(null)}
            onFocus={() => setFocus(si)}
            onBlur={() => setFocus(null)}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setFocus(focus === si ? null : si); }}}
          >
            <polygon
              points={pts.map((p) => p.join(",")).join(" ")}
              fill={expanded ? "color-mix(in srgb, var(--color-accent) 16%, transparent)" : isLagna ? "color-mix(in srgb, var(--color-accent) 9%, transparent)" : "transparent"}
              stroke={isLagna ? "var(--color-accent)" : expanded ? "color-mix(in srgb, var(--color-accent) 50%, transparent)" : "transparent"}
              strokeWidth={isLagna ? 1.5 : expanded ? 1 : 0}
            />
            <text x={cx} y={cy - fPl * 1.1} textAnchor="middle" fontSize={S * 0.036} fill="var(--color-text-muted)" fontWeight={600} className="font-mono">{hn}</text>
            {/* Elemental accent (Fire/Earth/Air/Water) — polygon house shapes
                don't take a clean border strip like the South chart's square
                cells, so a small dot next to the sign label carries it instead. */}
            <circle cx={cx - fSign * 1.3} cy={cy - fPl * 0.14} r={S * 0.011} fill={elementColor(si)} opacity={0.75} />
            <text x={cx} y={cy - fPl * 0.1} textAnchor="middle" fontSize={fSign} fill={isLagna ? "var(--color-accent)" : "var(--color-text-main)"} className="font-mono" fontWeight={isLagna ? 700 : 500}>{RASHI_SHORT[si]}</text>
            <PlanetStack planets={planets} expanded={expanded} x={cx} y={cy + fPl + 2} w={kendra ? S * 0.34 : S * 0.22} fontSize={fPl} />
            {isLagna && expanded && lagnaDeg && (
              <text x={cx} y={cy + fPl * 2.6} textAnchor="middle" fontSize={S * 0.028} fill="var(--color-accent)" className="font-mono" letterSpacing="0.03em">ASC {lagnaDeg}</text>
            )}
            {bindu != null && (
              <text x={cx} y={cy + fPl * 2.6} textAnchor="middle" fontSize={S * 0.03} fill={savColor(bindu)} className="font-mono" fontWeight={700}>{bindu}b</text>
            )}
          </g>
        );
      })}
      <rect width={S} height={S} rx={10} fill="none" stroke="var(--color-hairline)" strokeWidth={1.5} />
    </svg>
  );
}
