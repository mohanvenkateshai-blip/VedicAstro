#!/usr/bin/env node
/**
 * Apply portal/src/lib/auth/schema.sql to Neon Postgres.
 *
 * From the portal/ directory:
 *   npm run db:schema
 *
 * Or with an explicit URL:
 *   DATABASE_URL='postgres://...' node scripts/apply-schema.mjs
 */
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { neon } from "@neondatabase/serverless";

function loadEnvFile(path) {
  if (!existsSync(path)) return;
  for (const line of readFileSync(path, "utf8").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq < 0) continue;
    const key = trimmed.slice(0, eq).trim();
    let val = trimmed.slice(eq + 1).trim();
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1);
    }
    if (!val) continue;
    if (!process.env[key]) process.env[key] = val;
  }
}

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const envLocalPath = join(root, ".env.local");
loadEnvFile(envLocalPath);
loadEnvFile(join(root, ".env"));

// Allow: npm run db:schema -- 'postgres://...'
const cliUrl = process.argv[2]?.trim();
const url = (cliUrl || process.env.DATABASE_URL)?.trim();

function envLocalHasEmptyDatabaseUrl() {
  if (!existsSync(envLocalPath)) return false;
  return readFileSync(envLocalPath, "utf8")
    .split("\n")
    .some((line) => {
      const t = line.trim();
      if (!t.startsWith("DATABASE_URL=")) return false;
      const val = t.slice("DATABASE_URL=".length).trim().replace(/^["']|["']$/g, "");
      return val.length === 0;
    });
}

if (!url) {
  const vercelRedacted = envLocalHasEmptyDatabaseUrl();
  console.error(`
DATABASE_URL is missing or empty.
${vercelRedacted ? "\nYour .env.local has DATABASE_URL=\"\" — Vercel CLI never downloads secret values.\nRemove that line and paste the real Neon URL from the Vercel dashboard (Reveal).\n" : ""}
Option A — paste connection string for this run only (safest):
  DATABASE_URL='postgres://USER:PASS@HOST/DB?sslmode=require' npm run db:schema

Option B — add to portal/.env.local (get value from Vercel or Neon):
  DATABASE_URL=postgres://...

  Vercel:  https://vercel.com → vedicastro → Settings → Environment Variables → DATABASE_URL → Reveal
  Neon:    https://console.neon.tech → project teal-prism → Connect → connection string

  Note: \`vercel env pull\` and \`vercel env run\` cannot expose DATABASE_URL locally.

Option C — Neon SQL Editor (no local URL needed):
  1. Open Neon console → SQL Editor
  2. Paste contents of: portal/src/lib/auth/schema.sql
  3. Run

Production schema is already applied if /status shows Neon as "connected".
`);
  process.exit(1);
}

if (url.includes("YOUR_USER") || url.includes("YOUR_PASS") || url.includes("YOUR_HOST")) {
  console.error(
    "Replace YOUR_USER, YOUR_PASS, and YOUR_HOST with your real Neon connection string.",
  );
  process.exit(1);
}

const schemaPath = join(root, "src/lib/auth/schema.sql");
const sqlText = readFileSync(schemaPath, "utf8");
const statements = sqlText
  .split(";")
  .map((s) => s.replace(/--[^\n]*/g, "").trim())
  .filter(Boolean);

const sql = neon(url);

async function runStatement(stmt) {
  // Neon serverless v1.1+: use sql.query() for raw DDL — NOT sql(stmt)
  return sql.query(stmt, []);
}

for (const stmt of statements) {
  console.log("→", stmt.split("\n")[0].slice(0, 72), "…");
  try {
    await runStatement(stmt);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.includes("tagged-template")) {
      console.error(
        "\nNeon driver API error: use sql.query(stmt), not sql(stmt). Update apply-schema.mjs and retry.",
      );
    }
    throw e;
  }
}

console.log("✓ Schema applied (%d statements)", statements.length);
