"use client";

/** Client-side theme helpers. Source of truth for signed-in users is the DB
 *  (users.theme); localStorage['va-theme'] is a no-flash mirror for guests and
 *  first paint. The inline script in layout.tsx applies it before hydration. */

export type ThemePref = "light" | "dark" | "system";

export function applyTheme(theme: ThemePref) {
  const dark =
    theme === "dark" ||
    (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", dark);
}

export function getStoredTheme(): ThemePref {
  try {
    const t = localStorage.getItem("va-theme");
    if (t === "light" || t === "dark" || t === "system") return t;
  } catch {}
  return "system";
}

/** Apply + persist a theme choice. Mirrors to localStorage always; writes to the
 *  DB when signed in so the choice follows the user across devices. */
export function setThemePref(theme: ThemePref, signedIn: boolean) {
  applyTheme(theme);
  try {
    localStorage.setItem("va-theme", theme);
  } catch {}
  if (signedIn) {
    fetch("/api/prefs/theme", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ theme }),
    }).catch(() => {});
  }
}
