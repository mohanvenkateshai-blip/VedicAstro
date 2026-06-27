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
loadEnvFile(join(root, ".env.local"));
loadEnvFile(join(root, ".env"));

// Allow: npm run db:schema -- 'postgres://...'
const cliUrl = process.argv[2]?.trim();
const url = (cliUrl || process.env.DATABASE_URL)?.trim();
if (!url) {
  console.error(`
DATABASE_URL is missing or empty.

Option A — paste connection string for this run only (safest):
  DATABASE_URL='postgres://USER:PASS@HOST/DB?sslmode=require' npm run db:schema

Option B — add to portal/.env.local (get value from Vercel or Neon):
  DATABASE_URL=postgres://...

  Vercel:  https://vercel.com → vedicastro → Settings → Environment Variables → DATABASE_URL → Reveal
  Neon:    https://console.neon.tech → project teal-prism → Connect → connection string

  Tip: also add DATABASE_URL to the **Development** environment in Vercel so
  \`vercel env pull\` works locally for \`npm run dev\`.

Option C — Neon SQL Editor (no local URL needed):
  1. Open Neon console → SQL Editor
  2. Paste contents of: portal/src/lib/auth/schema.sql
  3. Run
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

for (const stmt of statements) {
  console.log("→", stmt.split("\n")[0].slice(0, 72), "…");
  await sql.query(stmt);
}

console.log("✓ Schema applied (%d statements)", statements.length);
