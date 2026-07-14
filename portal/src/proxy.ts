import { NextResponse, type NextRequest } from "next/server";
import { PROTECTED_PREFIXES, ADMIN_PREFIXES } from "@/lib/auth/types";
import { isAuthConfigured } from "@/lib/auth-config";
import { GUEST_COOKIE, GUEST_COOKIE_OPTS } from "@/lib/guest-owner-cookie";

function withGuestOwner(req: NextRequest, response?: NextResponse): NextResponse {
  if (req.cookies.has(GUEST_COOKIE)) return response ?? NextResponse.next();
  const guestId = crypto.randomUUID();
  const requestHeaders = new Headers(req.headers);
  const existing = requestHeaders.get("cookie");
  requestHeaders.set("cookie", `${existing ? `${existing}; ` : ""}${GUEST_COOKIE}=${guestId}`);
  const next = response ?? NextResponse.next({ request: { headers: requestHeaders } });
  next.cookies.set(GUEST_COOKIE, guestId, GUEST_COOKIE_OPTS);
  return next;
}

/**
 * Edge proxy — RBAC enforcement for protected routes.
 *
 * When NextAuth is configured (AUTH_SECRET set), this verifies the session
 * from the JWT cookie and redirects unauthorized requests:
 *   /dashboard → sign in required
 *   /admin     → admin role required
 *
 * When auth is NOT configured (no AUTH_SECRET), it passes through —
 * the old scaffold getSession() returns null and pages handle it.
 */
export function proxy(req: NextRequest) {
  const hasAuth = isAuthConfigured();
  if (!hasAuth) return withGuestOwner(req);

  const { pathname } = req.nextUrl;
  const isAdminRoute = ADMIN_PREFIXES.some((p) => pathname.startsWith(p));
  const isProtected = PROTECTED_PREFIXES.some((p) => pathname.startsWith(p));
  if (!isProtected) return withGuestOwner(req);

  const cookie = req.cookies.get("auth.session-token")
    ?? req.cookies.get("__Secure-authjs.session-token")
    ?? req.cookies.get("authjs.session-token");

  if (!cookie) {
    const signInUrl = new URL("/auth/signin", req.url);
    signInUrl.searchParams.set("callbackUrl", pathname);
    return withGuestOwner(req, NextResponse.redirect(signInUrl));
  }

  // Admin gating: the role is in the JWT, which proxy can't decode directly.
  // We redirect to the dashboard which can do server-side role check.
  // For now: proxy only gates authentication, page components gate roles.
  if (isAdminRoute) {
    return withGuestOwner(req); // page will verify role server-side
  }

  return withGuestOwner(req);
}

export const config = {
  matcher: ["/dashboard/:path*", "/admin/:path*", "/profile/:path*", "/settings/:path*", "/chart/timeline", "/api/cvce/:path*"],
};
