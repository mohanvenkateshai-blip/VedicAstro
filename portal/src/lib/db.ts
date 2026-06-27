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

type SqlQuery = ReturnType<NeonQueryFunction<any, any>>;

/**
 * Run a query with RLS context set in the same Neon transaction.
 * `makeQuery` must return a tagged-template query (not a Promise).
 */
export async function withUserContext<T>(
  userId: string,
  makeQuery: (s: NeonQueryFunction<any, any>) => SqlQuery,
): Promise<T> {
  const s = await getSql();
  if (!s) throw new Error("DATABASE_URL not configured");

  const txFn = (s as NeonQueryFunction<any, any> & { transaction?: Function })
    .transaction;

  if (typeof txFn !== "function") {
    await setRlsContext(userId);
    return (await makeQuery(s)) as T;
  }

  const results = await txFn.call(s, [
    s`SELECT set_config('app.current_user_id', ${userId}, true)`,
    makeQuery(s),
  ]);

  const last = Array.isArray(results) ? results[results.length - 1] : results;
  return last as T;
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
  } catch {
    /* non-fatal */
  }
}
