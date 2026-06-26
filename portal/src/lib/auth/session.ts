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

let _authFn: any = null;

async function getAuthModule() {
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
    const s = await auth();
    if (!s?.user?.id) return null;

    // Role comes from JWT token, set in the jwt callback
    const role: Role = (s.user as any).role ?? "free";

    return {
      userId: s.user.id as string,
      email: s.user.email as string,
      role,
    };
  } catch {
    return null;
  }
});
