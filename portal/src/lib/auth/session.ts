/**
 * Session resolution for NextAuth v5.
 *
 * For server components: call getSession() which reads the JWT cookie directly
 * via NextAuth's auth() helper.
 *
 * Falls back to null (anonymous) if auth is not configured or DB is down.
 */

import { cache } from "react";
import type { Session, Role } from "./types";
import { isAuthConfigured } from "@/lib/auth-config";

let _authFn: (() => Promise<unknown>) | null = null;

async function getAuthModule() {
  if (!isAuthConfigured()) return null;
  if (_authFn) return _authFn;
  try {
    const mod = await import("@/app/api/auth/auth");
    _authFn = mod.auth;
    return _authFn;
  } catch {
    return null;
  }
}

export const getSession = cache(async (): Promise<Session | null> => {
  const auth = await getAuthModule();
  if (!auth) return null;

  try {
    const s = (await auth()) as {
      user?: {
        id?: string;
        email?: string | null;
        role?: Role;
        name?: string | null;
        image?: string | null;
      };
      userId?: string;
    } | null;
    if (!s?.user) return null;
    const user = s.user;
    const userId = user.id ?? s.userId;
    if (!userId) return null;

    // Enrich with personalization fields from the DB (theme, last_path, and the
    // canonical name/image). Role/email/userId stay authoritative from the JWT.
    let theme: Session["theme"] = "system";
    let lastPath: string | null = null;
    let name: string | null = user.name ?? null;
    let image: string | null = user.image ?? null;
    try {
      const { getUserPrefs } = await import("./index");
      const prefs = await getUserPrefs(userId);
      if (prefs) {
        theme = prefs.theme;
        lastPath = prefs.lastPath;
        name = prefs.name ?? name;
        image = prefs.image ?? image;
      }
    } catch {
      /* DB down — fall back to token values + default theme */
    }

    return {
      userId,
      email: user.email ?? "",
      role: user.role ?? "free",
      name,
      image,
      theme,
      lastPath,
    };
  } catch {
    return null;
  }
});
