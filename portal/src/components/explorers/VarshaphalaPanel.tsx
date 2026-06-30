"use client";

import { useState, useEffect, useCallback } from "react";
import { Sun, Calendar, ArrowRight, Loader } from "lucide-react";
import { motion } from "motion/react";
import type { ChartData } from "@/lib/types";
import { postCvce } from "@/lib/cvce-client";

// ── Types ───────────────────────────────────────────────────────────────────

interface VarshaphalaData {
  natalSun?: {
    rashi: string;
    longitude: number;
    degLabel: string;
  };
  solarReturn?: {
    sun?: { rashi: string; degLabel?: string };
    moon?: { rashi: string };
  };
  muntha?: {
    sign: string;
    yearsElapsed: number;
    lord: string;
  };
  ke_version?: string;
}

// ── Constants ───────────────────────────────────────────────────────────────

const ACCENT = "#d4b483";
const ACCENT_STRONG = "#c5a46e";

// ── Sub-components ──────────────────────────────────────────────────────────

function SkeletonLine({ width, height }: { width: string; height?: string }) {
  return (
    <div
      className="rounded-md animate-pulse"
      style={{
        width,
        height: height ?? "0.875rem",
        backgroundColor: "var(--color-hairline)",
      }}
    />
  );
}

function SkeletonCard() {
  return (
    <div className="rounded-2xl border border-hairline bg-card p-6">
      <div className="flex items-center gap-2.5 mb-4">
        <SkeletonLine width="1.25rem" height="1.25rem" />
        <SkeletonLine width="6rem" />
      </div>
      <div className="space-y-3 pl-8">
        <SkeletonLine width="5rem" />
        <SkeletonLine width="4rem" />
      </div>
    </div>
  );
}

// ── Main component ──────────────────────────────────────────────────────────

export function VarshaphalaPanel({ chart }: { chart?: ChartData }) {
  const [data, setData] = useState<VarshaphalaData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchVarshaphala = useCallback(async () => {
    if (!chart?.meta?.birth_datetime) return;

    setLoading(true);
    setError(null);

    try {
      const json = await postCvce<VarshaphalaData>("varshaphala", {
        birth_datetime: chart.meta.birth_datetime,
        birth_lat: chart.meta.birth_lat,
        birth_lon: chart.meta.birth_lon,
        birth_tz: chart.meta.birth_tz,
      });
      setData(json);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Failed to load Varshaphala data",
      );
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
        const json = await postCvce<VarshaphalaData>("varshaphala", {
          birth_datetime: chart.meta.birth_datetime,
          birth_lat: chart.meta.birth_lat,
          birth_lon: chart.meta.birth_lon,
          birth_tz: chart.meta.birth_tz,
        });
        if (!cancelled) {
          setData(json);
        }
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof Error
              ? e.message
              : "Failed to load Varshaphala data",
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
        <Calendar className="h-5 w-5" />
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
        <span className="text-sm font-mono">Could not load Varshaphala data</span>
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
          onClick={fetchVarshaphala}
          className="mt-2 text-xs font-mono px-4 py-1.5 rounded-lg border transition-colors duration-200 hover:bg-card"
          style={{ borderColor: "var(--color-hairline)", color: "var(--color-text-main)" }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <>
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* ── Natal Sun ─────────────────────────────────────────────────── */}
      <motion.div
        className="rounded-2xl border border-hairline bg-card p-6 flex flex-col"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: "easeOut", delay: 0 }}
      >
        <div className="flex items-center gap-2.5 mb-5">
          <Sun
            className="h-5 w-5 shrink-0"
            style={{ color: ACCENT }}
          />
          <h3
            className="font-[family-name:var(--font-display)] text-base font-semibold tracking-tight"
            style={{ color: "var(--color-text-main)" }}
          >
            Natal Sun
          </h3>
        </div>

        {data?.natalSun ? (
          <div className="flex-1 flex flex-col justify-center pl-8 space-y-2">
            <span
              className="text-2xl font-[family-name:var(--font-display)] font-semibold tracking-tight"
              style={{ color: ACCENT_STRONG }}
            >
              {data.natalSun.rashi}
            </span>
            <span
              className="text-sm font-mono"
              style={{ color: "var(--color-text-muted)" }}
            >
              {data.natalSun.degLabel}
            </span>
            <span
              className="text-[11px] font-mono"
              style={{ color: "var(--color-text-muted)" }}
            >
              {data.natalSun.longitude.toFixed(2)}
            </span>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <p
              className="text-xs"
              style={{ color: "var(--color-text-muted)" }}
            >
              Not available
            </p>
          </div>
        )}
      </motion.div>

      {/* ── Solar Return ──────────────────────────────────────────────── */}
      <motion.div
        className="rounded-2xl border border-hairline bg-card p-6 flex flex-col"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: "easeOut", delay: 0.1 }}
      >
        <div className="flex items-center gap-2.5 mb-5">
          <ArrowRight
            className="h-5 w-5 shrink-0"
            style={{ color: ACCENT }}
          />
          <h3
            className="font-[family-name:var(--font-display)] text-base font-semibold tracking-tight"
            style={{ color: "var(--color-text-main)" }}
          >
            Solar Return
          </h3>
        </div>

        {data?.solarReturn ? (
          <div className="flex-1 flex flex-col justify-center pl-8 space-y-4">
            <div className="space-y-1.5">
              <span
                className="text-[10px] font-mono uppercase tracking-wider"
                style={{ color: "var(--color-text-muted)" }}
              >
                Sun
              </span>
              <div className="flex items-baseline gap-2">
                <span
                  className="text-lg font-[family-name:var(--font-display)] font-semibold"
                  style={{ color: ACCENT_STRONG }}
                >
                  {data.solarReturn.sun?.rashi}
                </span>
                <span
                  className="text-xs font-mono"
                  style={{ color: "var(--color-text-muted)" }}
                >
                  {data.solarReturn.sun?.degLabel}
                </span>
              </div>
            </div>

            <div className="space-y-1.5">
              <span
                className="text-[10px] font-mono uppercase tracking-wider"
                style={{ color: "var(--color-text-muted)" }}
              >
                Moon
              </span>
              <div className="flex items-baseline gap-2">
                <span
                  className="text-lg font-[family-name:var(--font-display)] font-semibold"
                  style={{ color: ACCENT_STRONG }}
                >
                  {data.solarReturn.moon?.rashi}
                </span>
                <span
                  className="text-xs font-mono"
                  style={{ color: "var(--color-text-muted)" }}
                >
                  {data.solarReturn.moon?.rashi}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <p
              className="text-xs"
              style={{ color: "var(--color-text-muted)" }}
            >
              Not available
            </p>
          </div>
        )}
      </motion.div>

      {/* ── Muntha ────────────────────────────────────────────────────── */}
      <motion.div
        className="rounded-2xl border border-hairline bg-card p-6 flex flex-col items-center text-center"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: "easeOut", delay: 0.2 }}
      >
        <div className="flex items-center gap-2 mb-4">
          <Calendar
            className="h-5 w-5 shrink-0"
            style={{ color: ACCENT }}
          />
          <h3
            className="font-[family-name:var(--font-display)] text-base font-semibold tracking-tight"
            style={{ color: "var(--color-text-main)" }}
          >
            Muntha
          </h3>
        </div>

        {data?.muntha ? (
          <div className="flex-1 flex flex-col items-center justify-center space-y-3">
            <span
              className="text-4xl font-[family-name:var(--font-display)] font-semibold tracking-tight leading-none"
              style={{ color: ACCENT_STRONG }}
            >
              {data.muntha.sign}
            </span>
            <span
              className="text-sm"
              style={{ color: "var(--color-text-muted)" }}
            >
              Year {data.muntha.yearsElapsed} since birth
            </span>
            <div
              className="px-3 py-1 rounded-full border mt-1"
              style={{ borderColor: "rgba(212, 180, 131, 0.3)" }}
            >
              <span
                className="text-xs font-mono font-medium"
                style={{ color: ACCENT }}
              >
                Lord: {data.muntha.lord}
              </span>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <p
              className="text-xs"
              style={{ color: "var(--color-text-muted)" }}
            >
              Not available
            </p>
          </div>
        )}
      </motion.div>
    </div>

      {data?.ke_version && (
        <div className="text-[10px] text-text-muted font-mono px-1">
          Knowledge source: Tajika solar return • ke: {data.ke_version}
        </div>
      )}
    </>
  );
}
