#!/usr/bin/env node
/**
 * Copy knowledge-graph structured books + patches into portal/data/
 * so Vercel (root=portal/) can read them at runtime.
 *
 * Run automatically via prebuild/predev in package.json.
 */
import fs from "fs";
import path from "path";

const PORTAL_ROOT = path.resolve(process.cwd());
const REPO_ROOT = path.resolve(PORTAL_ROOT, "..");
const SRC_STRUCTURED = path.join(REPO_ROOT, "knowledge-graph", "structured");
const SRC_PATCHES = path.join(REPO_ROOT, "knowledge-graph", "patches");
const DST_STRUCTURED = path.join(PORTAL_ROOT, "data", "structured");
const DST_PATCHES = path.join(PORTAL_ROOT, "data", "patches");

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

console.log(
  `[sync-structured] copied ${structuredCount} structured + ${patchCount} patch files → portal/data/`,
);
