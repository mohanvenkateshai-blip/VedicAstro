"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

/** Re-runs the server component (re-fetching /health/deep) on an interval,
 * so the admin sees live status without a manual reload. */
export function HealthAutoRefresh({ seconds = 30 }: { seconds?: number }) {
  const router = useRouter();
  const [countdown, setCountdown] = useState(seconds);

  useEffect(() => {
    const tick = setInterval(() => {
      setCountdown((c) => {
        if (c <= 1) {
          router.refresh();
          return seconds;
        }
        return c - 1;
      });
    }, 1000);
    return () => clearInterval(tick);
  }, [router, seconds]);

  return (
    <span className="text-[11px] font-mono text-text-muted">
      auto-refresh in {countdown}s ·{" "}
      <button onClick={() => router.refresh()} className="text-accent hover:underline">
        refresh now
      </button>
    </span>
  );
}
