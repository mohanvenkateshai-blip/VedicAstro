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
      user?: { id?: string; email?: string | null; role?: Role };
      userId?: string;
    } | null;
    if (!s?.user) return null;
    const user = s.user;
    const userId = user.id ?? s.userId;
    if (!userId) return null;

    return {
      userId,
      email: user.email ?? "",
      role: user.role ?? "free",
    };
  } catch {
    return null;
  }
});
