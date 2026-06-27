"use client";

import { useEffect, useState } from "react";
import { Sparkles, Loader, AlertCircle, TrendingUp } from "lucide-react";
import type { ChartData } from "@/lib/types";
import { postCvce } from "@/lib/cvce-client";

interface YogaEntry {
  name?: string;
  definition?: string;
  prediction?: string;
}

interface YogasPayload {
  activeCount?: number;
  totalChecked?: number | null;
  yogas?: Record<string, YogaEntry>;
}

interface YogasPanelProps {
  chart: ChartData;
}

function YogaCard({ id, entry }: { id: string; entry: YogaEntry }) {
  const title = entry.name || id.replace(/_/g, " ");
  return (
    <article className="rounded-xl border border-hairline bg-card p-4 flex flex-col gap-2">
      <div className="flex items-start gap-2">
        <Sparkles className="h-4 w-4 text-accent shrink-0 mt-0.5" aria-hidden />
        <h3 className="font-[family-name:var(--font-display)] text-sm font-semibold text-text-main leading-snug">
          {title}
        </h3>
      </div>
      {entry.definition ? (
        <p className="text-xs text-text-muted leading-relaxed">{entry.definition}</p>
      ) : null}
      {entry.prediction ? (
        <p className="text-xs font-mono text-success leading-relaxed border-t border-hairline pt-2">
          {entry.prediction}
        </p>
      ) : null}
    </article>
  );
}

function ShadbalaSummary({ shadbala }: { shadbala: NonNullable<ChartData["shadbala"]> }) {
  const planets = Object.keys(shadbala).filter((p) => p !== "Lagna");
  if (!planets.length) return null;

  return (
    <section className="rounded-xl border border-hairline bg-card p-5">
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp className="h-4 w-4 text-accent" aria-hidden />
        <h3 className="font-[family-name:var(--font-display)] text-base font-semibold">
          Shadbala (planetary strength)
        </h3>
      </div>
      <div className="overflow-x-auto -mx-1 px-1">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="text-left text-text-muted border-b border-hairline">
              <th className="pb-2 pr-3 font-normal">Planet</th>
              <th className="pb-2 pr-3 font-normal">Rupas</th>
              <th className="pb-2 font-normal">Ratio</th>
            </tr>
          </thead>
          <tbody>
            {planets.map((p) => {
              const row = shadbala[p];
              const rupas = row?.rupas ?? row?.Rupas ?? null;
              const ratio = row?.ratio ?? row?.Ratio ?? null;
              return (
                <tr key={p} className="border-b border-hairline/60">
                  <td className="py-2 pr-3 text-text-main">{p}</td>
                  <td className="py-2 pr-3 tabular-nums text-text-muted">
                    {rupas != null ? Number(rupas).toFixed(2) : "—"}
                  </td>
                  <td className="py-2 tabular-nums text-text-muted">
                    {ratio != null ? Number(ratio).toFixed(2) : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function YogasPanel({ chart }: YogasPanelProps) {
  const embedded = chart.yogas?.yogas as Record<string, YogaEntry> | undefined;
  const hasEmbedded = embedded && Object.keys(embedded).length > 0;

  const [remote, setRemote] = useState<YogasPayload | null>(null);
  const [loading, setLoading] = useState(!hasEmbedded);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (hasEmbedded || !chart.meta?.birth_datetime) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const json = await postCvce<YogasPayload>("yogas", {
          birth_datetime: chart.meta!.birth_datetime,
          birth_lat: chart.meta!.birth_lat,
          birth_lon: chart.meta!.birth_lon,
          birth_tz: chart.meta!.birth_tz,
        });
        if (!cancelled) setRemote(json);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load yogas");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [
    hasEmbedded,
    chart.meta?.birth_datetime,
    chart.meta?.birth_lat,
    chart.meta?.birth_lon,
    chart.meta?.birth_tz,
  ]);

  const payload: YogasPayload | null = hasEmbedded
    ? {
        activeCount: chart.yogas?.activeCount,
        totalChecked: chart.yogas?.totalChecked,
        yogas: embedded,
      }
    : remote;

  const active = payload?.yogas ?? {};
  const entries = Object.entries(active).filter(
    ([, v]) => v && (v.name || v.definition || v.prediction),
  );

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-16 text-text-muted">
        <Loader className="h-5 w-5 animate-spin" />
        <span className="text-sm font-mono">Computing yogas…</span>
      </div>
    );
  }

  if (error && entries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-16 text-danger">
        <AlertCircle className="h-5 w-5" />
        <span className="text-sm font-mono">{error}</span>
      </div>
    );
  }

  const count = payload?.activeCount ?? entries.length;
  const total = payload?.totalChecked;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <p className="text-sm text-text-muted">
          <span className="font-mono text-accent font-medium">{count}</span>
          {total != null ? (
            <>
              {" "}
              active of <span className="font-mono">{total}</span> checked
            </>
          ) : (
            " active yoga(s)"
          )}
        </p>
        {chart.meta?.name ? (
          <p className="text-xs text-text-muted font-mono">{chart.meta.name}</p>
        ) : null}
      </div>

      {entries.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {entries.map(([id, entry]) => (
            <YogaCard key={id} id={id} entry={entry} />
          ))}
        </div>
      ) : (
        <p className="text-sm text-text-muted py-8 text-center font-mono">
          No classical yogas detected for this chart.
        </p>
      )}

      {chart.shadbala ? <ShadbalaSummary shadbala={chart.shadbala} /> : null}

      {chart.ashtakavarga?.sav ? (
        <section className="rounded-xl border border-hairline bg-card p-5">
          <h3 className="font-[family-name:var(--font-display)] text-base font-semibold mb-2">
            Sarva Ashtakavarga
          </h3>
          <p className="text-xs font-mono text-text-muted">
            Total bindus:{" "}
            <span className="text-text-main">
              {chart.ashtakavarga.sav.reduce((a, b) => a + b, 0)}
            </span>{" "}
            (expect 337)
          </p>
        </section>
      ) : null}
    </div>
  );
}
