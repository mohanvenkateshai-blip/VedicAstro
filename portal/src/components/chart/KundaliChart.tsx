"use client";

import { useMemo, useState } from "react";
import { RASHI_SHORT, PLANET_SHORT, type SignIndex } from "@/lib/types";

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
  size?: number;
  className?: string;
}

const PLANET_ORDER = [
  "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu",
];

function occupantsBySign(signs: Record<string, SignIndex>) {
  const map: Record<number, string[]> = {};
  for (const p of PLANET_ORDER) {
    const s = signs[p];
    if (s == null) continue;
    (map[s] ??= []).push(PLANET_SHORT[p] ?? p.slice(0, 2));
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
  size = 340,
  className,
}: Props) {
  const lagnaSign = signs.Lagna ?? signs.Ascendant ?? 0;
  const occ = useMemo(() => occupantsBySign(signs), [signs]);
  const [hover, setHover] = useState<number | null>(null);
  const [focus, setFocus] = useState<number | null>(null);

  const props: InnerProps = {
    size, occ, lagnaSign, sav, hover, setHover, focus, setFocus, className,
  };

  return variant === "south" ? <SouthChart {...props} /> : <NorthChart {...props} />;
}

interface InnerProps {
  size: number;
  occ: Record<number, string[]>;
  lagnaSign: number;
  sav?: number[];
  hover: number | null;
  setHover: (n: number | null) => void;
  focus: number | null;
  setFocus: (n: number | null) => void;
  className?: string;
}

const GRID = "var(--color-hairline)";

function PlanetStack({
  planets, x, y, w, fontSize,
}: { planets: string[]; x: number; y: number; w: number; fontSize: number }) {
  if (!planets.length) return null;
  const perRow = Math.max(2, Math.floor(w / (fontSize * 1.6)));
  const rows: string[][] = [];
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
          fontWeight={600}
          fill="var(--color-card-fg)"
          className="font-mono"
        >
          {row.join(" ")}
        </text>
      ))}
    </>
  );
}

function SouthChart({ size, occ, lagnaSign, sav, hover, setHover, focus, setFocus, className }: InnerProps) {
  const CS = size / 4;
  const layout = [
    [11, 0, 1, 2],
    [10, -1, -1, 3],
    [9, -1, -1, 4],
    [8, 7, 6, 5],
  ];
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className={className} role="img" aria-label={`South Indian kundali, Lagna in ${RASHI_SHORT[lagnaSign]}`}>
      <rect width={size} height={size} rx={10} fill="var(--color-card)" />
      {[1, 2, 3].map((i) => (
        <g key={i}>
          <line x1={i * CS} y1={0} x2={i * CS} y2={size} stroke={GRID} />
          <line x1={0} y1={i * CS} x2={size} y2={i * CS} stroke={GRID} />
        </g>
      ))}
      <rect x={CS} y={CS} width={CS * 2} height={CS * 2} fill="var(--color-background)" opacity={0.5} />
      <text x={CS * 2} y={CS * 2 - 6} textAnchor="middle" fontSize={CS * 0.16} fill="var(--color-text-muted)" className="font-mono" opacity={0.7}>RĀŚI</text>
      <text x={CS * 2} y={CS * 2 + CS * 0.18} textAnchor="middle" fontSize={CS * 0.12} fill="var(--color-text-muted)" className="font-mono" opacity={0.5}>D1</text>
      {layout.flatMap((row, ri) =>
        row.map((si, ci) => {
          if (si < 0) return null;
          const x = ci * CS;
          const y = ri * CS;
          const isLagna = si === lagnaSign;
          const planets = occ[si] ?? [];
          const house = ((si - lagnaSign + 12) % 12) + 1;
          const bindu = sav?.[si];
          return (
            <g
              key={si}
              tabIndex={0}
              role="button"
              aria-label={`${RASHI_SHORT[si]}, house ${house}${isLagna ? ", Lagna" : ""}${planets.length ? ", " + planets.join(" ") : ""}${bindu != null ? ", " + bindu + " bindus" : ""}`}
              onMouseEnter={() => setHover(si)}
              onMouseLeave={() => setHover(null)}
              onFocus={() => setFocus(si)}
              onBlur={() => setFocus(null)}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setFocus(focus === si ? null : si); }}}
            >
              <rect
                x={x + 1} y={y + 1} width={CS - 2} height={CS - 2} rx={4}
                fill={(hover === si || focus === si) ? "color-mix(in srgb, var(--color-accent) 12%, transparent)" : isLagna ? "color-mix(in srgb, var(--color-accent) 7%, transparent)" : "transparent"}
                stroke={isLagna ? "var(--color-accent)" : "transparent"}
                strokeWidth={isLagna ? 1.5 : 0}
              />
              <text x={x + 6} y={y + CS * 0.2} fontSize={CS * 0.15} fill={isLagna ? "var(--color-accent)" : "var(--color-text-muted)"} className="font-mono" fontWeight={isLagna ? 700 : 400}>
                {RASHI_SHORT[si]}
              </text>
              <text x={x + CS - 5} y={y + CS * 0.2} textAnchor="end" fontSize={CS * 0.12} fill="var(--color-text-muted)" opacity={0.5} className="font-mono">{house}</text>
              <PlanetStack planets={planets} x={x + CS / 2} y={y + CS * 0.55} w={CS - 8} fontSize={CS * 0.155} />
              {isLagna && (
                <text x={x + CS / 2} y={y + CS - 7} textAnchor="middle" fontSize={CS * 0.12} fill="var(--color-accent)" className="font-mono" letterSpacing="0.06em">LAGNA</text>
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

function NorthChart({ size, occ, lagnaSign, sav, hover, setHover, focus, setFocus, className }: InnerProps) {
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
        return (
          <g
            key={hn}
            tabIndex={0}
            role="button"
            aria-label={`House ${hn}, ${RASHI_SHORT[si]}${isLagna ? ", Lagna" : ""}${planets.length ? ", " + planets.join(" ") : ""}${bindu != null ? ", " + bindu + " bindus" : ""}`}
            onMouseEnter={() => setHover(si)}
            onMouseLeave={() => setHover(null)}
            onFocus={() => setFocus(si)}
            onBlur={() => setFocus(null)}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setFocus(focus === si ? null : si); }}}
          >
            <polygon
              points={pts.map((p) => p.join(",")).join(" ")}
              fill={(hover === si || focus === si) ? "color-mix(in srgb, var(--color-accent) 12%, transparent)" : isLagna ? "color-mix(in srgb, var(--color-accent) 7%, transparent)" : "transparent"}
              stroke={isLagna ? "var(--color-accent)" : "transparent"}
              strokeWidth={isLagna ? 1.5 : 0}
            />
            <text x={cx} y={cy - fPl * 1.1} textAnchor="middle" fontSize={S * 0.032} fill="var(--color-text-muted)" opacity={0.6} className="font-mono">{hn}</text>
            <text x={cx} y={cy - fPl * 0.1} textAnchor="middle" fontSize={fSign} fill={isLagna ? "var(--color-accent)" : "var(--color-text-muted)"} className="font-mono" fontWeight={isLagna ? 700 : 400}>{RASHI_SHORT[si]}</text>
            <PlanetStack planets={planets} x={cx} y={cy + fPl + 2} w={kendra ? S * 0.34 : S * 0.22} fontSize={fPl} />
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
