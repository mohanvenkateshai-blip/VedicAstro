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

export function adminEmailsFromEnv(): string[] {
  return (process.env.ADMIN_EMAILS ?? "")
    .split(",")
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean);
}

export function isAdminEmail(email: string): boolean {
  return adminEmailsFromEnv().includes(email.trim().toLowerCase());
}
