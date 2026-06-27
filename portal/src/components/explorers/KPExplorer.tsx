"use client";

import { useState, useEffect, useMemo } from "react";
import { Loader, Star, Target } from "lucide-react";
import { clsx } from "clsx";
import type { ChartData } from "@/lib/types";
import { postCvce } from "@/lib/cvce-client";

interface KPCusp {
  bhava: number;
  cusp_label: string;
  star_lord: string;
  sub_lord: string;
  sub_sub_lord: string;
}

interface KPPlanet {
  planet: string;
  rashi_label: string;
  retro: boolean;
  bhava: number;
  star_lord: string;
  sub_lord: string;
}

interface KPSystemResponse {
  cusps: KPCusp[];
  planets: KPPlanet[];
}

const STAR_LORD_COLOR = "#c5a46e";
const SUB_LORD_COLOR = "#7c3aed";
const SUB_SUB_LORD_COLOR = "#5EE6D0";

const PLANET_ORDER = [
  "Sun",
  "Moon",
  "Mars",
  "Mercury",
  "Jupiter",
  "Venus",
  "Saturn",
  "Rahu",
  "Ketu",
  "Lagna",
];

function SkeletonTable({
  columns,
  rows,
}: {
  columns: number;
  rows: number;
}) {
  return (
    <div className="rounded-xl border border-hairline bg-card overflow-x-auto">
      <table className="w-full text-xs" aria-hidden>
        <thead>
          <tr className="border-b border-hairline">
            {Array.from({ length: columns }).map((_, i) => (
              <th
                key={i}
                className="px-3 py-2.5 text-left"
                style={{ backgroundColor: "var(--color-hairline)" }}
              >
                <span className="block h-3.5 rounded animate-pulse w-12" />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, ri) => (
            <tr
              key={ri}
              className={clsx(
                "border-b border-hairline/60 last:border-0",
                ri % 2 === 1 && "bg-[color-mix(in_srgb,var(--color-accent)_3%,transparent)]",
              )}
            >
              {Array.from({ length: columns }).map((_, ci) => (
                <td key={ci} className="px-3 py-2.5">
                  <span
                    className="block h-3 rounded animate-pulse"
                    style={{
                      width: `${40 + Math.random() * 40}px`,
                      backgroundColor: "var(--color-hairline)",
                    }}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function tableCellStyle(color?: string): React.CSSProperties {
  return color ? { color, fontWeight: 500 } : {};
}

/** CVCE returns camelCase; normalize for the table UI. */
function normalizeKP(raw: Record<string, unknown>): KPSystemResponse {
  const cuspsRaw = (raw.cusps as Record<string, unknown>[]) ?? [];
  const planetsRaw = (raw.planets as Record<string, unknown>[]) ?? [];

  const cusps: KPCusp[] = cuspsRaw.map((c, i) => {
    const rashi = String(c.rashi ?? "");
    const degLabel = String(c.degLabel ?? "");
    return {
      bhava: Number(c.bhava ?? i + 1),
      cusp_label:
        String(c.cusp_label ?? "") ||
        (rashi && degLabel ? `${rashi} ${degLabel}` : rashi || "—"),
      star_lord: String(c.star_lord ?? c.starLord ?? ""),
      sub_lord: String(c.sub_lord ?? c.subLord ?? ""),
      sub_sub_lord: String(c.sub_sub_lord ?? c.subSubLord ?? ""),
    };
  });

  const planets: KPPlanet[] = planetsRaw.map((p) => {
    const rashi = String(p.rashi ?? "");
    const degLabel = String(p.degLabel ?? "");
    return {
      planet: String(p.planet ?? p.name ?? ""),
      rashi_label:
        String(p.rashi_label ?? "") ||
        (rashi && degLabel ? `${rashi} ${degLabel}` : rashi || "—"),
      retro: Boolean(p.retro),
      bhava: Number(p.bhava ?? 0),
      star_lord: String(p.star_lord ?? p.starLord ?? ""),
      sub_lord: String(p.sub_lord ?? p.subLord ?? ""),
    };
  });

  return { cusps, planets };
}

export function KPExplorer({ chart }: { chart?: ChartData }) {
  const [data, setData] = useState<KPSystemResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    const meta = chart?.meta;
    if (!meta?.birth_datetime) return;

    let cancelled = false;

    const { birth_datetime, birth_lat, birth_lon, birth_tz } = meta;

    async function fetchKP() {
      setLoading(true);
      setError(null);
      setData(null);

      try {
        const json = await postCvce<Record<string, unknown>>("kp-system", {
          birth_datetime,
          birth_lat,
          birth_lon,
          birth_tz,
        });
        if (!cancelled) {
          setData(normalizeKP(json));
        }
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof Error ? e.message : "Failed to load KP data",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchKP();
    return () => {
      cancelled = true;
    };
  }, [
    chart?.meta?.birth_datetime,
    chart?.meta?.birth_lat,
    chart?.meta?.birth_lon,
    chart?.meta?.birth_tz,
    retryKey,
  ]);

  const significations = useMemo(() => {
    if (!data?.cusps) return [];

    const byPlanet = new Map<
      string,
      { starLordOf: number[]; subLordOf: number[] }
    >();

    for (const c of data.cusps) {
      if (c.star_lord) {
        const entry = byPlanet.get(c.star_lord) ?? {
          starLordOf: [],
          subLordOf: [],
        };
        if (!entry.starLordOf.includes(c.bhava)) {
          entry.starLordOf.push(c.bhava);
        }
        byPlanet.set(c.star_lord, entry);
      }

      if (c.sub_lord) {
        const entry = byPlanet.get(c.sub_lord) ?? {
          starLordOf: [],
          subLordOf: [],
        };
        if (!entry.subLordOf.includes(c.bhava)) {
          entry.subLordOf.push(c.bhava);
        }
        byPlanet.set(c.sub_lord, entry);
      }
    }

    return Array.from(byPlanet.entries())
      .map(([planet, { starLordOf, subLordOf }]) => ({
        planet,
        starLordOf: starLordOf.sort((a, b) => a - b),
        subLordOf: subLordOf.sort((a, b) => a - b),
        allHouses: [...new Set([...starLordOf, ...subLordOf])].sort(
          (a, b) => a - b,
        ),
      }))
      .sort(
        (a, b) =>
          PLANET_ORDER.indexOf(a.planet) - PLANET_ORDER.indexOf(b.planet),
      );
  }, [data?.cusps]);

  const sortedPlanets = useMemo(() => {
    if (!data?.planets) return [];
    return [...data.planets].sort((a, b) => {
      const ai = PLANET_ORDER.indexOf(a.planet);
      const bi = PLANET_ORDER.indexOf(b.planet);
      if (ai === -1 && bi === -1) return 0;
      if (ai === -1) return 1;
      if (bi === -1) return -1;
      return ai - bi;
    });
  }, [data?.planets]);

  if (!chart) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-16 text-text-muted">
        <Target className="h-5 w-5" />
        <span className="text-sm font-mono">
          No chart data provided
        </span>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div>
          <div className="flex items-center gap-2.5 mb-3">
            <Loader className="h-4 w-4 animate-spin text-accent" />
            <span className="text-[10px] font-mono uppercase tracking-wider text-text-muted">
              Loading cusps
            </span>
          </div>
          <SkeletonTable columns={5} rows={12} />
        </div>
        <div>
          <div className="flex items-center gap-2.5 mb-3">
            <Loader className="h-4 w-4 animate-spin text-accent" />
            <span className="text-[10px] font-mono uppercase tracking-wider text-text-muted">
              Loading planets
            </span>
          </div>
          <SkeletonTable columns={6} rows={10} />
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="rounded-2xl border border-hairline bg-card p-10">
        <div className="flex flex-col items-center justify-center gap-3 text-text-muted">
          <Target className="h-6 w-6 text-danger/60" />
          <p className="text-sm font-mono">Could not load KP data</p>
          <span
            className="text-xs font-mono px-3 py-1 rounded-md"
            style={{
              backgroundColor: "rgba(185, 28, 28, 0.08)",
              color: "var(--color-danger)",
            }}
          >
            {error}
          </span>
          <button
            onClick={() => setRetryKey((k) => k + 1)}
            className="mt-2 text-xs font-mono px-4 py-1.5 rounded-lg border border-hairline text-text-main hover:bg-card transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* ── Tables grid ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
        {/* ── House Cusps table ──────────────────────────────────────── */}
        <div className="rounded-xl border border-hairline bg-card overflow-x-auto">
          <table
            className="w-full text-xs"
            aria-label="KP House Cusps - Placidus cusps with star lords, sub lords, and sub-sub lords"
          >
            <thead>
              <tr className="text-[10px] uppercase tracking-wider text-text-muted border-b border-hairline">
                <th
                  scope="col"
                  className="px-3 py-2.5 text-left font-medium whitespace-nowrap"
                >
                  Bhava
                </th>
                <th
                  scope="col"
                  className="px-3 py-2.5 text-left font-medium whitespace-nowrap"
                >
                  Cusp
                </th>
                <th
                  scope="col"
                  className="px-3 py-2.5 text-left font-medium whitespace-nowrap"
                  style={{ color: STAR_LORD_COLOR }}
                >
                  Star Lord
                </th>
                <th
                  scope="col"
                  className="px-3 py-2.5 text-left font-medium whitespace-nowrap"
                  style={{ color: SUB_LORD_COLOR }}
                >
                  Sub Lord
                </th>
                <th
                  scope="col"
                  className="px-3 py-2.5 text-left font-medium whitespace-nowrap"
                  style={{ color: SUB_SUB_LORD_COLOR }}
                >
                  Sub-Sub Lord
                </th>
              </tr>
            </thead>
            <tbody>
              {(data?.cusps ?? []).map((c, i) => {
                const isLagna = c.bhava === 1;

                return (
                  <tr
                    key={c.bhava}
                    className={clsx(
                      "border-b border-hairline/60 last:border-0 transition-colors hover:bg-[color-mix(in_srgb,var(--color-accent)_4%,transparent)]",
                      i % 2 === 1 &&
                        "bg-[color-mix(in_srgb,var(--color-accent)_2%,transparent)]",
                    )}
                    style={
                      isLagna
                        ? {
                            borderLeft: `3px solid var(--color-accent-strong)`,
                          }
                        : undefined
                    }
                  >
                    <td
                      className={clsx(
                        "px-3 py-2.5 font-mono tabular-nums",
                        isLagna
                          ? "font-bold"
                          : "font-medium text-text-main",
                      )}
                      style={
                        isLagna
                          ? { color: "var(--color-accent-strong)" }
                          : undefined
                      }
                    >
                      {c.bhava}
                    </td>
                    <td className="px-3 py-2.5 font-mono tabular-nums text-text-main">
                      {c.cusp_label}
                    </td>
                    <td
                      className="px-3 py-2.5 font-medium whitespace-nowrap"
                      style={tableCellStyle(STAR_LORD_COLOR)}
                    >
                      {c.star_lord || "—"}
                    </td>
                    <td
                      className="px-3 py-2.5 font-medium whitespace-nowrap"
                      style={tableCellStyle(SUB_LORD_COLOR)}
                    >
                      {c.sub_lord || "—"}
                    </td>
                    <td
                      className="px-3 py-2.5 whitespace-nowrap"
                      style={tableCellStyle(SUB_SUB_LORD_COLOR)}
                    >
                      {c.sub_sub_lord || "—"}
                    </td>
                  </tr>
                );
              })}

              {(!data?.cusps || data.cusps.length === 0) && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-3 py-10 text-center text-text-muted"
                  >
                    No cusp data available
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* ── Planets with KP Data table ────────────────────────────── */}
        <div className="rounded-xl border border-hairline bg-card overflow-x-auto">
          <table
            className="w-full text-xs"
            aria-label="KP Planets - planetary positions with star lords and sub lords"
          >
            <thead>
              <tr className="text-[10px] uppercase tracking-wider text-text-muted border-b border-hairline">
                <th
                  scope="col"
                  className="px-3 py-2.5 text-left font-medium whitespace-nowrap"
                >
                  Planet
                </th>
                <th
                  scope="col"
                  className="px-3 py-2.5 text-left font-medium whitespace-nowrap"
                >
                  Rashi + Deg
                </th>
                <th
                  scope="col"
                  className="px-3 py-2.5 text-left font-medium whitespace-nowrap"
                >
                  R
                </th>
                <th
                  scope="col"
                  className="px-3 py-2.5 text-left font-medium whitespace-nowrap"
                >
                  Bhava
                </th>
                <th
                  scope="col"
                  className="px-3 py-2.5 text-left font-medium whitespace-nowrap"
                  style={{ color: STAR_LORD_COLOR }}
                >
                  Star Lord
                </th>
                <th
                  scope="col"
                  className="px-3 py-2.5 text-left font-medium whitespace-nowrap"
                  style={{ color: SUB_LORD_COLOR }}
                >
                  Sub Lord
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedPlanets.map((p, i) => {
                const isLagna = p.planet === "Lagna" || p.planet === "Ascendant";

                return (
                  <tr
                    key={p.planet}
                    className={clsx(
                      "border-b border-hairline/60 last:border-0 transition-colors hover:bg-[color-mix(in_srgb,var(--color-accent)_4%,transparent)]",
                      i % 2 === 1 &&
                        "bg-[color-mix(in_srgb,var(--color-accent)_2%,transparent)]",
                    )}
                    style={
                      isLagna
                        ? {
                            borderLeft:
                              "3px solid var(--color-accent-strong)",
                          }
                        : undefined
                    }
                  >
                    <td
                      className={clsx(
                        "px-3 py-2.5 font-medium whitespace-nowrap",
                        isLagna
                          ? "font-bold"
                          : "text-text-main",
                      )}
                      style={
                        isLagna
                          ? { color: "var(--color-accent-strong)" }
                          : undefined
                      }
                    >
                      {p.planet}
                    </td>
                    <td className="px-3 py-2.5 font-mono tabular-nums text-text-main">
                      {p.rashi_label}
                    </td>
                    <td className="px-3 py-2.5 font-mono tabular-nums text-center">
                      {p.retro ? (
                        <span className="text-warning font-medium">
                          ℞
                        </span>
                      ) : (
                        <span className="text-text-muted">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5 font-mono tabular-nums font-medium text-text-main">
                      {p.bhava}
                    </td>
                    <td
                      className="px-3 py-2.5 font-medium whitespace-nowrap"
                      style={tableCellStyle(STAR_LORD_COLOR)}
                    >
                      {p.star_lord || "—"}
                    </td>
                    <td
                      className="px-3 py-2.5 font-medium whitespace-nowrap"
                      style={tableCellStyle(SUB_LORD_COLOR)}
                    >
                      {p.sub_lord || "—"}
                    </td>
                  </tr>
                );
              })}

              {sortedPlanets.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-3 py-10 text-center text-text-muted"
                  >
                    No planet data available
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Signification Summary ────────────────────────────────────── */}
      {significations.length > 0 && (
        <div className="rounded-2xl border border-hairline bg-card p-6">
          <div className="flex items-center gap-2.5 mb-5">
            <Star
              className="h-5 w-5 shrink-0"
              style={{ color: STAR_LORD_COLOR }}
            />
            <h3 className="font-[family-name:var(--font-display)] text-base font-semibold tracking-tight text-text-main">
              Signification Summary
            </h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
            {significations.map((entry) => (
              <div
                key={entry.planet}
                className="rounded-xl border border-hairline bg-[color-mix(in_srgb,var(--color-accent)_3%,transparent)] p-4"
              >
                <div className="flex items-center gap-2 mb-3">
                  <Star
                    className="h-3.5 w-3.5 shrink-0"
                    style={{ color: STAR_LORD_COLOR }}
                  />
                  <span className="text-sm font-semibold text-text-main">
                    {entry.planet}
                  </span>
                </div>

                {entry.starLordOf.length > 0 && (
                  <div className="mb-1.5">
                    <span
                      className="text-[10px] font-medium"
                      style={{ color: STAR_LORD_COLOR }}
                    >
                      Star Lord of
                    </span>
                    <p className="text-[11px] text-text-muted mt-0.5">
                      {entry.starLordOf.map((h) => `Bh ${h}`).join(", ")}
                    </p>
                  </div>
                )}

                {entry.subLordOf.length > 0 && (
                  <div>
                    <span
                      className="text-[10px] font-medium"
                      style={{ color: SUB_LORD_COLOR }}
                    >
                      Sub Lord of
                    </span>
                    <p className="text-[11px] text-text-muted mt-0.5">
                      {entry.subLordOf.map((h) => `Bh ${h}`).join(", ")}
                    </p>
                  </div>
                )}

                {entry.starLordOf.length === 0 &&
                  entry.subLordOf.length === 0 && (
                    <p className="text-[11px] text-text-muted italic">
                      No significations
                    </p>
                  )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
