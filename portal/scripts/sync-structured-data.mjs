#!/usr/bin/env node
/**
 * Sync knowledge-graph artifacts into portal/data/ for runtime access.
 *
 * PURPOSE:
 *   - Vercel deploys with root=portal/, so sibling paths like ../knowledge-graph/*
 *     are NOT available at runtime.
 *   - Structured JSON, patches, and raw markdown are copied into portal/data/*
 *     during predev/prebuild so they are bundled and always present.
 *
 * RESOLUTION ORDER (see src/lib/books.ts):
 *   1) For dev: loadLocalRawMarkdown prefers the monorepo sibling
 *      ../knowledge-graph/raw/ (no copy cost, always fresh).
 *   2) If portal/data/raw/ exists (populated by this script or committed bundle),
 *      it is used first — this is the path for production Vercel builds.
 *
 * RAW COPYING:
 *   - ~61 files, ~21 MB total. Not "large" by modern standards; acceptable to copy.
 *   - Only *.md files are copied (byte-for-byte).
 *   - If the source sibling has no raw/ or is empty (fresh clone without the files),
 *     this step copies 0 files and the app falls back to Supabase corpus-vault.
 *   - To guarantee all books have local raw in a production bundle, ensure the
 *     files exist locally under knowledge-graph/raw/, run this sync, then commit
 *     the resulting portal/data/raw/* contents (they are not gitignored).
 *
 * Run automatically via prebuild/predev in package.json.
 * You can also run directly: node scripts/sync-structured-data.mjs
 */
import fs from "fs";
import path from "path";

const PORTAL_ROOT = path.resolve(process.cwd());
const REPO_ROOT = path.resolve(PORTAL_ROOT, "..");
const SRC_STRUCTURED = path.join(REPO_ROOT, "knowledge-graph", "structured");
const SRC_PATCHES = path.join(REPO_ROOT, "knowledge-graph", "patches");
const SRC_RAW = path.join(REPO_ROOT, "knowledge-graph", "raw");
const DST_STRUCTURED = path.join(PORTAL_ROOT, "data", "structured");
const DST_PATCHES = path.join(PORTAL_ROOT, "data", "patches");
const DST_RAW = path.join(PORTAL_ROOT, "data", "raw");

function copyDir(src, dst, filter) {
  if (!fs.existsSync(src)) {
    console.warn(`[sync-structured] skip — source missing: ${src}`);
    return 0;
  }
  fs.mkdirSync(dst, { recursive: true });
  const files = fs.readdirSync(src).filter(filter);
  for (const f of files) {
    fs.copyFileSync(path.join(src, f), path.join(dst, f));
  }
  return files.length;
}

const structuredCount = copyDir(SRC_STRUCTURED, DST_STRUCTURED, (f) => f.endsWith(".json"));
const patchCount = copyDir(SRC_PATCHES, DST_PATCHES, (f) => f.endsWith(".json"));

/**
 * Copy raw markdown sources.
 * We intentionally copy ALL .md so that loadLocalRawMarkdown can resolve any
 * of the 61+ classical texts by storage_path stem, canonical name, or fuzzy match.
 * This enables full-chapter rendering from local files without Supabase in both
 * dev (via sibling) and production bundles (via the copied portal/data/raw/).
 */
const rawCount = copyDir(SRC_RAW, DST_RAW, (f) => f.toLowerCase().endsWith(".md"));

console.log(
  `[sync-structured] copied ${structuredCount} structured + ${patchCount} patch + ${rawCount} raw → portal/data/`,
);
