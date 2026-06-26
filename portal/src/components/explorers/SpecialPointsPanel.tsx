"use client";

import { useState, useEffect } from "react";
import { Star, AlertTriangle, Target } from "lucide-react";
import type { ChartData } from "@/lib/types";

interface SpecialPoint {
  name: string;
  rashi: string;
  longitude: number;
  degLabel: string;
}

interface SpecialPointsResponse {
  mandi?: SpecialPoint;
  gulika?: SpecialPoint;
  bhrigu_bindu?: SpecialPoint;
}

const DESCRIPTIONS: Record<string, string> = {
  Mandi:
    "Son of Saturn (Shani). A malefic upagraha that brings delays, obstacles, and chronic issues. Its house placement shows where one faces persistent challenges.",
  Gulika:
    "A secondary malefic upagraha related to Saturn. Indicates areas of hidden enemies, toxins, and karmic debts. More subtle than Mandi.",
  "Bhrigu Bindu":
    "The midpoint between Rahu and Moon. Represents a karmic destiny point — where major life shifts and fated events occur. Discovered by Maharishi Bhrigu.",
};

const ICONS: Record<string, React.ReactNode> = {
  Mandi: <AlertTriangle className="h-5 w-5 text-danger shrink-0" />,
  Gulika: <AlertTriangle className="h-5 w-5 text-warning shrink-0" />,
  "Bhrigu Bindu": <Target className="h-5 w-5 text-accent shrink-0" />,
};

type FetchState = "idle" | "loading" | "error" | "success";

export function SpecialPointsPanel({ chart }: { chart: ChartData | undefined }) {
  const [state, setState] = useState<FetchState>("idle");
  const [data, setData] = useState<SpecialPointsResponse | null>(null);

  useEffect(() => {
    if (!chart || !chart.meta?.birth_datetime) return;

    let cancelled = false;

    async function fetchPoints() {
      setState("loading");
      try {
        const res = await fetch(
          "https://vedicastro-cvce.fly.dev/special-points",
          {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({
              birth_datetime: chart?.meta?.birth_datetime,
              birth_lat: chart?.meta?.birth_lat,
              birth_lon: chart?.meta?.birth_lon,
              birth_tz: chart?.meta?.birth_tz,
            }),
          }
        );
        if (!res.ok) throw new Error(`Engine returned ${res.status}`);
        const json = (await res.json()) as SpecialPointsResponse;
        if (!cancelled) {
          setData(json);
          setState("success");
        }
      } catch {
        if (!cancelled) setState("error");
      }
    }

    fetchPoints();
    return () => {
      cancelled = true;
    };
  }, [chart?.meta?.birth_datetime, chart?.meta?.birth_lat, chart?.meta?.birth_lon, chart?.meta?.birth_tz]);

  const points: { key: string; point: SpecialPoint | undefined }[] = [
    { key: "Mandi", point: data?.mandi },
    { key: "Gulika", point: data?.gulika },
    { key: "Bhrigu Bindu", point: data?.bhrigu_bindu },
  ];

  if (state === "idle") {
    return (
      <div className="text-center py-10 text-text-muted text-sm">
        <Star className="h-8 w-8 mx-auto mb-2 text-accent/40" />
        <p>Special points will appear here after computing a chart.</p>
      </div>
    );
  }

  if (state === "loading") {
    return (
      <div className="flex items-center justify-center gap-3 py-12 text-text-muted text-sm">
        <span className="grid h-7 w-7 place-items-center rounded-lg bg-accent/15 text-accent">
          <Star className="h-4 w-4 animate-pulse" />
        </span>
        Computing special points…
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="flex flex-col items-center gap-2 py-10 text-text-muted text-sm">
        <AlertTriangle className="h-8 w-8 text-danger/60" />
        <p>Unable to fetch special points.</p>
        <button
          onClick={() => setState("idle")}
          className="text-accent hover:underline text-xs mt-1"
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      {points.map(({ key, point }) => (
        <div
          key={key}
          className="rounded-2xl border border-hairline bg-card p-5"
        >
          <div className="flex items-start gap-3 mb-3">
            {ICONS[key]}
            <div>
              <h3 className="text-sm font-medium">{key}</h3>
              {point ? (
                <p className="text-xs text-text-muted font-mono mt-0.5">
                  {point.rashi} · {point.degLabel}
                </p>
              ) : (
                <p className="text-xs text-text-muted italic mt-0.5">
                  Not available for this chart
                </p>
              )}
            </div>
          </div>
          <p className="text-xs text-text-muted leading-relaxed">
            {DESCRIPTIONS[key]}
          </p>
        </div>
      ))}
    </div>
  );
}
