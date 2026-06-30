#!/usr/bin/env node
/**
 * Corpus-wide Learn verification (local FS only — no Supabase, no Gemini, no embeddings).
 *
 * Iterates real books from knowledge-graph/corpus-manifest.json (excludes AUDIT_SUMMARY).
 * Mirrors portal resolveStructuredBookSync + verify-structured-path enrichment path.
 *
 * Run from repo root or portal/:
 *   node portal/scripts/verify-all-learn-books.mjs
 *   cd portal && node scripts/verify-all-learn-books.mjs
 *
 * Exit 1 only if zero books resolve with chapters (catastrophic).
 */

import fs from "fs";
import path from "path";

const PORTAL_DIR = fs.existsSync(path.join(process.cwd(), "package.json")) &&
  fs.existsSync(path.join(process.cwd(), "scripts", "verify-structured-path.mjs"))
  ? process.cwd()
  : path.join(process.cwd(), "portal");
const ROOT = path.resolve(PORTAL_DIR, "..");

const MANIFEST_PATH = path.join(ROOT, "knowledge-graph", "corpus-manifest.json");
const EXCLUDE_STEMS = new Set(["AUDIT_SUMMARY"]);
const KNOWN_ZERO_CHAPTER = "Jataka_Tatva_Mahadeva";

const FORCE_KG = process.env.VERIFY_LEARN_FORCE_KG === "1";

function resolveDataDir(name) {
  if (FORCE_KG) return path.join(ROOT, "knowledge-graph", name);
  const bundled = path.join(PORTAL_DIR, "data", name);
  if (fs.existsSync(bundled)) return bundled;
  return path.join(ROOT, "knowledge-graph", name);
}

const STRUCTURED_DIR = resolveDataDir("structured");
const PATCHES_DIR = resolveDataDir("patches");

function getRawDir() {
  if (FORCE_KG) return path.join(ROOT, "knowledge-graph", "raw");
  const bundled = path.join(PORTAL_DIR, "data", "raw");
  if (fs.existsSync(bundled)) return bundled;
  return path.join(ROOT, "knowledge-graph", "raw");
}

const RAW_DIR = getRawDir();

function bookIdVariants(trimmed) {
  if (!trimmed) return [];
  const spaced = trimmed.replace(/[-_]+/g, " ");
  const underscored = trimmed.replace(/-/g, "_").replace(/\s+/g, "_");
  return [...new Set([trimmed, spaced, underscored, trimmed.replace(/_/g, "-")].filter(Boolean))];
}

function structuredLookupIds(...hints) {
  const out = [];
  for (const hint of hints) {
    if (!hint) continue;
    for (const v of bookIdVariants(hint)) out.push(v);
  }
  return [...new Set(out)];
}

/** Exact copy of books.ts resolveStructuredBookSync (requires chapters.length > 0). */
function resolveStructuredBookSync(...hints) {
  const ids = structuredLookupIds(...hints);
  if (!ids.length) return null;

  try {
    if (!fs.existsSync(STRUCTURED_DIR)) return null;

    for (const id of ids) {
      for (const stem of [id, id.replace(/\s+/g, "_")]) {
        const p = path.join(STRUCTURED_DIR, `${stem}.json`);
        if (fs.existsSync(p)) {
          const data = JSON.parse(fs.readFileSync(p, "utf8"));
          if (data?.chapters?.length) return data;
        }
      }
    }

    const norm = (s) => (s || "").toLowerCase().replace(/[-_\s]+/g, "");
    const idNorms = new Set(ids.map(norm).filter(Boolean));

    for (const f of fs.readdirSync(STRUCTURED_DIR).filter((fn) => fn.endsWith(".json"))) {
      if (f === "AUDIT_SUMMARY.json") continue;
      const full = path.join(STRUCTURED_DIR, f);
      const data = JSON.parse(fs.readFileSync(full, "utf8"));
      if (!data?.chapters?.length) continue;
      const keys = [
        data.book_id,
        data.canonical_name,
        data.source_file?.replace(/\.md$/i, ""),
        f.replace(/\.json$/i, ""),
      ];
      if (keys.some((k) => k && idNorms.has(norm(k)))) return data;
      if (keys.some((k) => k && ids.some((id) => k.toLowerCase().includes(id.toLowerCase())))) return data;
    }
  } catch {}
  return null;
}

/** Load structured JSON even when chapters array is empty (diagnostics). */
function loadStructuredFileRaw(bookStem) {
  const candidates = [
    path.join(STRUCTURED_DIR, `${bookStem}.json`),
    path.join(STRUCTURED_DIR, `${bookStem.replace(/\s+/g, "_")}.json`),
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) {
      try {
        return JSON.parse(fs.readFileSync(p, "utf8"));
      } catch {}
    }
  }
  return null;
}

function chaptersFromStructured(sb) {
  const out = [];
  (sb.chapters || []).forEach((ch) => {
    out.push({
      id: ch.id,
      title: ch.title,
      properties: { level: ch.level ?? 1, structured: true },
      nodeIds: [],
    });
    (ch.sections || []).forEach((sec) => {
      out.push({
        id: sec.id,
        title: sec.title,
        properties: { level: sec.level ?? 2, structured: true },
        nodeIds: [],
      });
    });
  });
  return out;
}

function loadNodeChapterPatch(bookId) {
  try {
    if (bookId) {
      const variants = [bookId, bookId.replace(/\s+/g, "_"), bookId.replace(/ /g, "_")].filter(
        (v, i, a) => v && a.indexOf(v) === i,
      );
      for (const v of variants) {
        const perBookPath = path.join(PATCHES_DIR, `patch-${v}.json`);
        if (fs.existsSync(perBookPath)) {
          return JSON.parse(fs.readFileSync(perBookPath, "utf8"));
        }
      }
      if (fs.existsSync(PATCHES_DIR)) {
        const files = fs.readdirSync(PATCHES_DIR).filter((f) => f.startsWith("patch-") && f.endsWith(".json"));
        for (const f of files) {
          try {
            const data = JSON.parse(fs.readFileSync(path.join(PATCHES_DIR, f), "utf8"));
            const bks = data.books || [];
            const bid = data.book_id || "";
            if (
              bks.includes(bookId) ||
              bid === bookId ||
              bks.some((b) => (b || "").toLowerCase().includes(bookId.toLowerCase())) ||
              (bid || "").toLowerCase().includes(bookId.toLowerCase())
            ) {
              return data;
            }
          } catch {}
        }
      }
    }
    const mapPath = path.join(PATCHES_DIR, "node-chapter-map.json");
    if (fs.existsSync(mapPath)) {
      return JSON.parse(fs.readFileSync(mapPath, "utf8"));
    }
  } catch {}
  return null;
}

function enrichChaptersWithNodeIds(chapters, bookId, patch) {
  if (!patch?.patches?.length) return chapters;
  const byChapter = new Map();
  const norm = (s) => (s || "").toLowerCase().replace(/\s+/g, "_");
  const bookKey = norm(bookId);
  for (const p of patch.patches) {
    const bid = norm(p.book_id || "");
    if (!bid || (!bid.includes(bookKey) && bookKey !== bid)) continue;
    const arr = byChapter.get(p.chapter_id) || [];
    if (p.node_id) arr.push(p.node_id);
    byChapter.set(p.chapter_id, arr);
  }
  return chapters.map((ch) => ({
    ...ch,
    nodeIds: byChapter.get(ch.id) || ch.nodeIds || [],
  }));
}

function loadRawMarkdown(bookStem) {
  const candidates = [
    path.join(RAW_DIR, `${bookStem}.md`),
    path.join(RAW_DIR, `${bookStem.replace(/\s+/g, "_")}.md`),
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) return fs.readFileSync(p, "utf8");
  }
  try {
    const norm = (s) => (s || "").toLowerCase().replace(/[-_\s–—]+/g, "");
    const want = norm(bookStem);
    for (const f of fs.readdirSync(RAW_DIR).filter((x) => x.toLowerCase().endsWith(".md"))) {
      const have = norm(f.replace(/\.md$/i, ""));
      if (have === want || have.includes(want) || want.includes(have)) {
        return fs.readFileSync(path.join(RAW_DIR, f), "utf8");
      }
    }
  } catch {}
  return null;
}

function sectionsFromStructured(sb, fullMarkdown) {
  if (!sb?.chapters?.length || !fullMarkdown) return [];
  const lines = fullMarkdown.split(/\r?\n/);
  const blocks = [];
  for (const ch of sb.chapters) {
    const hasSections = !!(ch.sections && ch.sections.length > 0);
    const chStart = typeof ch.start_line === "number" ? ch.start_line : 0;
    const chEndEx = typeof ch.end_line === "number" ? ch.end_line + 1 : lines.length;

    if (hasSections && ch.sections) {
      const lead = lines.slice(Math.max(0, chStart), Math.min(lines.length, chEndEx)).join("\n").trim();
      const headerContent = lead.split("\n").slice(0, 3).join("\n").trim() || ch.title;
      blocks.push({ id: ch.id, title: ch.title, content: headerContent });
      for (const sec of ch.sections) {
        const sStart = typeof sec.start_line === "number" ? sec.start_line : chStart;
        const sEndEx = typeof sec.end_line === "number" ? sec.end_line + 1 : chEndEx;
        const content = lines.slice(Math.max(0, sStart), Math.min(lines.length, sEndEx)).join("\n").trim();
        if (content) blocks.push({ id: sec.id, title: sec.title, content });
      }
    } else {
      const content = lines.slice(Math.max(0, chStart), Math.min(lines.length, chEndEx)).join("\n").trim();
      if (content) blocks.push({ id: ch.id, title: ch.title, content });
    }
  }
  return blocks;
}

function patchNodeCountForBook(patch, bookStem) {
  if (!patch?.patches?.length) return 0;
  const norm = (s) => (s || "").toLowerCase().replace(/\s+/g, "_");
  const bookKey = norm(bookStem);
  return patch.patches.filter((p) => {
    const bid = norm(p.book_id || "");
    return bid && (bid.includes(bookKey) || bookKey.includes(bid) || bookKey === bid);
  }).length;
}

function loadManifestBooks() {
  const manifest = JSON.parse(fs.readFileSync(MANIFEST_PATH, "utf8"));
  const sources = manifest.sources || manifest;
  return Object.keys(sources)
    .filter((k) => k.endsWith(".md"))
    .map((k) => k.replace(/\.md$/i, ""))
    .filter((stem) => !EXCLUDE_STEMS.has(stem))
    .sort();
}

function main() {
  const books = loadManifestBooks();
  const rows = [];
  let structuredPass = 0;
  let fallbackOnly = 0;
  let zeroChapter = 0;
  let chapterSum = 0;
  let withPatchNodes = 0;
  let withSections = 0;

  for (const stem of books) {
    const rawFile = loadStructuredFileRaw(stem);
    const resolved = resolveStructuredBookSync(stem, rawFile?.canonical_name, rawFile?.book_id);
    const chCount = resolved?.chapters?.length ?? 0;
    const rawPresent = !!loadRawMarkdown(stem);
    const patch = loadNodeChapterPatch(stem) || loadNodeChapterPatch(rawFile?.canonical_name);
    const patchNodes = patchNodeCountForBook(patch, stem);

    let bucket;
    if (chCount > 0) {
      bucket = "structured-pass";
      structuredPass++;
      chapterSum += chCount;
    } else if (rawFile && Array.isArray(rawFile.chapters) && rawFile.chapters.length === 0) {
      bucket = "zero-chapter";
      zeroChapter++;
    } else {
      bucket = "fallback-only";
      fallbackOnly++;
    }

    let enrichedChaptersWithNodes = 0;
    let sectionBlocks = 0;
    if (resolved) {
      let chapters = chaptersFromStructured(resolved);
      chapters = enrichChaptersWithNodeIds(chapters, stem, patch);
      if (chapters.every((c) => (c.nodeIds || []).length === 0) && rawFile?.canonical_name) {
        chapters = enrichChaptersWithNodeIds(chapters, rawFile.canonical_name, patch);
      }
      enrichedChaptersWithNodes = chapters.filter(
        (c) => ((c.properties && c.properties.level) || 1) === 1 && (c.nodeIds || []).length > 0,
      ).length;
      if (enrichedChaptersWithNodes > 0) withPatchNodes++;

      if (rawPresent) {
        const md = loadRawMarkdown(stem);
        sectionBlocks = sectionsFromStructured(resolved, md).length;
        if (sectionBlocks > 0) withSections++;
      }
    }

    const flag =
      stem === KNOWN_ZERO_CHAPTER
        ? "KNOWN_EDGE"
        : bucket === "zero-chapter"
          ? "ZERO"
          : "";

    rows.push({
      stem,
      bucket,
      ch: chCount,
      raw: rawPresent ? "Y" : "-",
      patchN: patchNodes,
      chNodes: enrichedChaptersWithNodes,
      secs: sectionBlocks,
      flag,
    });
  }

  const total = books.length;
  const avgCh = structuredPass ? (chapterSum / structuredPass).toFixed(1) : "0";

  console.log("VERIFY ALL LEARN BOOKS (local FS only)");
  console.log(`manifest: ${MANIFEST_PATH}`);
  console.log(`structured: ${STRUCTURED_DIR}`);
  console.log(`patches:  ${PATCHES_DIR}`);
  console.log(`raw:      ${RAW_DIR}`);
  console.log("");

  console.log("SUMMARY");
  console.log(`  total manifest books:     ${total}`);
  console.log(`  structured-pass:          ${structuredPass}`);
  console.log(`  fallback-only:            ${fallbackOnly}`);
  console.log(`  zero-chapter (structured): ${zeroChapter}`);
  console.log(`  avg chapters (pass only): ${avgCh}`);
  console.log(`  with patch nodes on ≥1 ch: ${withPatchNodes}`);
  console.log(`  with md sections (raw+TOC): ${withSections}`);
  console.log(`  known edge ${KNOWN_ZERO_CHAPTER}: flagged in table`);
  console.log("");

  const problems = rows.filter((r) => r.flag === "ZERO" && r.stem !== KNOWN_ZERO_CHAPTER);
  if (problems.length) {
    console.log("UNEXPECTED zero-chapter (besides known edge):");
    for (const p of problems) console.log(`  - ${p.stem}`);
    console.log("");
  }

  console.log("stem | bucket | ch | raw | patchN | ch w/nodes | secs | flag");
  for (const r of rows) {
    if (r.flag || r.bucket !== "structured-pass") {
      console.log(
        `${r.stem} | ${r.bucket} | ${r.ch} | ${r.raw} | ${r.patchN} | ${r.chNodes} | ${r.secs} | ${r.flag}`,
      );
    }
  }
  const quietPass = rows.filter((r) => r.bucket === "structured-pass" && !r.flag).length;
  console.log(`(... ${quietPass} structured-pass books omitted from table)`);
  console.log("");

  if (structuredPass === 0) {
    console.error("CATASTROPHIC: no books resolved with chapters > 0");
    process.exit(1);
  }
  process.exit(0);
}

main();
