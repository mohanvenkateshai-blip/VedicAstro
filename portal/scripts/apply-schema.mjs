#!/usr/bin/env node
/**
 * Apply portal/src/lib/auth/schema.sql to Neon Postgres.
 * Usage: DATABASE_URL=postgres://... node scripts/apply-schema.mjs
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { neon } from "@neondatabase/serverless";

const url = process.env.DATABASE_URL;
if (!url) {
  console.error("DATABASE_URL is required");
  process.exit(1);
}

const schemaPath = join(
  dirname(fileURLToPath(import.meta.url)),
  "../src/lib/auth/schema.sql",
);
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
