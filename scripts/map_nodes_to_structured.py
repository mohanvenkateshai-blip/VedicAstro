#!/usr/bin/env python3
"""
Map KE graph nodes to structured book chapters/sections.

For each structured book:
- Load its chapter/section hierarchy (with line ranges into raw md)
- Find matching nodes by source_file
- Attach chapter_id, section_id (best effort), hierarchy_path

Matching order (combined scoring):
1. Explicit: parse source_location for "Chapter N" / ch-N numbers
2. Title match: fuzzy against chapter + section titles (difflib)
3. Phrase lookup: search distinctive phrases from label/rule_text inside chapter text slices

Non-destructive: always writes a patch JSON with the proposed enrichments.
--dry-run prints samples and stats without side effects beyond the patch file.

Usage:
  python scripts/map_nodes_to_structured.py \
    --books "Ashtakavarga_System_Comprehensive_Handbook,Brihat_Parasara_Hora_Sastra_Vol_1" \
    --dry-run \
    --graph knowledge-graph/graphify-out/graph.json

Outputs sample mappings proving "KE TEXT is mapped to the source book chapters".
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STRUCTURED_DIR = ROOT / "knowledge-graph" / "structured"
RAW_DIR = ROOT / "knowledge-graph" / "raw"
DEFAULT_GRAPH = ROOT / "knowledge-graph" / "graphify-out" / "graph.json"
DEFAULT_PATCH_OUT = ROOT / "knowledge-graph" / "patches" / "node-chapter-map.json"

# --- env / supabase helpers (optional path) ---

def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    for k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        v = os.environ.get(k, "").strip()
        if v:
            out[k] = v
    env_local = ROOT / "portal" / ".env.local"
    if env_local.is_file():
        for line in env_local.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY") and k not in out:
                out[k] = v
    return out


def fetch_nodes_via_supabase(stems: list[str], graph_version: str = "newbooks-v1") -> list[dict]:
    """Best-effort fetch nodes for the given book stems from Supabase.
    Uses REST if supabase lib not present. Returns [] on any failure (caller falls back to file).
    """
    env = load_env()
    url = env.get("SUPABASE_URL")
    key = env.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return []
    try:
        import requests  # type: ignore
    except Exception:
        return []
    # We query graph_nodes with ilike on source_file for each stem
    nodes: list[dict] = []
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    for stem in stems:
        # Try several candidate patterns, mirroring the TS books.ts logic
        candidates = [
            f"raw/{stem}.md",
            f"%{stem}%",
            f"%{stem.replace('_', ' ')}%",
        ]
        got = False
        for cand in candidates:
            try:
                params = {
                    "select": "id,label,source_file,source_location,properties,community,norm_label,description,rule_text",
                    "graph_version": f"eq.{graph_version}",
                    "source_file": f"ilike.{cand}",
                    "limit": "2000",
                }
                r = requests.get(f"{url}/rest/v1/graph_nodes", headers=headers, params=params, timeout=30)
                if r.ok:
                    batch = r.json()
                    if batch:
                        nodes.extend(batch)
                        got = True
                        break
            except Exception:
                continue
        if not got:
            # last try: broader ilike on stem words
            try:
                short = stem.split("_")[0]
                params = {
                    "select": "id,label,source_file,source_location,properties,community,norm_label,description,rule_text",
                    "graph_version": f"eq.{graph_version}",
                    "source_file": f"ilike.%{short}%",
                    "limit": "2000",
                }
                r = requests.get(f"{url}/rest/v1/graph_nodes", headers=headers, params=params, timeout=30)
                if r.ok:
                    nodes.extend([n for n in r.json() if stem.split("_")[0].lower() in (n.get("source_file") or "").lower()])
            except Exception:
                pass
    # Dedup by id
    seen = set()
    uniq = []
    for n in nodes:
        if n["id"] not in seen:
            seen.add(n["id"])
            uniq.append(n)
    return uniq


# --- data loading ---

def load_structured(stem: str) -> dict[str, Any] | None:
    p = STRUCTURED_DIR / f"{stem}.json"
    if not p.exists():
        # fuzzy
        for f in STRUCTURED_DIR.glob("*.json"):
            if stem.lower() in f.stem.lower():
                p = f
                break
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def load_graph_nodes(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("nodes", [])


def load_raw_lines(stem: str) -> list[str]:
    p = RAW_DIR / f"{stem}.md"
    if not p.exists():
        # try fuzzy
        for f in RAW_DIR.glob("*.md"):
            if stem.lower() in f.stem.lower():
                p = f
                break
    if not p.exists():
        return []
    return p.read_text(encoding="utf-8", errors="replace").splitlines()


def nodes_for_book(nodes: list[dict], stem: str) -> list[dict]:
    """Find nodes whose source_file mentions the stem (handles raw/ prefix, spaces vs _ etc)."""
    out = []
    s_norm = stem.lower().replace(" ", "_")
    for n in nodes:
        sf = (n.get("source_file") or "").lower().replace(" ", "_")
        if not sf:
            continue
        if s_norm in sf or sf.endswith(s_norm + ".md") or sf.endswith("/" + s_norm + ".md"):
            out.append(n)
    return out


# --- matching ---

def norm(s: str) -> str:
    s = re.sub(r"[^\w\s]", " ", s.lower())
    s = re.sub(r"\s+", " ", s).strip()
    return s


def explicit_chapter_from_location(loc: str | None, chapters: list[dict]) -> dict | None:
    if not loc:
        return None
    m = re.search(r"(?:Chapter|Ch\.?)\s*(\d+[\.\d]*)", loc, re.I)
    if not m:
        return None
    num = m.group(1)
    # find chapter(s) with matching number
    cands = [c for c in chapters if str(c.get("number") or "") == str(num)]
    if not cands:
        # fallback: number appears in id
        cands = [c for c in chapters if re.search(rf"\b{re.escape(num)}\b", c.get("id", ""))]
    if cands:
        def _is_junk_title(t: str) -> bool:
            t = t.strip()
            if not t:
                return True
            # body-text like fragments that the structured parser accidentally made into chapters
            if re.match(r"^[a-z]", t):
                return True
            if t.startswith(("If ", "The figure", "The remainder", "Planetary additaments")):
                return True
            return False

        real = [c for c in cands if not _is_junk_title(c.get("title", ""))]
        pool = real or cands
        # prefer later in the document (TOC noise is early)
        pool.sort(key=lambda c: (c.get("start_line") or 0, len(c.get("title", ""))), reverse=True)
        return pool[0]
    return None


def best_title_match(text: str, chapters: list[dict]) -> tuple[dict | None, float, str | None]:
    """Return (best_chapter_or_section, score, which_kind)."""
    t = norm(text)
    best = (None, 0.0, None)
    # chapters
    for ch in chapters:
        title = ch.get("title", "")
        sc = difflib.SequenceMatcher(None, t, norm(title)).ratio()
        if sc > best[1]:
            best = (ch, sc, "chapter")
        # sections inside
        for sec in ch.get("sections") or []:
            ssc = difflib.SequenceMatcher(None, t, norm(sec.get("title", ""))).ratio()
            if ssc > best[1]:
                best = (ch, ssc, "section")  # still return chapter; caller will refine section
    return best  # type: ignore


def find_section_for_chapter(text: str, chapter: dict) -> dict | None:
    t = norm(text)
    secs = chapter.get("sections") or []
    if not secs:
        return None
    best = (None, 0.0)
    for sec in secs:
        sc = difflib.SequenceMatcher(None, t, norm(sec.get("title", ""))).ratio()
        if sc > best[1]:
            best = (sec, sc)
    return best[0] if best[1] > 0.25 else None


def build_chapter_slices(structured: dict, raw_lines: list[str]) -> dict[str, str]:
    """Map chapter_id -> joined text for that chapter's line range (best effort)."""
    slices: dict[str, str] = {}
    chapters = structured.get("chapters", [])
    nlines = len(raw_lines)
    for ch in chapters:
        start = int(ch.get("start_line") or 0)
        end = int(ch.get("end_line") or (start + 20))
        end = min(end + 1, nlines)
        txt = "\n".join(raw_lines[max(0, start):end])
        slices[ch["id"]] = txt
    return slices


PHRASE_MIN = 6  # chars

def phrase_score(phrase: str, chapter_text: str) -> float:
    p = norm(phrase)
    if len(p) < PHRASE_MIN:
        return 0.0
    if p in norm(chapter_text):
        return 0.92
    # token overlap
    ptoks = set(p.split())
    ctoks = set(norm(chapter_text).split())
    if not ptoks:
        return 0.0
    overlap = len(ptoks & ctoks) / len(ptoks)
    return min(0.88, overlap)


def phrase_lookup(node: dict, structured: dict, slices: dict[str, str]) -> tuple[str | None, float]:
    """Return (chapter_id, score) by searching node phrases in chapter slices."""
    candidates: list[tuple[str, float]] = []
    label = node.get("label") or node.get("norm_label") or ""
    rule = node.get("rule_text") or node.get("description") or ""
    phrases = [label, rule]
    # also split label on common delimiters for sub-phrases
    for sep in "—:-–—()[]:;,. ":
        if sep in label:
            phrases.extend([x.strip() for x in label.split(sep) if len(x.strip()) > 8])
    for ch_id, txt in slices.items():
        sc = 0.0
        for ph in phrases:
            sc = max(sc, phrase_score(ph, txt))
        if sc > 0.1:
            candidates.append((ch_id, sc))
    if not candidates:
        return None, 0.0
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0]


def enrich_node(node: dict, structured: dict, raw_lines: list[str]) -> dict | None:
    chapters = structured.get("chapters", [])
    if not chapters:
        return None

    label = node.get("label") or ""
    loc = node.get("source_location")
    rule = node.get("rule_text") or node.get("description") or ""

    # 1. explicit
    ch_explicit = explicit_chapter_from_location(loc, chapters)

    # 2. title
    title_text = " ".join([label, rule, loc or ""])
    ch_title, title_score, _kind = best_title_match(title_text, chapters)

    # 3. phrase
    slices = build_chapter_slices(structured, raw_lines)
    ch_phrase_id, phrase_score_val = phrase_lookup(node, structured, slices)

    # pick winner
    scored: list[tuple[float, str, dict | None]] = []
    if ch_explicit:
        scored.append((0.95, "explicit", ch_explicit))
    if ch_title and title_score > 0.35:
        scored.append((title_score, "title_match", ch_title))
    if ch_phrase_id and phrase_score_val > 0.3:
        chp = next((c for c in chapters if c["id"] == ch_phrase_id), None)
        if chp:
            scored.append((phrase_score_val, "phrase_lookup", chp))

    if not scored:
        # weak fallback: any chapter whose title words appear in label
        for ch in chapters:
            if any(w in norm(label) for w in norm(ch.get("title", "")).split() if len(w) > 4):
                scored.append((0.25, "weak_word", ch))
                break
    if not scored:
        return None

    scored.sort(key=lambda x: x[0], reverse=True)
    conf, method, ch = scored[0]
    if ch is None:
        return None

    # try to pick a section
    sec = None
    sec_id = None
    if method in ("title_match", "phrase_lookup"):
        sec = find_section_for_chapter(" ".join([label, rule]), ch)
    if sec:
        sec_id = sec["id"]

    # hierarchy path
    ch_title = ch.get("title", ch["id"])
    sec_title = sec.get("title") if sec else None
    hierarchy = f"{ch_title} > {sec_title}" if sec_title else ch_title

    patch = {
        "node_id": node.get("id"),
        "chapter_id": ch["id"],
        "section_id": sec_id,
        "hierarchy_path": hierarchy,
        "method": method,
        "confidence": round(conf, 3),
        "source_location": loc,
        "matched_on": (label[:80] or rule[:80]).strip(),
    }
    return patch


# --- main flow ---

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--books", required=True, help="Comma list of book stems (no .json)")
    ap.add_argument("--graph", default=str(DEFAULT_GRAPH), help="Path to graph.json")
    ap.add_argument("--out", default=str(DEFAULT_PATCH_OUT), help="Where to write patch JSON")
    ap.add_argument("--dry-run", action="store_true", help="Print samples; still writes patch")
    ap.add_argument("--supabase", action="store_true", help="Try to load nodes from Supabase (needs env)")
    ap.add_argument("--limit-samples", type=int, default=8, help="How many samples to print")
    args = ap.parse_args()

    book_stems = [b.strip() for b in args.books.split(",") if b.strip()]
    print(f"Mapping nodes for {len(book_stems)} book(s): {book_stems}")

    # Load structured for each
    structured_map: dict[str, dict] = {}
    for stem in book_stems:
        sb = load_structured(stem)
        if sb:
            structured_map[stem] = sb
            print(f"  ✓ structured: {stem} ({len(sb.get('chapters', []))} chapters)")
        else:
            print(f"  ✗ structured not found for {stem}")

    if not structured_map:
        print("No structured books loaded. Exiting.")
        return

    # Nodes: prefer Supabase when requested, else file. Fall back silently.
    nodes: list[dict] = []
    if args.supabase:
        nodes = fetch_nodes_via_supabase(book_stems)
        print(f"  Loaded {len(nodes)} nodes via Supabase (may be partial)")
    if not nodes:
        gpath = Path(args.graph)
        if not gpath.exists():
            print(f"Graph not found: {gpath}")
            return
        all_nodes = load_graph_nodes(gpath)
        print(f"  Loaded {len(all_nodes)} nodes from {gpath}")
        for stem in book_stems:
            matched = nodes_for_book(all_nodes, stem)
            nodes.extend(matched)
            print(f"    {stem}: {len(matched)} nodes matched by source_file")
        # dedup
        seen = set()
        uniq = []
        for n in nodes:
            if n["id"] not in seen:
                seen.add(n["id"])
                uniq.append(n)
        nodes = uniq

    if not nodes:
        print("No nodes found for the requested books.")
        return

    # Group nodes by the book stem they matched
    per_book: dict[str, list[dict]] = {s: [] for s in book_stems}
    for n in nodes:
        sf = (n.get("source_file") or "").lower().replace(" ", "_")
        for stem in book_stems:
            if stem.lower().replace(" ", "_") in sf:
                per_book[stem].append(n)
                break

    patches: list[dict] = []
    samples: list[dict] = []

    for stem, sb in structured_map.items():
        raw_lines = load_raw_lines(stem)
        book_nodes = per_book.get(stem, [])
        print(f"\n--- {stem} ({len(book_nodes)} nodes) ---")

        book_patches = []
        for n in book_nodes:
            p = enrich_node(n, sb, raw_lines)
            if p:
                p["book_id"] = sb.get("book_id", stem)
                book_patches.append(p)

        print(f"  Enriched {len(book_patches)} / {len(book_nodes)} nodes")
        patches.extend(book_patches)

        # collect a few samples for printing
        for p in book_patches[: args.limit_samples]:
            samples.append(p)

    # write patch (non-destructive)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": "graph.json" if not args.supabase else "supabase+graph",
        "books": book_stems,
        "patch_count": len(patches),
        "patches": patches,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"\nWrote patch: {out_path} ({len(patches)} entries)")

    # Print concrete samples (5-8) for the user
    print("\n=== SAMPLE ENRICHED NODE MAPPINGS (proof: KE text → source book chapters) ===")
    shown = 0
    for s in samples:
        if shown >= args.limit_samples:
            break
        print(f"\nnode: {s['node_id']}")
        print(f"  matched_on: {s['matched_on'][:110]}")
        print(f"  → chapter_id: {s['chapter_id']}")
        if s.get("section_id"):
            print(f"  → section_id: {s['section_id']}")
        print(f"  → hierarchy_path: {s['hierarchy_path']}")
        print(f"  method: {s['method']}  conf: {s['confidence']}")
        shown += 1

    if args.dry_run:
        print("\n(dry-run complete; patch written for inspection)")


if __name__ == "__main__":
    main()
