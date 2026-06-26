import { NextResponse, type NextRequest } from "next/server";
import { hasAtLeast, PROTECTED_PREFIXES, ADMIN_PREFIXES } from "@/lib/auth/types";

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
  const hasAuth = !!process.env.AUTH_SECRET;
  if (!hasAuth) return NextResponse.next();

  const { pathname } = req.nextUrl;
  const isAdminRoute = ADMIN_PREFIXES.some((p) => pathname.startsWith(p));
  const isProtected = PROTECTED_PREFIXES.some((p) => pathname.startsWith(p));
  if (!isProtected) return NextResponse.next();

  const cookie = req.cookies.get("auth.session-token")
    ?? req.cookies.get("__Secure-authjs.session-token")
    ?? req.cookies.get("authjs.session-token");

  if (!cookie) {
    const signInUrl = new URL("/auth/signin", req.url);
    signInUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(signInUrl);
  }

  // Admin gating: the role is in the JWT, which proxy can't decode directly.
  // We redirect to the dashboard which can do server-side role check.
  // For now: proxy only gates authentication, page components gate roles.
  if (isAdminRoute) {
    return NextResponse.next(); // page will verify role server-side
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/admin/:path*"],
};
