import { cookies } from "next/headers";
import { getSession } from "@/lib/auth/session";
import { GUEST_COOKIE } from "@/lib/guest-owner-cookie";

export { GUEST_COOKIE, GUEST_COOKIE_OPTS } from "@/lib/guest-owner-cookie";

/**
 * The scoping key for a person's saved charts (used as the `guest_id` column
 * value in guest_charts). Authenticated users are keyed by their stable account
 * id — so their charts are private per-account AND follow them across devices —
 * while anonymous visitors fall back to a per-browser cookie.
 *
 * SECURITY: this is the ONLY thing separating one user's charts from another's,
 * because the Supabase client uses the service-role key (RLS is bypassed), so
 * scoping MUST be enforced here in application code. Every read/write/delete on
 * guest_charts must filter by the value this returns.
 */
export async function resolveChartOwner(): Promise<string | null> {
  const session = await getSession().catch(() => null);
  if (session?.userId) return `user_${session.userId}`;
  const store = await cookies();
  return store.get(GUEST_COOKIE)?.value ?? null;
}

/**
 * Owner key for a WRITE. Authenticated users get their account key (no cookie).
 * Guests get their existing cookie or a freshly minted one; when `mintedGuestId`
 * is returned non-null the caller must set the GUEST_COOKIE on the response.
 */
export async function resolveChartOwnerForWrite(): Promise<{
  owner: string;
  mintedGuestId: string | null;
}> {
  const session = await getSession().catch(() => null);
  if (session?.userId) return { owner: `user_${session.userId}`, mintedGuestId: null };

  const store = await cookies();
  const existing = store.get(GUEST_COOKIE)?.value;
  if (existing) return { owner: existing, mintedGuestId: null };
  const fresh = crypto.randomUUID();
  return { owner: fresh, mintedGuestId: fresh };
}
