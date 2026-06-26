export type Role = "free" | "pro" | "premium" | "admin";

export const ROLE_RANK: Record<Role, number> = {
  free: 0,
  pro: 1,
  premium: 2,
  admin: 3,
};

export interface Session {
  userId: string;
  email: string;
  role: Role;
}

export function hasAtLeast(role: Role, required: Role): boolean {
  return ROLE_RANK[role] >= ROLE_RANK[required];
}

export const PROTECTED_PREFIXES = ["/dashboard", "/admin"] as const;
export const ADMIN_PREFIXES = ["/admin"] as const;
