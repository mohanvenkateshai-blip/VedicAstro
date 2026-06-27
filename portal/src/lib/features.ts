import type { Role } from "@/lib/auth/types";
import { hasAtLeast } from "@/lib/auth/types";

/** Saved-chart limits per tier. */
export const MAX_SAVED_CHARTS: Record<Role, number> = {
  free: 5,
  pro: 50,
  premium: 200,
  admin: 999,
};

/** Minimum role required for chart workspace features. */
export const FEATURE_MIN_ROLE: Record<string, Role> = {
  "chart/kp": "free",
  "chart/varshaphala": "pro",
  "chart/transits": "free",
  "chart/yogas": "free",
  "chart/bhava": "free",
  "chart/graha": "free",
  prashna: "free",
  export: "free",
};

export function canAccessFeature(role: Role, feature: string): boolean {
  const required = FEATURE_MIN_ROLE[feature] ?? "free";
  return hasAtLeast(role, required);
}

export function maxSavedCharts(role: Role): number {
  return MAX_SAVED_CHARTS[role] ?? MAX_SAVED_CHARTS.free;
}
