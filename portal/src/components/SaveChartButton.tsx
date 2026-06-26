"use client";

import { useState } from "react";
import { saveChart } from "@/lib/actions";
import type { ChartData } from "@/lib/types";

export function SaveChartButton({ chart, chartName }: { chart: ChartData; chartName: string }) {
  const [status, setStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  async function handleClick() {
    setStatus("saving");
    setErrorMsg("");
    try {
      const result = await saveChart(chartName, chart);
      if (result.ok) {
        setStatus("saved");
      } else {
        setStatus("error");
        setErrorMsg(result.error || "Unknown error");
      }
    } catch (e: any) {
      setStatus("error");
      setErrorMsg(e?.message || "Save failed");
    }
  }

  const btnClass = status === "saved"
    ? "border-success bg-success/10 text-success"
    : status === "error"
    ? "border-danger bg-danger/5 text-danger"
    : "border-hairline text-text-muted hover:text-text-main hover:border-accent/60";

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={handleClick}
        disabled={status === "saving" || status === "saved"}
        aria-live="polite"
        aria-label={status === "saved" ? "Chart saved" : status === "saving" ? "Saving chart" : status === "error" ? "Save failed, click to retry" : "Save this chart to your dashboard"}
        className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-2.5 min-h-[44px] text-xs font-medium transition-colors ${btnClass}`}
      >
        {status === "saving" ? "Saving…" : status === "saved" ? "✓ Saved" : status === "error" ? "✕ Retry" : "Save to my charts"}
      </button>
      {errorMsg && (
        <span className="text-xs text-danger max-w-[200px] truncate">{errorMsg}</span>
      )}
    </div>
  );
}
