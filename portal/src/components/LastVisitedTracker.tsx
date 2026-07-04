"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";

const SKIP = ["/auth", "/api", "/resume"];

/** Records the signed-in user's current page (debounced) so they resume there on
 *  next login. Mounted once in the root layout. No-op for guests. */
export function LastVisitedTracker({ signedIn }: { signedIn: boolean }) {
  const pathname = usePathname();
  const last = useRef<string | null>(null);

  useEffect(() => {
    if (!signedIn || !pathname) return;
    if (SKIP.some((p) => pathname.startsWith(p))) return;
    if (pathname === last.current) return;

    const t = setTimeout(() => {
      last.current = pathname;
      fetch("/api/prefs/last-path", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: pathname }),
        keepalive: true,
      }).catch(() => {});
    }, 1000);

    return () => clearTimeout(t);
  }, [pathname, signedIn]);

  return null;
}
