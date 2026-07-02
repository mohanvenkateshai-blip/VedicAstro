"use client";

import { useMemo, useState } from "react";
import { motion } from "motion/react";
import type { KalachakraCycle } from "@/lib/types";
import { leapStyle } from "./kalachakraCopy";

interface Slice {
  index: number;
  sign: string;
  years: number;
  startDeg: number;
  endDeg: number;
  midDeg: number;
  leapType: "frog_leap" | "lions_leap" | "monkey_leap" | null;
}

function sliceAngles(cycle: KalachakraCycle): Slice[] {
  const total = cycle.totalYears || cycle.signs.reduce((s, n) => s + n.years, 0);
  let cursor = 0;
  return cycle.signs.map((n) => {
    const sweep = (n.years / total) * 360;
    const startDeg = cursor;
    const endDeg = cursor + sweep;
    cursor = endDeg;
    return {
      index: n.index,
      sign: n.sign,
      years: n.years,
      startDeg,
      endDeg,
      midDeg: (startDeg + endDeg) / 2,
      leapType: n.leapFromPrevious?.type ?? null,
    };
  });
}

function polar(cx: number, cy: number, r: number, angleDeg: number) {
  // 0deg = top (12 o'clock), clockwise.
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function donutSlicePath(cx: number, cy: number, rOuter: number, rInner: number, startDeg: number, endDeg: number) {
  const largeArc = endDeg - startDeg > 180 ? 1 : 0;
  const o1 = polar(cx, cy, rOuter, startDeg);
  const o2 = polar(cx, cy, rOuter, endDeg);
  const i1 = polar(cx, cy, rInner, endDeg);
  const i2 = polar(cx, cy, rInner, startDeg);
  return [
    `M ${o1.x} ${o1.y}`,
    `A ${rOuter} ${rOuter} 0 ${largeArc} 1 ${o2.x} ${o2.y}`,
    `L ${i1.x} ${i1.y}`,
    `A ${rInner} ${rInner} 0 ${largeArc} 0 ${i2.x} ${i2.y}`,
    "Z",
  ].join(" ");
}

const LEAP_STROKE: Record<string, string> = {
  frog_leap: "var(--color-warning)",
  lions_leap: "var(--color-danger)",
  monkey_leap: "#a78bfa",
};

export function KalachakraWheel({
  cycle,
  currentSign,
}: {
  cycle: KalachakraCycle;
  currentSign?: string | null;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const slices = useMemo(() => sliceAngles(cycle), [cycle]);

  const size = 320;
  const cx = size / 2;
  const cy = size / 2;
  const rOuter = size * 0.46;
  const rInner = size * 0.26;
  const rLabel = (rOuter + rInner) / 2;

  const leapArrows = slices.filter((s) => s.leapType);

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label={`Kalachakra wheel — Deha ${cycle.dehaRasi}, Jeeva ${cycle.jeevaRasi}`}
      className="mx-auto"
    >
      <circle cx={cx} cy={cy} r={rOuter + 1} fill="var(--color-card)" />

      {slices.map((s) => {
        const isCurrent = currentSign === s.sign;
        const isHover = hover === s.index;
        const path = donutSlicePath(cx, cy, rOuter, rInner, s.startDeg + 0.6, s.endDeg - 0.6);
        const style = s.leapType ? leapStyle(s.leapType) : null;
        const pos = polar(cx, cy, rLabel, s.midDeg);

        return (
          <g key={s.index}>
            {isCurrent ? (
              <motion.path
                d={path}
                fill="var(--color-accent)"
                fillOpacity={0.35}
                stroke="var(--color-accent)"
                strokeWidth={1.5}
                animate={{ fillOpacity: [0.2, 0.45, 0.2] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                tabIndex={0}
                role="button"
                aria-label={`${s.sign}, ${s.years} years, currently running`}
                onMouseEnter={() => setHover(s.index)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(s.index)}
                onBlur={() => setHover(null)}
              />
            ) : (
              <path
                d={path}
                fill={
                  isHover
                    ? "color-mix(in srgb, var(--color-accent) 14%, transparent)"
                    : style
                      ? "color-mix(in srgb, var(--color-hairline) 40%, transparent)"
                      : "var(--color-card)"
                }
                stroke="var(--color-hairline)"
                strokeWidth={1}
                tabIndex={0}
                role="button"
                aria-label={`${s.sign}, ${s.years} years${style ? ", " + style.shortLabel : ""}`}
                onMouseEnter={() => setHover(s.index)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(s.index)}
                onBlur={() => setHover(null)}
              />
            )}
            <text
              x={pos.x}
              y={pos.y}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize={11}
              className="font-mono pointer-events-none"
              fill={isCurrent ? "var(--color-accent)" : "var(--color-text-muted)"}
              fontWeight={isCurrent ? 700 : 400}
            >
              {s.sign.slice(0, 3)}
            </text>
          </g>
        );
      })}

      {/* Leap arrows — curved dotted paths through the interior between the
          leaping slice and its previous slice, control point pulled toward center. */}
      {leapArrows.map((s, i) => {
        const prevIdx = slices.findIndex((x) => x.index === s.index) - 1;
        if (prevIdx < 0) return null;
        const from = polar(cx, cy, rInner * 0.85, slices[prevIdx].midDeg);
        const to = polar(cx, cy, rInner * 0.85, s.midDeg);
        const ctrl = { x: cx + (cx - (from.x + to.x) / 2) * -0.3, y: cy + (cy - (from.y + to.y) / 2) * -0.3 };
        return (
          <path
            key={`arrow-${i}`}
            d={`M ${from.x} ${from.y} Q ${ctrl.x} ${ctrl.y} ${to.x} ${to.y}`}
            fill="none"
            stroke={LEAP_STROKE[s.leapType!]}
            strokeWidth={1.5}
            strokeDasharray="3 3"
            opacity={0.7}
            markerEnd="url(#leap-arrowhead)"
          />
        );
      })}

      <defs>
        <marker id="leap-arrowhead" markerWidth="6" markerHeight="6" refX="4" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="var(--color-text-muted)" />
        </marker>
      </defs>

      <circle cx={cx} cy={cy} r={rInner - 2} fill="var(--color-card)" stroke="var(--color-hairline)" strokeWidth={1} />
      <text x={cx} y={cy - 6} textAnchor="middle" fontSize={10} className="font-mono" fill="var(--color-text-muted)" opacity={0.7}>
        DEHA
      </text>
      <text x={cx} y={cy + 8} textAnchor="middle" fontSize={13} fill="var(--color-accent)" fontWeight={600}>
        {cycle.dehaRasi}
      </text>
    </svg>
  );
}
