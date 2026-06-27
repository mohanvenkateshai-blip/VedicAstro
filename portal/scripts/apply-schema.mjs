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
    if (!process.env[key]) process.env[key] = val;
  }
}

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
loadEnvFile(join(root, ".env.local"));
loadEnvFile(join(root, ".env"));

const url = process.env.DATABASE_URL?.trim();
if (!url) {
  console.error(`
DATABASE_URL is missing or empty.

You are already in the portal/ folder — run:
  npm run db:schema

If .env.local has DATABASE_URL="" (Vercel often omits secrets on pull), paste your
Neon connection string into .env.local:

  DATABASE_URL=postgres://user:pass@host/db?sslmode=require

Get it from: Vercel → Project → Settings → Environment Variables → DATABASE_URL
         or: Neon console → Connection string
`);
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
  await sql(stmt);
}

console.log("✓ Schema applied (%d statements)", statements.length);
