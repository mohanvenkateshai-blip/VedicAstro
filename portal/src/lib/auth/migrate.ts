import "server-only";

import { readFileSync } from "node:fs";
import { join } from "node:path";

export type SchemaApplyResult = {
  applied: number;
  skipped?: boolean;
  already?: boolean;
};

let schemaPromise: Promise<SchemaApplyResult> | null = null;
let schemaDone = false;

function parseSchemaStatements(sqlText: string): string[] {
  return sqlText
    .split(";")
    .map((s) => s.replace(/--[^\n]*/g, "").trim())
    .filter(Boolean);
}

function schemaPath(): string {
  return join(process.cwd(), "src/lib/auth/schema.sql");
}

async function applySchemaInternal(): Promise<SchemaApplyResult> {
  const url = process.env.DATABASE_URL?.trim();
  if (!url) return { applied: 0, skipped: true };

  const mod = await import("@neondatabase/serverless");
  const sql = mod.neon(url);
  const statements = parseSchemaStatements(readFileSync(schemaPath(), "utf8"));

  for (const stmt of statements) {
    await sql.query(stmt, []);
  }

  return { applied: statements.length };
}

/**
 * Idempotent DDL from schema.sql — runs once per server instance when DATABASE_URL is set.
 * Called automatically from db client init on Vercel (production has the real URL).
 */
export async function ensureSchema(force = false): Promise<SchemaApplyResult> {
  if (!process.env.DATABASE_URL?.trim()) {
    return { applied: 0, skipped: true };
  }
  if (schemaDone && !force) {
    return { applied: 0, already: true };
  }
  if (!schemaPromise || force) {
    schemaPromise = applySchemaInternal()
      .then((result) => {
        schemaDone = true;
        return result;
      })
      .catch((e) => {
        schemaPromise = null;
        schemaDone = false;
        throw e;
      });
  }
  return schemaPromise;
}

/** Probe whether core tables exist (no DDL). */
export async function schemaTablesPresent(): Promise<boolean> {
  const url = process.env.DATABASE_URL?.trim();
  if (!url) return false;
  try {
    const mod = await import("@neondatabase/serverless");
    const sql = mod.neon(url);
    const rows = await sql.query(
      `SELECT EXISTS (
         SELECT 1 FROM information_schema.tables
         WHERE table_schema = 'public' AND table_name = 'users'
       ) AS ok`,
      [],
    );
    const row = Array.isArray(rows) ? rows[0] : rows;
    return Boolean(row && (row as { ok?: boolean }).ok);
  } catch {
    return false;
  }
}
