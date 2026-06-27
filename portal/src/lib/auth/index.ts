/**
 * Auth & RBAC — real implementation with NextAuth v5 + Neon Postgres.
 *
 * Provides:
 *   - getSession() → Session | null (from NextAuth JWT cookie)
 *   - Role type + hasAtLeast() → same interface as the old scaffold
 *   - createUser() / getUser() → user management
 *
 * Relies on:
 *   - AUTH_GOOGLE_ID / AUTH_GOOGLE_SECRET env vars for Google OAuth
 *   - AUTH_SECRET (NextAuth cookie signing key)
 *   - DATABASE_URL (Neon Postgres connection string)
 *   - ENCRYPTION_KEY (256-bit key for birth PII)
 */

import { getSession as authSession } from "./session";
import { sql, withUserContext } from "@/lib/db";
import type { Role, Session } from "./types";

export type { Role, Session } from "./types";
export { ROLE_RANK, hasAtLeast, PROTECTED_PREFIXES, ADMIN_PREFIXES } from "./types";
export { isAuthConfigured, isDatabaseConfigured } from "@/lib/auth-config";

/** Replace the old scaffold getSession() with real NextAuth session. */
export async function getSession(): Promise<Session | null> {
  return authSession();
}

/** Create or update a user after OAuth sign-in. Called from auth callback. */
export async function upsertUser(params: {
  id: string;
  email: string;
  name?: string;
}): Promise<void> {
  try {
    await sql`
      INSERT INTO users (id, email, name)
      VALUES (${params.id}, ${params.email}, ${params.name ?? null})
      ON CONFLICT (id) DO UPDATE SET
        email = ${params.email},
        name = COALESCE(${params.name ?? null}, users.name),
        updated_at = now()
    `;
  } catch (e) {
    console.error("Failed to upsert user:", e);
  }
}

/** Get user by ID. Returns null if no DB. */
export async function getUser(id: string): Promise<{
  id: string;
  email: string;
  name: string | null;
  role: Role;
  created_at: string;
} | null> {
  try {
    const rows = await sql`
      SELECT id, email, name, role, created_at
      FROM users WHERE id = ${id}
    `;
    const all = rows as any[];
    return all[0] ?? null;
  } catch {
    return null;
  }
}

/** Save a horoscope chart for a user. Encrypts birth PII before storing. */
export async function saveHoroscope(
  userId: string,
  name: string,
  chartData: Record<string, unknown>,
): Promise<string | null> {
  let data = chartData;
  try {
    const { encryptChartData } = await import("./encrypt");
    data = await encryptChartData(chartData);
  } catch {
    /* encryption optional */
  }

  const rows = await withUserContext(userId, (s) => s`
    INSERT INTO horoscopes (user_id, name, chart_data)
    VALUES (${userId}, ${name}, ${JSON.stringify(data)}::jsonb)
    RETURNING id
  `);
  const all = rows as { id: string }[];
  return all[0]?.id ?? null;
}

/** Get a user's saved horoscopes (decrypts PII). */
export async function getHoroscopes(userId: string): Promise<
  Array<{
    id: string;
    name: string;
    chart_data: Record<string, unknown>;
    created_at: string;
  }>
> {
  try {
    const rows = await withUserContext(userId, (s) => s`
      SELECT id, name, chart_data, created_at
      FROM horoscopes
      WHERE user_id = ${userId}
      ORDER BY created_at DESC
      LIMIT 50
    `);
    const { decryptChartData } = await import("./encrypt");
    const all = rows as {
      id: string;
      name: string;
      chart_data: Record<string, unknown>;
      created_at: string;
    }[];
    return await Promise.all(
      all.map(async (r) => ({
        ...r,
        chart_data: await decryptChartData(r.chart_data),
      })),
    );
  } catch {
    return [];
  }
}

/** Check if DB is healthy */
export async function dbHealthy(): Promise<boolean> {
  const { healthCheck } = await import("@/lib/db");
  return healthCheck();
}
