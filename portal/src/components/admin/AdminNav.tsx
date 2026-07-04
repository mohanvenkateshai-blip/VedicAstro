"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import { LayoutGrid, Activity, Network, ShieldCheck } from "lucide-react";

const TABS = [
  { href: "/admin", label: "Console", icon: LayoutGrid, match: (p: string) => p === "/admin" },
  { href: "/admin/health", label: "System health", icon: Activity, match: (p: string) => p.startsWith("/admin/health") },
  { href: "/admin/knowledge", label: "Knowledge graph", icon: Network, match: (p: string) => p.startsWith("/admin/knowledge") },
];

/** Persistent sub-nav for the admin section — switch between admin tools without
 *  leaving the area. Rendered by src/app/admin/layout.tsx on every admin page. */
export function AdminNav() {
  const pathname = usePathname() ?? "";
  return (
    <div className="border-b border-hairline bg-card/40">
      <div className="mx-auto flex max-w-5xl items-center gap-1 overflow-x-auto px-6">
        <span className="mr-3 flex shrink-0 items-center gap-1.5 text-sm font-semibold text-accent">
          <ShieldCheck size={15} /> Admin
        </span>
        {TABS.map((t) => {
          const active = t.match(pathname);
          const Icon = t.icon;
          return (
            <Link
              key={t.href}
              href={t.href}
              aria-current={active ? "page" : undefined}
              className={clsx(
                "-mb-px flex items-center gap-1.5 whitespace-nowrap border-b-2 px-3 py-3 text-sm transition-colors",
                active
                  ? "border-accent font-medium text-text-main"
                  : "border-transparent text-text-muted hover:text-text-main",
              )}
            >
              <Icon size={14} /> {t.label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
