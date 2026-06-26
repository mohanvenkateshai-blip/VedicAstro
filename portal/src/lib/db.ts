/**
 * Neon serverless Postgres client — dynamic import, no require().
 */

import type { NeonQueryFunction } from "@neondatabase/serverless";

let _sql: NeonQueryFunction<any, any> | null = null;
let _initPromise: Promise<NeonQueryFunction<any, any> | null> | null = null;

async function getSql(): Promise<NeonQueryFunction<any, any> | null> {
  if (_sql) return _sql;
  if (_initPromise) return _initPromise;

  _initPromise = (async () => {
    const url = process.env.DATABASE_URL;
    if (!url) return null;
    try {
      const mod = await import("@neondatabase/serverless");
      _sql = mod.neon(url);
      return _sql;
    } catch (e) {
      console.error("Failed to initialize Neon:", e);
      return null;
    }
  })();

  return _initPromise;
}

export function sql(strings: TemplateStringsArray, ...values: unknown[]): Promise<any> {
  return _execute(strings, ...values);
}

async function _execute(strings: TemplateStringsArray, ...values: unknown[]): Promise<any> {
  const s = await getSql();
  if (!s) throw new Error("DATABASE_URL not configured");
  return s(strings as any, ...values);
}

export async function healthCheck(): Promise<boolean> {
  try {
    const s = await getSql();
    if (!s) return false;
    await (s as any)`SELECT 1`;
    return true;
  } catch {
    return false;
  }
}

export async function setRlsContext(userId: string | null) {
  if (!userId) return;
  try {
    const s = await getSql();
    if (!s) return;
    await (s as any)`SELECT set_config('app.current_user_id', ${userId}, true)`;
  } catch { /* non-fatal */ }
}
