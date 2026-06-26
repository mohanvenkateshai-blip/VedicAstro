"use client";

import { useState, useEffect, useCallback } from "react";
import { Clock, Loader, AlertCircle } from "lucide-react";
import { motion } from "motion/react";
import type { ChartData } from "@/lib/types";

// ── Types ───────────────────────────────────────────────────────────────────

interface DashaItem {
  maha: string | null;
  antara: string | null;
}

interface YoginiPeriod {
  lord: string;
  startYear: number;
  durationYears: number;
}

interface DashaSystemsData {
  vimshottari?: DashaItem;
  yogini?: DashaItem & { upcoming?: YoginiPeriod[] };
  ashtottari?: DashaItem;
}

// ── Constants ───────────────────────────────────────────────────────────────

const CVCE_URL =
  process.env.NEXT_PUBLIC_CVCE_BASE_URL ?? "https://vedicastro-cvce.fly.dev";

const THEMES = {
  vimshottari: {
    label: "Vimshottari",
    color: "#7c3aed",
    bg: "rgba(124, 58, 237, 0.08)",
    border: "rgba(124, 58, 237, 0.30)",
    tagBg: "rgba(124, 58, 237, 0.14)",
  },
  yogini: {
    label: "Yogini",
    color: "#5EE6D0",
    bg: "rgba(94, 230, 208, 0.08)",
    border: "rgba(94, 230, 208, 0.30)",
    tagBg: "rgba(94, 230, 208, 0.14)",
  },
  ashtottari: {
    label: "Ashtottari",
    color: "#fbbf24",
    bg: "rgba(251, 191, 36, 0.08)",
    border: "rgba(251, 191, 36, 0.30)",
    tagBg: "rgba(251, 191, 36, 0.14)",
  },
} as const;

type DashaKey = keyof typeof THEMES;

const KEYS: DashaKey[] = ["vimshottari", "yogini", "ashtottari"];

// ── Sub-components ──────────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="rounded-2xl border border-hairline bg-card p-5">
      <div className="h-5 w-24 rounded-md animate-pulse bg-hairline mb-4" />
      <div className="space-y-3">
        <div className="h-4 w-32 rounded-md animate-pulse bg-hairline" />
        <div className="h-4 w-20 rounded-md animate-pulse bg-hairline" />
      </div>
    </div>
  );
}

function DashaCard({
  dashaKey,
  data,
}: {
  dashaKey: DashaKey;
  data: DashaItem & { upcoming?: YoginiPeriod[] };
}) {
  const t = THEMES[dashaKey];

  return (
    <motion.div
      className="rounded-2xl border p-5 flex flex-col"
      style={{
        backgroundColor: "var(--color-card)",
        borderColor: t.border,
        boxShadow: `inset 0 0 0 1px ${t.border}`,
      }}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
    >
      <div className="flex items-center justify-between mb-4">
        <h3
          className="font-[family-name:var(--font-display)] text-base font-semibold tracking-tight"
          style={{ color: t.color }}
        >
          {t.label}
        </h3>
      </div>

      {data.maha ? (
        <div className="flex-1 space-y-3">
          <div className="flex items-center gap-2.5">
            <span
              className="text-[11px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-md"
              style={{
                backgroundColor: t.tagBg,
                color: t.color,
              }}
            >
              Maha
            </span>
            <span
              className="text-sm font-semibold"
              style={{ color: "var(--color-text-main)" }}
            >
              {data.maha}
            </span>
          </div>

          {data.antara && (
            <div className="flex items-center gap-2.5">
              <span
                className="text-[11px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-md"
                style={{
                  backgroundColor: t.tagBg,
                  color: t.color,
                }}
              >
                Antar
              </span>
              <span
                className="text-sm font-medium"
                style={{ color: "var(--color-text-main)" }}
              >
                {data.antara}
              </span>
            </div>
          )}

          {data.upcoming && data.upcoming.length > 0 && (
            <div className="mt-4 pt-4" style={{ borderTop: "1px solid var(--color-hairline)" }}>
              <p
                className="text-[11px] font-mono uppercase tracking-wider mb-2.5"
                style={{ color: "var(--color-text-muted)" }}
              >
                Upcoming
              </p>
              <div className="overflow-x-auto -mx-1 px-1">
                <table className="w-full text-xs">
                  <thead>
                    <tr
                      className="text-left"
                      style={{ borderBottom: "1px solid var(--color-hairline)" }}
                    >
                      <th
                        className="pb-1.5 font-mono font-normal"
                        style={{ color: "var(--color-text-muted)" }}
                      >
                        Lord
                      </th>
                      <th
                        className="pb-1.5 font-mono font-normal"
                        style={{ color: "var(--color-text-muted)" }}
                      >
                        Start
                      </th>
                      <th
                        className="pb-1.5 font-mono font-normal text-right"
                        style={{ color: "var(--color-text-muted)" }}
                      >
                        Dur
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.upcoming.map((p, i) => (
                      <tr
                        key={i}
                        style={{ borderBottom: "1px solid var(--color-hairline)" }}
                      >
                        <td
                          className="py-1.5 font-mono font-medium"
                          style={{ color: t.color }}
                        >
                          {p.lord}
                        </td>
                        <td
                          className="py-1.5 font-mono tabular-nums"
                          style={{ color: "var(--color-text-main)" }}
                        >
                          {p.startYear}
                        </td>
                        <td
                          className="py-1.5 font-mono tabular-nums text-right"
                          style={{ color: "var(--color-text-muted)" }}
                        >
                          {p.durationYears}y
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {!data.maha && !data.antara && (
            <p
              className="text-xs"
              style={{ color: "var(--color-text-muted)" }}
            >
              No active period data
            </p>
          )}
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <p
            className="text-xs text-center py-4"
            style={{ color: "var(--color-text-muted)" }}
          >
            Not available for this chart
          </p>
        </div>
      )}
    </motion.div>
  );
}

// ── Main component ──────────────────────────────────────────────────────────

export function AllDashasPanel({ chart }: { chart?: ChartData }) {
  const [data, setData] = useState<DashaSystemsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDashas = useCallback(async () => {
    if (!chart?.meta?.birth_datetime) return;

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${CVCE_URL}/dashas`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          birth_datetime: chart.meta.birth_datetime,
          birth_lat: chart.meta.birth_lat,
          birth_lon: chart.meta.birth_lon,
          birth_tz: chart.meta.birth_tz,
        }),
      });

      if (!res.ok) {
        throw new Error(`Engine returned ${res.status}`);
      }

      const json: any = await res.json();
      setData(json.dashas ?? json);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dasha data");
    } finally {
      setLoading(false);
    }
  }, [chart]);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      if (!chart?.meta?.birth_datetime) return;
      setLoading(true);
      setError(null);
      setData(null);

      try {
        const res = await fetch(`${CVCE_URL}/dashas`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            birth_datetime: chart.meta.birth_datetime,
            birth_lat: chart.meta.birth_lat,
            birth_lon: chart.meta.birth_lon,
            birth_tz: chart.meta.birth_tz,
          }),
        });

        if (!res.ok) {
          throw new Error(`Engine returned ${res.status}`);
        }

        const json: any = await res.json();
        if (!cancelled) {
          setData(json.dashas ?? json);
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

    run();
    return () => {
      cancelled = true;
    };
  }, [
    chart?.meta?.birth_datetime,
    chart?.meta?.birth_lat,
    chart?.meta?.birth_lon,
    chart?.meta?.birth_tz,
  ]);

  if (!chart) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-16 text-text-muted">
        <Clock className="h-5 w-5" />
        <span className="text-sm font-mono">No chart data provided</span>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16 text-text-muted">
        <div className="flex items-center gap-2">
          <AlertCircle
            className="h-5 w-5"
            style={{ color: "var(--color-danger)" }}
          />
          <span className="text-sm font-mono">Could not load dasha data</span>
        </div>
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
          onClick={fetchDashas}
          className="mt-2 text-xs font-mono px-4 py-1.5 rounded-lg border transition-colors duration-200 hover:bg-card"
          style={{ borderColor: "var(--color-hairline)", color: "var(--color-text-main)" }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {KEYS.map((key) => (
        <DashaCard key={key} dashaKey={key} data={data?.[key] ?? { maha: null, antara: null }} />
      ))}
    </div>
  );
}
