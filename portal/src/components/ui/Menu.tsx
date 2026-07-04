"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { clsx } from "clsx";

/** Lightweight anchored dropdown — the small corner popover the UI kit lacked
 *  (Overlay is a full-screen modal/sheet). Outside-click + Escape close. */
export function Menu({
  trigger,
  children,
  align = "right",
  className,
  panelClassName,
  label,
}: {
  trigger: React.ReactNode;
  children: React.ReactNode | ((close: () => void) => React.ReactNode);
  align?: "left" | "right";
  className?: string;
  panelClassName?: string;
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const close = () => setOpen(false);

  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={ref} className={clsx("relative", className)}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={label}
        className="flex items-center rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
      >
        {trigger}
      </button>
      {open && (
        <div
          role="menu"
          className={clsx(
            "absolute z-50 mt-2 min-w-[220px] rounded-2xl border border-hairline bg-card shadow-lg overflow-hidden",
            align === "right" ? "right-0" : "left-0",
            panelClassName,
          )}
        >
          {typeof children === "function" ? children(close) : children}
        </div>
      )}
    </div>
  );
}

/** A row inside a Menu — link or button. */
export function MenuItem({
  href,
  onClick,
  icon,
  children,
  danger,
  disabled,
}: {
  href?: string;
  onClick?: () => void;
  icon?: React.ReactNode;
  children: React.ReactNode;
  danger?: boolean;
  disabled?: boolean;
}) {
  const cls = clsx(
    "flex w-full items-center gap-2.5 px-4 py-2.5 text-sm text-left transition-colors",
    danger ? "text-danger hover:bg-danger/10" : "text-text-main hover:bg-accent/5",
    disabled && "opacity-50 pointer-events-none",
  );
  const inner = (
    <>
      {icon && <span className="shrink-0 text-text-muted">{icon}</span>}
      <span className="min-w-0 flex-1 truncate">{children}</span>
    </>
  );
  if (href) {
    return (
      <Link href={href} role="menuitem" className={cls} onClick={onClick}>
        {inner}
      </Link>
    );
  }
  return (
    <button type="button" role="menuitem" className={cls} onClick={onClick} disabled={disabled}>
      {inner}
    </button>
  );
}
