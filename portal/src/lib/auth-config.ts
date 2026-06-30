/** Trim env var; reject empty strings and obvious placeholders. */
function envVar(name: string, minLen = 1): string | undefined {
  const v = process.env[name]?.trim();
  if (!v || v.length < minLen) return undefined;
  if (v === '""' || v === "''" || v === "-" || v === "xx") return undefined;
  return v;
}

/** True when NextAuth can issue real sessions (all three vars required). */
export function isAuthConfigured(): boolean {
  return !!(
    envVar("AUTH_SECRET", 32) &&
    envVar("AUTH_GOOGLE_ID", 10) &&
    envVar("AUTH_GOOGLE_SECRET", 10)
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
