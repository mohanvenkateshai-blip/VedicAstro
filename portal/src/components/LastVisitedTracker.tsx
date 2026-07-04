"use client";

import { useEffect, useRef } from "react";
import { usePathname, useSearchParams } from "next/navigation";

const SKIP = ["/auth", "/api", "/resume"];

/** Records the signed-in user's current page — including the query string, so a
 *  chart (identified by birth params in the URL) is restored on resume, not just
 *  the bare page. Mounted once in the root layout, inside a Suspense boundary
 *  (useSearchParams requirement). No-op for guests. */
export function LastVisitedTracker({ signedIn }: { signedIn: boolean }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const last = useRef<string | null>(null);

  useEffect(() => {
    if (!signedIn || !pathname) return;
    if (SKIP.some((p) => pathname.startsWith(p))) return;

    const qs = searchParams.toString();
    const full = pathname + (qs ? `?${qs}` : "");
    if (full === last.current) return;

    const t = setTimeout(() => {
      last.current = full;
      fetch("/api/prefs/last-path", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: full }),
        keepalive: true,
      }).catch(() => {});
    }, 1000);

    return () => clearTimeout(t);
  }, [pathname, searchParams, signedIn]);

  return null;
}
