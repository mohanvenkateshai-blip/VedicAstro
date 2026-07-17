/**
 * Neon serverless Postgres client — dynamic import, no require().
 */

import type { NeonQueryFunction } from "@neondatabase/serverless";

// `neon(url)` is called below with no options, so it's the default
// (non-array-mode, non-full-results) shape: rows come back as
// `Record<string, unknown>[]`.
type Sql = NeonQueryFunction<false, false>;

let _sql: Sql | null = null;
let _initPromise: Promise<Sql | null> | null = null;

async function getSql(): Promise<Sql | null> {
  if (_sql) return _sql;
  if (_initPromise) return _initPromise;

  _initPromise = (async () => {
    const url = process.env.DATABASE_URL;
    if (!url) return null;
    try {
      const mod = await import("@neondatabase/serverless");
      _sql = mod.neon(url);
      const { ensureSchema } = await import("@/lib/auth/migrate");
      await ensureSchema();
      return _sql;
    } catch (e) {
      console.error("Failed to initialize Neon:", e);
      return null;
    }
  })();

  return _initPromise;
}

/** Normalize Neon / transaction results to an array of row objects. */
export function rowsFrom(result: unknown): Record<string, unknown>[] {
  if (result == null) return [];
  if (Array.isArray(result)) {
    if (result.length === 0) return [];
    const first = result[0];
    if (typeof first === "object" && first !== null && !Array.isArray(first)) {
      return result as Record<string, unknown>[];
    }
    return [];
  }
  if (typeof result === "object" && "rows" in result) {
    const rows = (result as { rows: unknown }).rows;
    return Array.isArray(rows) ? (rows as Record<string, unknown>[]) : [];
  }
  return [];
}

export function sql(strings: TemplateStringsArray, ...values: unknown[]): Promise<Record<string, unknown>[]> {
  return _execute(strings, ...values);
}

async function _execute(strings: TemplateStringsArray, ...values: unknown[]): Promise<Record<string, unknown>[]> {
  const s = await getSql();
  if (!s) throw new Error("DATABASE_URL not configured");
  return s(strings, ...values);
}

type SqlQuery = ReturnType<Sql>;

/**
 * Run a query with RLS context set in the same Neon transaction.
 * `makeQuery` must return a tagged-template query (not a Promise).
 */
export async function withUserContext<T>(
  userId: string,
  makeQuery: (s: Sql) => SqlQuery,
): Promise<T> {
  const s = await getSql();
  if (!s) throw new Error("DATABASE_URL not configured");

  const txFn = s.transaction;

  if (typeof txFn !== "function") {
    await setRlsContext(userId);
    const raw = await makeQuery(s);
    return rowsFrom(raw) as T;
  }

  const results = await txFn.call(s, [
    s`SELECT set_config('app.current_user_id', ${userId}, true)`,
    makeQuery(s),
  ]);

  const last = Array.isArray(results) ? results[results.length - 1] : results;
  return rowsFrom(last) as T;
}

export async function healthCheck(): Promise<boolean> {
  try {
    const s = await getSql();
    if (!s) return false;
    await s`SELECT 1`;
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
    await s`SELECT set_config('app.current_user_id', ${userId}, true)`;
  } catch {
    /* non-fatal */
  }
}
