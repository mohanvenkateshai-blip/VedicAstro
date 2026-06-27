/** True when NextAuth can issue real sessions (all three vars required). */
export function isAuthConfigured(): boolean {
  return !!(
    process.env.AUTH_SECRET &&
    process.env.AUTH_GOOGLE_ID &&
    process.env.AUTH_GOOGLE_SECRET
  );
}

export function isDatabaseConfigured(): boolean {
  return !!process.env.DATABASE_URL;
}
