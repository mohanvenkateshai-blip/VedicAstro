"use client";

import { useEffect, useState } from "react";
import { Monitor, Moon, Sun } from "lucide-react";
import { clsx } from "clsx";
import { getStoredTheme, setThemePref, type ThemePref } from "@/lib/theme";

const OPTIONS: { value: ThemePref; label: string; icon: React.ReactNode }[] = [
  { value: "light", label: "Light", icon: <Sun size={14} /> },
  { value: "dark", label: "Dark", icon: <Moon size={14} /> },
  { value: "system", label: "System", icon: <Monitor size={14} /> },
];

/** Segmented light / dark / system control. Reused in the user menu and Settings. */
export function ThemePicker({ signedIn, size = "sm" }: { signedIn: boolean; size?: "sm" | "md" }) {
  const [theme, setTheme] = useState<ThemePref>("system");

  useEffect(() => {
    // Read localStorage after mount rather than synchronously in the effect
    // body, so this doesn't cascade-render.
    const t = setTimeout(() => {
      setTheme(getStoredTheme());
    }, 0);
    return () => clearTimeout(t);
  }, []);

  function choose(next: ThemePref) {
    setTheme(next);
    setThemePref(next, signedIn);
  }

  return (
    <div
      role="radiogroup"
      aria-label="Theme"
      className="inline-flex items-center gap-1 rounded-xl border border-hairline bg-background/50 p-1"
    >
      {OPTIONS.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={theme === o.value}
          onClick={() => choose(o.value)}
          className={clsx(
            "flex items-center gap-1.5 rounded-lg font-medium transition-colors",
            size === "md" ? "px-3 py-1.5 text-sm" : "px-2.5 py-1 text-xs",
            theme === o.value
              ? "bg-primary text-primary-fg"
              : "text-text-muted hover:text-text-main",
          )}
        >
          {o.icon}
          {o.label}
        </button>
      ))}
    </div>
  );
}
