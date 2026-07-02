"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import {
  Compass, Orbit, Clock, Sparkles,
  Sun, Crosshair, BookOpen, Download, Target,
  Home, CircleDot, FileText,
} from "lucide-react";

const TABS = [
  { id: "overview", label: "Chart Overview", icon: Compass, href: "/chart", engine: "Janma Kundali" },
  { id: "report", label: "Horoscope Report", icon: FileText, href: "/chart/report", engine: "Synthesis" },
  { id: "transits", label: "Transits", icon: Orbit, href: "/chart/transits", engine: "Gochar Phala" },
  { id: "dasha", label: "Dasha Timeline", icon: Clock, href: "/chart/dasha", engine: "Dasha Phala" },
  { id: "yogas", label: "Yogas & Strength", icon: Sparkles, href: "/chart/yogas", engine: "Yoga + Bala" },
  { id: "bhava", label: "Bhava Explorer", icon: Home, href: "/chart/bhava", engine: "Bhava Phala" },
  { id: "graha", label: "Graha Explorer", icon: CircleDot, href: "/chart/graha", engine: "Graha Phala" },
  { id: "special", label: "Special Points", icon: Target, href: "/chart/special", engine: "Special Points" },
  { id: "kp", label: "KP System", icon: Crosshair, href: "/chart/kp", engine: "KP Engine" },
  { id: "kalachakra", label: "Kalachakra Dasha", icon: Target, href: "/chart/kalachakra", engine: "Kalachakra" },
  { id: "varshaphala", label: "Solar Return", icon: Sun, href: "/chart/varshaphala", engine: "Varshaphala" },
];

const BOTTOM_TABS = [
  { id: "sources", label: "Classical Sources", icon: BookOpen, href: "/chart/sources", engine: "Shastra Pramana" },
  { id: "export", label: "Export PDF", icon: Download, href: "/chart/export", engine: "Rendering" },
];

export function ChartSidebar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const qs = searchParams?.toString() ?? "";

  return (
    <nav className="flex flex-col gap-0.5 w-56" aria-label="Chart analysis sections">
      <div className="px-3 py-2 mb-1">
        <span className="text-[10px] font-mono uppercase tracking-[0.14em] text-text-muted">Analysis Tools</span>
      </div>
      {TABS.map((tab) => {
        const Icon = tab.icon;
        const isActive = pathname === tab.href || (pathname === "/chart" && tab.id === "overview");
        const href = qs ? `${tab.href}?${qs}` : tab.href;
        return (
          <Link
            key={tab.id}
            href={href}
            className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
              isActive
                ? "bg-accent/15 text-accent font-medium"
                : "text-text-muted hover:text-text-main hover:bg-white/3"
            }`}
          >
            <Icon size={15} />
            <span>{tab.label}</span>
            {isActive && (
              <span className="ml-auto text-[9px] font-mono text-accent/60">{tab.engine}</span>
            )}
          </Link>
        );
      })}
      <div className="mt-4 px-3 py-2 mb-1 border-t border-hairline">
        <span className="text-[10px] font-mono uppercase tracking-[0.14em] text-text-muted">Reference</span>
      </div>
      {BOTTOM_TABS.map((tab) => {
        const Icon = tab.icon;
        const href = qs ? `${tab.href}?${qs}` : tab.href;
        const isActive = pathname === tab.href;
        return (
          <Link
            key={tab.id}
            href={href}
            className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
              isActive
                ? "bg-accent/15 text-accent font-medium"
                : "text-text-muted hover:text-text-main hover:bg-white/3"
            }`}
          >
            <Icon size={15} />
            <span>{tab.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
