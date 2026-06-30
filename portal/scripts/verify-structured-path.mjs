#!/usr/bin/env node
/**
 * Minimal verification of the EXACT structured book data path used by portal
 * for BookReaderClient, WITHOUT any Supabase or server-only imports.
 *
 * Exercises (reimplemented precisely from books.ts):
 *   loadStructuredBook, chaptersFromStructured, loadNodeChapterPatch,
 *   enrichChaptersWithNodeIds, buildNodeProvenanceMap, sectionsFromStructured
 *
 * Run from portal/:
 *   node scripts/verify-structured-path.mjs
 */

import fs from "fs";
import path from "path";

const ROOT = path.resolve(process.cwd(), ".."); // from portal/ -> repo root
const STRUCTURED_DIR = path.join(ROOT, "knowledge-graph", "structured");
const PATCHES_DIR = path.join(ROOT, "knowledge-graph", "patches");
const RAW_DIR = path.join(ROOT, "knowledge-graph", "raw");

function loadStructuredBook(bookId) {
  try {
    const candidates = [
      path.join(STRUCTURED_DIR, `${bookId}.json`),
      path.join(STRUCTURED_DIR, `${bookId.replace(/\s+/g, "_")}.json`),
    ];
    for (const p of candidates) {
      if (fs.existsSync(p)) {
        const raw = fs.readFileSync(p, "utf8");
        return JSON.parse(raw);
      }
    }
    if (fs.existsSync(STRUCTURED_DIR)) {
      const files = fs.readdirSync(STRUCTURED_DIR).filter(f => f.endsWith(".json"));
      for (const f of files) {
        const full = path.join(STRUCTURED_DIR, f);
        const data = JSON.parse(fs.readFileSync(full, "utf8"));
        if (
          data.book_id === bookId ||
          (data.canonical_name || "").toLowerCase().includes(bookId.toLowerCase()) ||
          (data.source_file || "").includes(bookId)
        ) {
          return data;
        }
      }
    }
  } catch {}
  return null;
}

function chaptersFromStructured(sb) {
  const out = [];
  (sb.chapters || []).forEach((ch) => {
    out.push({
      id: ch.id,
      title: ch.title,
      order: out.length,
      sourceLocation: ch.number ? `Chapter ${ch.number}` : undefined,
      nodeIds: [],
      properties: { level: ch.level ?? 1, structured: true, hasSections: !!(ch.sections && ch.sections.length), start_line: ch.start_line, end_line: ch.end_line },
    });
    (ch.sections || []).forEach((sec) => {
      out.push({
        id: sec.id,
        title: sec.title,
        order: out.length,
        sourceLocation: undefined,
        nodeIds: [],
        properties: { level: sec.level ?? 2, structured: true, parentChapter: ch.id, start_line: sec.start_line, end_line: sec.end_line },
      });
    });
  });
  return out;
}

function loadNodeChapterPatch(bookId) {
  try {
    if (bookId) {
      const variants = [
        bookId,
        bookId.replace(/\s+/g, "_"),
        bookId.replace(/ /g, "_"),
      ].filter((v, i, a) => v && a.indexOf(v) === i);
      for (const v of variants) {
        const perBookPath = path.join(PATCHES_DIR, `patch-${v}.json`);
        if (fs.existsSync(perBookPath)) {
          const raw = fs.readFileSync(perBookPath, "utf8");
          return JSON.parse(raw);
        }
      }
      if (fs.existsSync(PATCHES_DIR)) {
        const files = fs.readdirSync(PATCHES_DIR).filter((f) => f.startsWith("patch-") && f.endsWith(".json"));
        for (const f of files) {
          const full = path.join(PATCHES_DIR, f);
          try {
            const data = JSON.parse(fs.readFileSync(full, "utf8"));
            const bks = (data.books || []);
            const bid = (data.book_id || "");
            if (bks.includes(bookId) || bid === bookId || bks.some((b) => (b || "").toLowerCase().includes(bookId.toLowerCase())) || (bid || "").toLowerCase().includes(bookId.toLowerCase())) {
              return data;
            }
          } catch {}
        }
      }
    }
    const PATCH_PATH = path.join(PATCHES_DIR, "node-chapter-map.json");
    if (fs.existsSync(PATCH_PATH)) {
      const raw = fs.readFileSync(PATCH_PATH, "utf8");
      return JSON.parse(raw);
    }
  } catch {}
  return null;
}

function buildNodeProvenanceMap(patch, bookId) {
  const map = {};
  if (!patch?.patches?.length) return map;
  const norm = (s) => (s || "").toLowerCase().replace(/\s+/g, "_");
  const bookKey = bookId ? norm(bookId) : null;
  for (const p of patch.patches) {
    if (!p.node_id) continue;
    if (bookKey) {
      const bid = norm(p.book_id || "");
      if (bid && !bid.includes(bookKey) && bookKey !== bid) continue;
    }
    map[p.node_id] = {
      chapter_id: p.chapter_id,
      section_id: p.section_id ?? null,
      hierarchy_path: p.hierarchy_path,
      method: p.method,
      confidence: p.confidence,
      matched_on: p.matched_on,
    };
  }
  return map;
}

function enrichChaptersWithNodeIds(chapters, bookId, patch) {
  if (!patch || !patch.patches || patch.patches.length === 0) return chapters;
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

function sectionsFromStructured(sb, fullMarkdown) {
  if (!sb?.chapters?.length || !fullMarkdown || typeof fullMarkdown !== "string") return [];
  const lines = fullMarkdown.split(/\r?\n/);
  const blocks = [];
  for (const ch of sb.chapters) {
    const hasSections = !!(ch.sections && ch.sections.length > 0);
    const chStart = typeof ch.start_line === "number" ? ch.start_line : 0;
    const chEndEx = typeof ch.end_line === "number" ? ch.end_line + 1 : lines.length;

    if (hasSections && ch.sections) {
      const lead = lines.slice(Math.max(0, chStart), Math.min(lines.length, chEndEx)).join("\n").trim();
      const headerContent = lead.split("\n").slice(0, 3).join("\n").trim() || ch.title;
      blocks.push({ id: ch.id, title: ch.title || `Chapter ${ch.number || ""}`.trim(), content: headerContent });

      for (const sec of ch.sections) {
        const sStart = typeof sec.start_line === "number" ? sec.start_line : chStart;
        const sEndEx = typeof sec.end_line === "number" ? sec.end_line + 1 : chEndEx;
        const content = lines.slice(Math.max(0, sStart), Math.min(lines.length, sEndEx)).join("\n").trim();
        if (content) {
          blocks.push({ id: sec.id, title: sec.title, content });
        }
      }
    } else {
      const content = lines.slice(Math.max(0, chStart), Math.min(lines.length, chEndEx)).join("\n").trim();
      if (content) {
        blocks.push({
          id: ch.id,
          title: ch.title || `Chapter ${ch.number || ""}`.trim(),
          content,
        });
      }
    }
  }
  return blocks;
}

function loadRawMarkdown(bookIdOrStem) {
  const candidates = [
    path.join(RAW_DIR, `${bookIdOrStem}.md`),
    path.join(RAW_DIR, `${bookIdOrStem.replace(/\s+/g, "_")}.md`),
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) return fs.readFileSync(p, "utf8");
  }
  // fuzzy
  if (fs.existsSync(RAW_DIR)) {
    const files = fs.readdirSync(RAW_DIR).filter(f => f.endsWith(".md"));
    for (const f of files) {
      if (f.toLowerCase().includes(bookIdOrStem.toLowerCase().replace(/_/g, ""))) {
        return fs.readFileSync(path.join(RAW_DIR, f), "utf8");
      }
    }
  }
  return null;
}

function printEvidence(label, obj) {
  console.log(`\n=== ${label} ===`);
  console.dir(obj, { depth: 3, colors: false });
}

function analyzeChapters(chapters) {
  const ids = chapters.map(c => c.id);
  const titles = chapters.map(c => c.title);
  const levels = chapters.map(c => (c.properties && c.properties.level) || 1);
  const nodeIdCounts = chapters.map(c => (c.nodeIds || []).length);
  const hasCh0 = ids.some(id => /^ch-0\b/i.test(id) || id === "ch-0");
  const frontmatterTitles = titles.filter(t => /^(frontmatter|h1|main|untitled|unknown|start)$/i.test((t || "").trim()));
  const numericOrderCheck = (() => {
    // Extract first number from title or id for ch-N
    const nums = ids.map((id, i) => {
      const m = id.match(/ch-(\d+)/i);
      return m ? parseInt(m[1], 10) : null;
    }).filter(n => n != null);
    if (!nums.length) return { ordered: null, nums };
    const sorted = [...nums].sort((a,b)=>a-b);
    return { ordered: JSON.stringify(nums) === JSON.stringify(sorted), nums };
  })();
  return { ids, titles, levels, nodeIdCounts, hasCh0, frontmatterTitles, numericOrderCheck };
}

function main() {
  console.log("VERIFY: structured book data path (no Supabase)");
  console.log("cwd:", process.cwd());
  console.log("STRUCTURED_DIR:", STRUCTURED_DIR);
  console.log("PATCHES_DIR:", PATCHES_DIR);
  console.log("RAW_DIR:", RAW_DIR);

  const booksToTest = [
    { arg: "Ashtakavarga_System_Comprehensive_Handbook", label: "Ashtakavarga" },
    { arg: "Saravali", label: "Saravali" },
  ];

  for (const { arg, label } of booksToTest) {
    console.log(`\n\n========== ${label} (${arg}) ==========`);

    const structured = loadStructuredBook(arg);
    if (!structured) {
      console.log("  [MISS] loadStructuredBook returned null");
      continue;
    }
    console.log("  loadStructuredBook: ok");
    console.log("    book_id:", structured.book_id);
    console.log("    canonical_name:", structured.canonical_name);
    console.log("    chapters in structured:", (structured.chapters || []).length);

    let chapters = chaptersFromStructured(structured);
    console.log("  chaptersFromStructured: produced", chapters.length, "flat entries (chapters + sections)");

    const patch = loadNodeChapterPatch(arg) || loadNodeChapterPatch(structured.canonical_name) || loadNodeChapterPatch();
    console.log("  loadNodeChapterPatch:", patch ? `ok, ${patch.patches?.length || 0} patches` : "null");

    const beforeNodeIds = chapters.map(c => (c.nodeIds || []).length);
    chapters = enrichChaptersWithNodeIds(chapters, arg, patch);
    if (structured.canonical_name) {
      const allZero = chapters.every(c => (c.nodeIds || []).length === 0);
      if (allZero) chapters = enrichChaptersWithNodeIds(chapters, structured.canonical_name, patch);
    }
    const afterNodeIds = chapters.map(c => (c.nodeIds || []).length);
    console.log("  enrichChaptersWithNodeIds: before zeros=", beforeNodeIds.filter(n=>n===0).length, "after zeros=", afterNodeIds.filter(n=>n===0).length);

    const nodeProvMap = buildNodeProvenanceMap(patch, arg) || buildNodeProvenanceMap(patch, structured.canonical_name);
    const provEntries = Object.entries(nodeProvMap);
    console.log("  buildNodeProvenanceMap: entries=", provEntries.length);

    const rawMd = loadRawMarkdown(arg) || loadRawMarkdown(structured.source_file?.replace(/\.md$/, "") || "");
    let mdSections = [];
    if (rawMd && structured) {
      mdSections = sectionsFromStructured(structured, rawMd);
    }
    console.log("  sectionsFromStructured: produced", mdSections.length, "content blocks");

    // Evidence prints
    const analysis = analyzeChapters(chapters);
    printEvidence(`${label} — chapters passed to BookReaderClient (first 12)`, chapters.slice(0, 12).map(c => ({
      id: c.id,
      title: c.title,
      level: (c.properties && c.properties.level) || 1,
      nodeIdsCount: (c.nodeIds || []).length,
      nodeIdsSample: (c.nodeIds || []).slice(0, 2),
    })));
    printEvidence(`${label} — chapter id list (all)`, analysis.ids);
    printEvidence(`${label} — titles (all)`, analysis.titles);
    printEvidence(`${label} — levels (all)`, analysis.levels);
    printEvidence(`${label} — nodeId counts per chapter entry`, afterNodeIds);
    printEvidence(`${label} — sample mdSections (first 2)`, mdSections.slice(0, 2).map(s => ({ id: s.id, title: s.title })));
    printEvidence(`${label} — sample nodeProvMap entries (up to 5)`, Object.fromEntries(provEntries.slice(0, 5)));

    // Confirmations
    console.log("\n--- Confirmations for", label, "---");
    console.log("no ch-0:", !analysis.hasCh0, "(hasCh0=", analysis.hasCh0, ")");
    console.log("no frontmatter titles:", analysis.frontmatterTitles.length === 0, "(found:", analysis.frontmatterTitles, ")");
    if (label === "Ashtakavarga") {
      console.log("numeric chapter order:", analysis.numericOrderCheck.ordered, "nums:", analysis.numericOrderCheck.nums);
    }
    const chaptersWithNodes = chapters.filter((c, i) => (afterNodeIds[i] || 0) > 0 && ((c.properties && c.properties.level) || 1) === 1);
    console.log("nodeIds attached on chapter-level entries:", chaptersWithNodes.length > 0);
    const provWithHierarchy = provEntries.filter(([,v]) => v && v.hierarchy_path).length;
    console.log("provenance hierarchy present for some:", provWithHierarchy > 0, "(count with hierarchy_path:", provWithHierarchy, ")");

    // What left nav would render
    const leftNavRender = chapters.map((c, idx) => {
      const level = (c.properties && c.properties.level) || 1;
      const isSection = level > 1;
      return { idx, id: c.id, title: c.title, level, isSection };
    });
    printEvidence(`${label} — left nav would render (id, title, level, isSection)`, leftNavRender);

    // Content block ids for jumps (from chapters and from sections)
    const chapterIdsForJumps = chapters.map(c => c.id);
    const sectionBlockIds = mdSections.map(s => s.id);
    console.log("\nContent block ids for jumps (chapters prop):", chapterIdsForJumps);
    console.log("Content block ids for jumps (sections prop):", sectionBlockIds);

    // Props that would go to BookReaderClient
    const propsForClient = {
      chapters: chapters.map(c => ({
        id: c.id,
        title: c.title,
        sourceLocation: c.sourceLocation,
        nodeIds: c.nodeIds,
        properties: c.properties,
      })),
      sections: mdSections.length ? mdSections : null,
      nodeProvenance: Object.keys(nodeProvMap).length ? nodeProvMap : {},
    };
    // Avoid dumping huge nodeProvenance; summarize + sample
    const provSample = Object.fromEntries(Object.entries(nodeProvMap).slice(0, 3));
    printEvidence(`${label} — props passed to <BookReaderClient ...> (chapters summary + sections sample + nodeProvenance sample)`, {
      chaptersCount: propsForClient.chapters.length,
      chaptersSample: propsForClient.chapters.slice(0, 4),
      sectionsCount: propsForClient.sections ? propsForClient.sections.length : 0,
      sectionsSample: propsForClient.sections ? propsForClient.sections.slice(0, 2) : null,
      nodeProvenanceKeys: Object.keys(nodeProvMap).length,
      nodeProvenanceSample: provSample,
    });

    // Final quick assertions for Ashtakavarga
    if (label === "Ashtakavarga") {
      const ch1 = chapters.find(c => c.id === "ch-1");
      const ch1sec = chapters.find(c => c.id === "ch-1-sec-authoritative_classical_source_documents");
      console.log("\nAshtakavarga specific:");
      console.log("  ch-1 present with nodeIds > 0 after enrich?", !!(ch1 && (ch1.nodeIds || []).length > 0), "nodeIds:", ch1 && ch1.nodeIds);
      console.log("  ch-1 section present?", !!ch1sec);
      console.log("  first mdSection id/title:", mdSections[0] && { id: mdSections[0].id, title: mdSections[0].title });
    }
  }

  console.log("\n\n=== DONE ===");
}

main();
