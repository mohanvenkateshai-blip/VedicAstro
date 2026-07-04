export type Role = "free" | "pro" | "premium" | "admin";

export const ROLE_RANK: Record<Role, number> = {
  free: 0,
  pro: 1,
  premium: 2,
  admin: 3,
};

export type ThemePref = "light" | "dark" | "system";

export interface Session {
  userId: string;
  email: string;
  role: Role;
  name?: string | null;
  image?: string | null;
  theme: ThemePref;
  lastPath?: string | null;
}

export function hasAtLeast(role: Role, required: Role): boolean {
  return ROLE_RANK[role] >= ROLE_RANK[required];
}

export const PROTECTED_PREFIXES = ["/dashboard", "/admin", "/profile", "/settings"] as const;
export const ADMIN_PREFIXES = ["/admin"] as const;
