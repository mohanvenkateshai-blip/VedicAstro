/** Edge-safe guest owner cookie metadata. Keep auth/session imports out of the
 * Next.js proxy bundle. */
export const GUEST_COOKIE = "vedicastro_guest_id";

export const GUEST_COOKIE_OPTS = {
  httpOnly: true,
  sameSite: "lax" as const,
  path: "/",
  maxAge: 60 * 60 * 24 * 365,
};
