#!/usr/bin/env python3
"""
Extract graphify-compatible nodes/links from Gyan markdown corpus in knowledge-graph/raw/.

Merges into knowledge-graph/graphify-out/graph.json (incremental — skips files
already represented unless --force).

Run after: ./scripts/sync-gyan-to-raw.sh
Then:      ./scripts/sync-graph.sh [--deploy]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "knowledge-graph" / "raw"
GRAPH_PATH = ROOT / "knowledge-graph" / "graphify-out" / "graph.json"
CHUNKS = ROOT / "knowledge-graph" / "chunks"

YOGA_LINE = re.compile(
    r"^([A-Z][A-Za-z\s/–\-]+?)\s*[“\"']?([^”\"']+?)[”\"']?\s*Yoga\s*:?\s*(.*)$",
    re.MULTILINE,
)
HEADER = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)
THRESHOLD = re.compile(
    r"(?:SAV|bindu|Bindu|score|threshold)[^\n]{0,80}?(\d+)\s*[-–]\s*(\d+)|"
    r"(?:below|under|less than)\s*(\d+)|(?:above|over|≥|>=)\s*(\d+)",
    re.IGNORECASE,
)

# Wilhelm Vara/Tithi auspicious combos (muhurta_yogas.md prose)
SIDDHA_VARA_TITHI = [
    ("Venus", "Nanda"),
    ("Mercury", "Bhadra"),
    ("Mars", "Jaya"),
    ("Saturn", "Rikta"),
    ("Jupiter", "Purna"),
]
AMRITA_VARA_TITHI = [
    ("Sun", "Nanda"),
    ("Moon", "Bhadra"),
    ("Mars", "Nanda"),
    ("Mercury", "Jaya"),
    ("Jupiter", "Rikta"),
    ("Venus", "Bhadra"),
    ("Saturn", "Purna"),
]
DAGDHA_VARA_TITHI = [
    ("Sun", 12),
    ("Moon", 11),
    ("Mars", 5),
    ("Mercury", 2),
    ("Mercury", 3),
    ("Jupiter", 6),
    ("Venus", 8),
    ("Saturn", 9),
]
VISHAKHA_TITHI = [
    ("Sun", 4),
    ("Moon", 6),
    ("Mars", 7),
    ("Mercury", 2),
    ("Jupiter", 8),
    ("Venus", 9),
    ("Saturn", 7),
]

VARA_INDEX = {"Sun": 0, "Moon": 1, "Mars": 2, "Mercury": 3, "Jupiter": 4, "Venus": 5, "Saturn": 6}


def slug(s: str, max_len: int = 48) -> str:
    s = re.sub(r"[^\w\s-]", "", s.lower())
    s = re.sub(r"[\s_]+", "_", s).strip("_")
    return s[:max_len] or "item"


def file_prefix(name: str) -> str:
    return slug(Path(name).stem)[:40]


def node(
    nid: str,
    label: str,
    source_file: str,
    community: int,
    **extra,
) -> dict:
    n = {
        "id": nid,
        "label": label,
        "file_type": "document",
        "source_file": source_file,
        "community": community,
        "description": extra.pop("description", label[:240]),
    }
    n.update(extra)
    return n


def link(src: str, tgt: str, relation: str, source_file: str, conf: str = "EXTRACTED") -> dict:
    return {
        "source": src,
        "target": tgt,
        "relation": relation,
        "confidence": conf,
        "confidence_score": 1.0 if conf == "EXTRACTED" else 0.7,
        "source_file": source_file,
    }


def community_for(filename: str, base: int = 40) -> int:
    h = int(hashlib.md5(filename.encode()).hexdigest()[:8], 16)
    return base + (h % 200)


def extract_generic(path: Path, source_file: str, comm: int) -> tuple[list, list, list]:
    text = path.read_text(encoding="utf-8", errors="replace")
    prefix = file_prefix(path.name)
    nodes: list[dict] = []
    links: list[dict] = []
    hyperedges: list[dict] = []

    root_id = f"gyan_{prefix}_corpus"
    nodes.append(node(root_id, path.stem.replace("_", " "), source_file, comm, is_god_node=True))

    # Section headers
    for m in HEADER.finditer(text):
        level, title = m.group(1), m.group(2).strip()
        if len(title) < 3:
            continue
        sid = f"gyan_{prefix}_sec_{slug(title)}"
        if any(n["id"] == sid for n in nodes):
            continue
        nodes.append(node(sid, title, source_file, comm, source_location=f"h{len(level)}"))
        links.append(link(root_id, sid, "contains_section", source_file))

    # Named yogas in prose
    for m in YOGA_LINE.finditer(text):
        yoga_name = m.group(2).strip() or m.group(1).strip()
        if len(yoga_name) < 3 or len(yoga_name) > 80:
            continue
        yid = f"gyan_{prefix}_yoga_{slug(yoga_name)}"
        if any(n["id"] == yid for n in nodes):
            continue
        desc = m.group(3).strip()[:500] if m.group(3) else yoga_name
        nature = (
            "auspicious"
            if re.search(r"auspici|benefic|good|siddha|amrita|subha", desc, re.I)
            else (
                "inauspicious"
                if re.search(r"inauspici|malefic|bad|dagdha|visha|krakacha|mrityu", desc, re.I)
                else "mixed"
            )
        )
        nodes.append(
            node(yid, f"{yoga_name} Yoga", source_file, comm, nature=nature, definition=desc)
        )
        links.append(link(root_id, yid, "defines_yoga", source_file))

    # SAV / bindu thresholds
    for m in THRESHOLD.finditer(text):
        if m.group(1) and m.group(2):
            lo, hi = int(m.group(1)), int(m.group(2))
            tid = f"gyan_{prefix}_sav_band_{lo}_{hi}"
            if not any(n["id"] == tid for n in nodes):
                nodes.append(
                    node(
                        tid, f"SAV band {lo}–{hi}", source_file, comm, min_bindus=lo, max_bindus=hi
                    )
                )
                links.append(link(root_id, tid, "defines_sav_band", source_file))

    # Key concept lines (CRITICAL, MUST, rule bullets)
    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) < 20:
            continue
        if re.match(r"^(CRITICAL|IMPORTANT|MUST|NOTE|Rule)\b", line, re.I):
            cid = f"gyan_{prefix}_rule_{slug(line[:60])}"
            if any(n["id"] == cid for n in nodes):
                continue
            nodes.append(node(cid, line[:120], source_file, comm, rule_text=line[:400]))
            links.append(link(root_id, cid, "states_rule", source_file))

    return nodes, links, hyperedges


def extract_muhurta_yogas(path: Path, source_file: str, comm: int) -> tuple[list, list, list]:
    nodes, links, _ = extract_generic(path, source_file, comm)
    prefix = file_prefix(path.name)

    def add_combo_yoga(name: str, nature: str, combos: list, combo_type: str):
        yid = f"gyan_muhurta_yoga_{slug(name)}"
        if any(n["id"] == yid for n in nodes):
            return
        nodes.append(
            node(
                yid,
                f"{name} Yoga",
                source_file,
                comm,
                nature=nature,
                combo_type=combo_type,
                is_muhurta_yoga=True,
            )
        )
        for item in combos:
            if combo_type == "vara_tithi_group":
                vara_lord, tithi_group = item
                cid = f"gyan_muhurta_{slug(name)}_{vara_lord}_{tithi_group}".lower()
                nodes.append(
                    node(
                        cid,
                        f"{name}: {tithi_group} tithi on {vara_lord}'s weekday",
                        source_file,
                        comm,
                        vara_lord=vara_lord,
                        tithi_group=tithi_group,
                        verdict=nature,
                    )
                )
                links.append(link(yid, cid, "requires", source_file))
            else:
                vara_lord, tithi_num = item
                cid = f"gyan_muhurta_{slug(name)}_{vara_lord}_t{tithi_num}".lower()
                nodes.append(
                    node(
                        cid,
                        f"{name}: tithi {tithi_num} on {vara_lord}'s weekday",
                        source_file,
                        comm,
                        vara_lord=vara_lord,
                        tithi_num=tithi_num,
                        verdict=nature,
                    )
                )
                links.append(link(yid, cid, "requires", source_file))

    add_combo_yoga("Siddha", "auspicious", SIDDHA_VARA_TITHI, "vara_tithi_group")
    add_combo_yoga("Amrita", "auspicious", AMRITA_VARA_TITHI, "vara_tithi_group")
    add_combo_yoga("Dagdha", "inauspicious", DAGDHA_VARA_TITHI, "vara_tithi_num")
    add_combo_yoga("Visha", "inauspicious", VISHAKHA_TITHI, "vara_tithi_num")

    return nodes, links, []


def extract_ashtakavarga(path: Path, source_file: str, comm: int) -> tuple[list, list, list]:
    nodes, links, hyper = extract_generic(path, source_file, comm)
    prefix = file_prefix(path.name)

    bands = [
        (30, 999, "excellent", "shubh"),
        (28, 29, "good", "shubh"),
        (25, 27, "standard", "neutral"),
        (0, 24, "depleted", "ashubh"),
    ]
    for lo, hi, band, verdict in bands:
        bid = f"gyan_ashtakavarga_sav_{band}"
        if any(n["id"] == bid for n in nodes):
            continue
        nodes.append(
            node(
                bid,
                f"SAV {band} ({lo}+)" if hi > 100 else f"SAV {band} ({lo}–{hi})",
                source_file,
                comm,
                min_bindus=lo,
                max_bindus=hi,
                verdict=verdict,
                domain="ashtakavarga",
            )
        )
        links.append(link(f"gyan_{prefix}_corpus", bid, "defines_sav_band", source_file))

    totals = {
        "Sun": 48,
        "Moon": 49,
        "Mars": 39,
        "Mercury": 54,
        "Jupiter": 56,
        "Venus": 52,
        "Saturn": 39,
    }
    for planet, total in totals.items():
        pid = f"gyan_ashtakavarga_bav_total_{planet.lower()}"
        if any(n["id"] == pid for n in nodes):
            continue
        nodes.append(
            node(
                pid,
                f"{planet} BAV total {total} bindus",
                source_file,
                comm,
                planet=planet,
                bav_total=total,
            )
        )
        links.append(link(f"gyan_{prefix}_corpus", pid, "documents", source_file))

    return nodes, links, hyper


def load_chunk_fragments() -> tuple[list, list, list]:
    """Merge pre-built high-quality chunk extractions (Jaimini, Yogini)."""
    nodes, links, hyper = [], [], []
    for chunk in sorted(CHUNKS.glob(".graphify_chunk_*.json")):
        data = json.loads(chunk.read_text(encoding="utf-8"))
        nodes.extend(data.get("nodes", []))
        edges = data.get("edges") or data.get("links") or []
        links.extend(edges)
        hyper.extend(data.get("hyperedges", []))
    return nodes, links, hyper


def sources_in_graph(graph: dict) -> set[str]:
    out: set[str] = set()
    for n in graph.get("nodes", []):
        sf = n.get("source_file") or ""
        if sf:
            out.add(Path(sf).name)
    return out


def merge_graph(base: dict, new_nodes: list, new_links: list, new_hyper: list) -> dict:
    g = json.loads(json.dumps(base))  # deep copy
    existing_ids = {n["id"] for n in g.get("nodes", [])}
    for n in new_nodes:
        if n["id"] not in existing_ids:
            g.setdefault("nodes", []).append(n)
            existing_ids.add(n["id"])
    existing_links = {
        (l.get("source"), l.get("target"), l.get("relation")) for l in g.get("links", [])
    }
    for l in new_links:
        key = (l.get("source"), l.get("target"), l.get("relation"))
        if key not in existing_links:
            g.setdefault("links", []).append(l)
            existing_links.add(key)
    existing_he = {h.get("id") for h in g.get("hyperedges", [])}
    for h in new_hyper:
        if h.get("id") not in existing_he:
            g.setdefault("hyperedges", []).append(h)
    return g


def extract_file(path: Path, force: bool) -> tuple[list, list, list]:
    source_file = f"raw/{path.name}"
    comm = community_for(path.name)
    if path.name == "muhurta_yogas.md":
        return extract_muhurta_yogas(path, source_file, comm)
    if path.name == "Ashtakavarga_System_Comprehensive_Handbook.md":
        return extract_ashtakavarga(path, source_file, comm)
    return extract_generic(path, source_file, comm)


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract Gyan corpus into graph.json")
    ap.add_argument("--force", action="store_true", help="Re-extract files already in graph")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not RAW.is_dir():
        print(f"error: {RAW} missing — run ./scripts/sync-gyan-to-raw.sh first", file=sys.stderr)
        return 1
    if not GRAPH_PATH.is_file():
        print(f"error: {GRAPH_PATH} missing — run graphify on raw/ first", file=sys.stderr)
        return 1

    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    present = sources_in_graph(graph)

    all_nodes: list[dict] = []
    all_links: list[dict] = []
    all_hyper: list[dict] = []

    # Pre-built chunks for texts already hand-extracted
    cn, cl, ch = load_chunk_fragments()
    all_nodes.extend(cn)
    all_links.extend(cl)
    all_hyper.extend(ch)
    print(f"chunks: +{len(cn)} nodes from knowledge-graph/chunks/")

    processed = 0
    for path in sorted(RAW.glob("*.md")):
        if not args.force and path.name in present:
            print(f"  skip (in graph): {path.name}")
            continue
        n, l, h = extract_file(path, args.force)
        all_nodes.extend(n)
        all_links.extend(l)
        all_hyper.extend(h)
        print(f"  extract: {path.name} → {len(n)} nodes, {len(l)} links")
        processed += 1

    merged = merge_graph(graph, all_nodes, all_links, all_hyper)
    print(
        f"\ngraph: {len(graph['nodes'])}→{len(merged['nodes'])} nodes, "
        f"{len(graph['links'])}→{len(merged['links'])} links "
        f"({processed} files processed)"
    )

    if args.dry_run:
        return 0

    GRAPH_PATH.write_text(json.dumps(merged, indent=2), encoding="utf-8")

    # Update manifest hashes for graphify --update compatibility
    manifest_path = GRAPH_PATH.parent / "manifest.json"
    manifest: dict = {}
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for path in RAW.glob("*.md"):
        key = str(path.resolve())
        data = path.read_bytes()
        h = hashlib.md5(data).hexdigest()
        manifest[key] = {"mtime": path.stat().st_mtime, "ast_hash": h, "semantic_hash": h}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"✓ wrote {GRAPH_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
