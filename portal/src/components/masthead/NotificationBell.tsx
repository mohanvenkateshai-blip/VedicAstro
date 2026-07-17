"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Bell, Check } from "lucide-react";
import { clsx } from "clsx";

type Item = {
  id: string;
  kind: "info" | "success" | "warning" | "alert";
  title: string;
  body: string | null;
  href: string | null;
  read: boolean;
  created_at: string;
};

const DOT: Record<Item["kind"], string> = {
  info: "bg-primary",
  success: "bg-success",
  warning: "bg-warning",
  alert: "bg-danger",
};

function relTime(iso: string): string {
  const d = new Date(iso).getTime();
  if (Number.isNaN(d)) return "";
  const s = Math.floor((Date.now() - d) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Item[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/notifications", { cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        setItems(data.items ?? []);
        setUnread(data.unread ?? 0);
      }
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, []);

  // Poll the unread count on mount + every 60s (cheap COUNT query).
  useEffect(() => {
    let stop = false;
    async function poll() {
      try {
        const res = await fetch("/api/notifications", { cache: "no-store" });
        if (!stop && res.ok) {
          const data = await res.json();
          setUnread(data.unread ?? 0);
        }
      } catch {}
    }
    poll();
    const t = setInterval(poll, 60000);
    return () => {
      stop = true;
      clearInterval(t);
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    // Defer past the current commit so this doesn't cascade-render.
    const t = setTimeout(() => { load(); }, 0);
    function onClick(e: MouseEvent) {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      clearTimeout(t);
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, load]);

  async function markAll() {
    setItems((prev) => prev.map((i) => ({ ...i, read: true })));
    setUnread(0);
    await fetch("/api/notifications", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ all: true }),
    }).catch(() => {});
  }

  async function markOne(id: string) {
    setItems((prev) => prev.map((i) => (i.id === id ? { ...i, read: true } : i)));
    setUnread((u) => Math.max(0, u - 1));
    await fetch("/api/notifications", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    }).catch(() => {});
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={`Notifications${unread ? ` (${unread} unread)` : ""}`}
        aria-expanded={open}
        className="relative grid h-11 w-11 min-h-[44px] min-w-[44px] place-items-center rounded-lg border border-hairline text-text-muted hover:text-text-main transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
      >
        <Bell size={16} aria-hidden="true" />
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-danger px-1 text-[10px] font-medium text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-[340px] max-w-[calc(100vw-2rem)] rounded-2xl border border-hairline bg-card shadow-lg overflow-hidden">
          <div className="flex items-center justify-between border-b border-hairline px-4 py-2.5">
            <span className="text-sm font-medium">Notifications</span>
            {items.some((i) => !i.read) && (
              <button
                onClick={markAll}
                className="flex items-center gap-1 text-xs text-accent hover:underline"
              >
                <Check size={12} /> Mark all read
              </button>
            )}
          </div>

          {loading && <div className="px-4 py-6 text-sm text-text-muted">Loading…</div>}

          {!loading && items.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-text-muted">
              You&rsquo;re all caught up.
            </div>
          )}

          {!loading && items.length > 0 && (
            <ul className="max-h-[400px] overflow-auto divide-y divide-hairline">
              {items.map((n) => {
                const row = (
                  <div
                    className={clsx(
                      "flex gap-3 px-4 py-3 transition-colors hover:bg-accent/5",
                      !n.read && "bg-accent/[0.04]",
                    )}
                  >
                    <span className={clsx("mt-1.5 h-2 w-2 shrink-0 rounded-full", DOT[n.kind])} />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-text-main">{n.title}</p>
                      {n.body && <p className="mt-0.5 text-xs text-text-muted">{n.body}</p>}
                      <p className="mt-1 text-[11px] text-text-muted">{relTime(n.created_at)}</p>
                    </div>
                  </div>
                );
                return (
                  <li key={n.id} onClick={() => !n.read && markOne(n.id)}>
                    {n.href ? (
                      <Link href={n.href} onClick={() => setOpen(false)}>
                        {row}
                      </Link>
                    ) : (
                      row
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
