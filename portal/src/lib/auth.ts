/**
 * Auth & RBAC — re-exports from the full implementation.
 *
 * When NextAuth is configured (AUTH_SECRET + AUTH_GOOGLE_ID set), this
 * module provides real Google OAuth sessions via NextAuth v5.
 * When not configured, getSession() returns null (anonymous mode).
 */

export {
  getSession,
  hasAtLeast,
  PROTECTED_PREFIXES,
  ADMIN_PREFIXES,
  type Role,
  type Session,
} from "./auth/index";
