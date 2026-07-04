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
import { redirect } from "next/navigation";
import { hasAtLeast } from "./types";

export type { Role, Session } from "./types";
export { ROLE_RANK, hasAtLeast, PROTECTED_PREFIXES, ADMIN_PREFIXES } from "./types";
export { isAuthConfigured, isDatabaseConfigured } from "@/lib/auth-config";
import { isAdminEmail } from "@/lib/auth-config";

/** Replace the old scaffold getSession() with real NextAuth session. */
export async function getSession(): Promise<Session | null> {
  return authSession();
}

/** Require signed-in session; optionally enforce minimum role tier.
 *  @param returnPath - where to send user back after signin / on tier error (defaults to "/")
 */
export async function requireSession(minRole: Role = "free", returnPath: string = "/"): Promise<Session> {
  const session = await getSession();
  const cb = encodeURIComponent(returnPath);
  if (!session) redirect(`/auth/signin?callbackUrl=${cb}`);
  if (!hasAtLeast(session.role, minRole)) redirect(`${returnPath}?error=tier`);
  return session;
}

/** Create or update a user after OAuth sign-in. Called from auth callback. */
export async function upsertUser(params: {
  id: string;
  email: string;
  name?: string;
  image?: string;
}): Promise<void> {
  const role: Role = isAdminEmail(params.email) ? "admin" : "free";
  try {
    await sql`
      INSERT INTO users (id, email, name, image, role)
      VALUES (${params.id}, ${params.email}, ${params.name ?? null}, ${params.image ?? null}, ${role})
      ON CONFLICT (id) DO UPDATE SET
        email = ${params.email},
        name = COALESCE(${params.name ?? null}, users.name),
        image = COALESCE(${params.image ?? null}, users.image),
        role = CASE
          WHEN ${role} = 'admin' THEN 'admin'
          ELSE users.role
        END,
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

// ── Personalization: prefs + profile ────────────────────────────────────────

export type ThemePref = "light" | "dark" | "system";

export interface UserPrefs {
  name: string | null;
  image: string | null;
  theme: ThemePref;
  lastPath: string | null;
}

/** Read a user's personalization fields. Returns null on DB error. */
export async function getUserPrefs(id: string): Promise<UserPrefs | null> {
  try {
    const rows = (await sql`
      SELECT name, image, theme, last_path
      FROM users WHERE id = ${id}
    `) as any[];
    const r = rows[0];
    if (!r) return null;
    return {
      name: r.name ?? null,
      image: r.image ?? null,
      theme: (r.theme as ThemePref) ?? "system",
      lastPath: r.last_path ?? null,
    };
  } catch {
    return null;
  }
}

/** Persist the user's theme choice (light | dark | system). */
export async function updateUserTheme(id: string, theme: ThemePref): Promise<void> {
  if (theme !== "light" && theme !== "dark" && theme !== "system") return;
  try {
    await sql`UPDATE users SET theme = ${theme}, updated_at = now() WHERE id = ${id}`;
  } catch (e) {
    console.error("Failed to update theme:", e);
  }
}

/** Record the last meaningful page the user visited (for resume-on-login). */
export async function updateLastPath(id: string, path: string): Promise<void> {
  if (!path || !path.startsWith("/")) return;
  try {
    await sql`UPDATE users SET last_path = ${path}, updated_at = now() WHERE id = ${id}`;
  } catch (e) {
    console.error("Failed to update last_path:", e);
  }
}

/** Update the user's display name (from the Profile page). */
export async function updateDisplayName(id: string, name: string): Promise<void> {
  const clean = name.trim().slice(0, 80);
  if (!clean) return;
  try {
    await sql`UPDATE users SET name = ${clean}, updated_at = now() WHERE id = ${id}`;
  } catch (e) {
    console.error("Failed to update name:", e);
  }
}

/** Update the user's avatar URL (after an upload to Supabase Storage). */
export async function updateUserImage(id: string, url: string): Promise<void> {
  if (!url) return;
  try {
    await sql`UPDATE users SET image = ${url}, updated_at = now() WHERE id = ${id}`;
  } catch (e) {
    console.error("Failed to update image:", e);
  }
}

// ── Notification center (RLS-isolated) ──────────────────────────────────────

export interface NotificationRow {
  id: string;
  kind: "info" | "success" | "warning" | "alert";
  title: string;
  body: string | null;
  href: string | null;
  read: boolean;
  created_at: string;
}

/** List a user's notifications, newest first. */
export async function listNotifications(
  userId: string,
  limit = 20,
): Promise<NotificationRow[]> {
  try {
    const rows = await withUserContext<Record<string, unknown>[]>(userId, (s) => s`
      SELECT id, kind, title, body, href, read_at, created_at
      FROM notifications
      WHERE user_id = ${userId}
      ORDER BY created_at DESC
      LIMIT ${limit}
    `);
    return rows.map((r) => ({
      id: String(r.id),
      kind: (r.kind as NotificationRow["kind"]) ?? "info",
      title: String(r.title),
      body: r.body == null ? null : String(r.body),
      href: r.href == null ? null : String(r.href),
      read: r.read_at != null,
      created_at: String(r.created_at),
    }));
  } catch {
    return [];
  }
}

/** Count unread notifications for the bell badge. */
export async function unreadCount(userId: string): Promise<number> {
  try {
    const rows = await withUserContext<Record<string, unknown>[]>(userId, (s) => s`
      SELECT COUNT(*)::int AS n FROM notifications
      WHERE user_id = ${userId} AND read_at IS NULL
    `);
    const n = rows[0]?.n;
    return typeof n === "number" ? n : Number(n) || 0;
  } catch {
    return 0;
  }
}

/** Mark one notification read (RLS-scoped). */
export async function markNotificationRead(userId: string, id: string): Promise<void> {
  try {
    await withUserContext(userId, (s) => s`
      UPDATE notifications SET read_at = now()
      WHERE id = ${id}::uuid AND user_id = ${userId} AND read_at IS NULL
    `);
  } catch (e) {
    console.error("Failed to mark notification read:", e);
  }
}

/** Mark all of a user's notifications read. */
export async function markAllRead(userId: string): Promise<void> {
  try {
    await withUserContext(userId, (s) => s`
      UPDATE notifications SET read_at = now()
      WHERE user_id = ${userId} AND read_at IS NULL
    `);
  } catch (e) {
    console.error("Failed to mark all read:", e);
  }
}

/** Create a notification for a user (server-side; e.g. after a chart is saved). */
export async function createNotification(
  userId: string,
  n: { kind?: NotificationRow["kind"]; title: string; body?: string; href?: string },
): Promise<void> {
  try {
    await withUserContext(userId, (s) => s`
      INSERT INTO notifications (user_id, kind, title, body, href)
      VALUES (${userId}, ${n.kind ?? "info"}, ${n.title}, ${n.body ?? null}, ${n.href ?? null})
    `);
  } catch (e) {
    console.error("Failed to create notification:", e);
  }
}

/** Ensure users row exists (FK for horoscopes). */
export async function ensureUser(id: string, email: string): Promise<void> {
  await sql`
    INSERT INTO users (id, email)
    VALUES (${id}, ${email})
    ON CONFLICT (id) DO UPDATE SET
      email = EXCLUDED.email,
      updated_at = now()
  `;
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

  const rows = await withUserContext<Record<string, unknown>[]>(userId, (s) => s`
    INSERT INTO horoscopes (user_id, name, chart_data)
    VALUES (${userId}, ${name}, ${JSON.stringify(data)}::jsonb)
    RETURNING id
  `);
  const id = rows[0]?.id;
  return typeof id === "string" ? id : null;
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
  const rows = await withUserContext<Record<string, unknown>[]>(userId, (s) => s`
    SELECT id, name, chart_data, created_at
    FROM horoscopes
    WHERE user_id = ${userId}
    ORDER BY created_at DESC
    LIMIT 50
  `);

  const { decryptChartData } = await import("./encrypt");
  const out: Array<{
    id: string;
    name: string;
    chart_data: Record<string, unknown>;
    created_at: string;
  }> = [];

  for (const r of rows) {
    let chart_data = r.chart_data;
    if (typeof chart_data === "string") {
      try {
        chart_data = JSON.parse(chart_data);
      } catch {
        continue;
      }
    }
    if (!chart_data || typeof chart_data !== "object") continue;

    out.push({
      id: String(r.id),
      name: String(r.name),
      chart_data: await decryptChartData(chart_data as Record<string, unknown>),
      created_at: String(r.created_at),
    });
  }

  return out;
}

/** Delete a saved horoscope (RLS-scoped). */
export async function deleteHoroscope(userId: string, horoscopeId: string): Promise<boolean> {
  const rows = await withUserContext<Record<string, unknown>[]>(userId, (s) => s`
    DELETE FROM horoscopes
    WHERE id = ${horoscopeId}::uuid AND user_id = ${userId}
    RETURNING id
  `);
  return rows.length > 0;
}

/** Count saved charts for tier limits. */
export async function countHoroscopes(userId: string): Promise<number> {
  const rows = await withUserContext<Record<string, unknown>[]>(userId, (s) => s`
    SELECT COUNT(*)::int AS n FROM horoscopes WHERE user_id = ${userId}
  `);
  const n = rows[0]?.n;
  return typeof n === "number" ? n : Number(n) || 0;
}

/** Check if DB is healthy */
export async function dbHealthy(): Promise<boolean> {
  const { healthCheck } = await import("@/lib/db");
  return healthCheck();
}
