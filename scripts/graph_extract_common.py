"""Shared helpers for multi-provider graph extraction pipelines."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KG = ROOT / "knowledge-graph"
RAW = KG / "raw"
MANIFEST = KG / "corpus-manifest.json"
GRAPH_BASE = KG / "graphify-out" / "graph.json"
GRAPH_VERSION_PATH = KG / "graph-version.json"
FILE_CHAR_CAP = 20_000


def load_graph_version() -> dict:
    if GRAPH_VERSION_PATH.is_file():
        return json.loads(GRAPH_VERSION_PATH.read_text(encoding="utf-8"))
    return {}


def production_node_floor() -> int:
    ver = load_graph_version()
    if ver.get("production_nodes"):
        return int(ver["production_nodes"])
    if GRAPH_BASE.is_file():
        return len(json.loads(GRAPH_BASE.read_text(encoding="utf-8")).get("nodes", []))
    return 23267


# Merge guard: never shrink below current production graph (see graph-version.json).
BASELINE_NODES = production_node_floor()

GRAPHIFY_SITE = Path(os.environ.get("GRAPHIFY_SITE", ""))
if not GRAPHIFY_SITE.is_dir():
    GRAPHIFY_SITE = Path(
        "/Users/ganesha/Projects/04-UX-Practice/Panchang/.venv/lib/python3.14/site-packages"
    )
if GRAPHIFY_SITE.is_dir() and str(GRAPHIFY_SITE) not in sys.path:
    sys.path.insert(0, str(GRAPHIFY_SITE))


def load_env_local() -> dict[str, str]:
    out: dict[str, str] = {}
    p = ROOT / "portal" / ".env.local"
    if not p.is_file():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def env_key(*names: str) -> str | None:
    for k in names:
        v = os.environ.get(k, "").strip().strip('"').strip("'")
        if v:
            return v
    local = load_env_local()
    for k in names:
        v = local.get(k, "").strip()
        if v:
            return v
    return None


def merge_graph(base: dict, fragment: dict) -> dict:
    g = json.loads(json.dumps(base))
    existing_ids = {n["id"] for n in g.get("nodes", []) if n.get("id")}
    for n in fragment.get("nodes", []):
        if n.get("id") and n["id"] not in existing_ids:
            g.setdefault("nodes", []).append(n)
            existing_ids.add(n["id"])
    existing_links = {
        (l.get("source"), l.get("target"), l.get("relation")) for l in g.get("links", [])
    }
    for e in fragment.get("edges") or fragment.get("links") or []:
        key = (e.get("source"), e.get("target"), e.get("relation"))
        if key not in existing_links and e.get("source") and e.get("target"):
            g.setdefault("links", []).append(dict(e))
            existing_links.add(key)
    existing_he = {h.get("id") for h in g.get("hyperedges", []) if h.get("id")}
    for h in fragment.get("hyperedges", []):
        if h.get("id") and h["id"] not in existing_he:
            g.setdefault("hyperedges", []).append(h)
    return g


def corpus_paths(*, only_md: list[str] | None = None) -> list[Path]:
    paths: list[Path] = []
    for sub in ("raw", "digests"):
        d = KG / sub
        if d.is_dir():
            paths.extend(sorted(d.glob("*.md")))
    if only_md:
        allow = {n if n.endswith(".md") else f"{n}.md" for n in only_md}
        paths = [p for p in paths if p.name in allow]
    return paths


def units_for_file(path: Path) -> list:
    from graphify.file_slice import expand_oversized_files

    return expand_oversized_files([path], FILE_CHAR_CAP)


def unit_key(unit, root: Path) -> str:
    from graphify.file_slice import FileSlice, unit_path

    p = unit_path(unit)
    try:
        rel = p.relative_to(root)
    except ValueError:
        rel = p
    key = str(rel).replace("\\", "/")
    if isinstance(unit, FileSlice):
        key = f"{key}#slice{unit.index}"
    return key


def build_user_message(unit, root: Path) -> str:
    from graphify.llm import _read_files

    return _read_files([unit], root)


def build_extraction_jobs(
    *,
    only_md: list[str] | None = None,
    deep: bool = True,
) -> list[dict]:
    from graphify.llm import _extraction_system

    system = _extraction_system(deep=deep)
    jobs: list[dict] = []
    root = KG.resolve()
    for path in corpus_paths(only_md=only_md):
        for unit in units_for_file(path):
            key = unit_key(unit, root)
            jobs.append(
                {
                    "key": key,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": build_user_message(unit, root)},
                    ],
                }
            )
    return jobs


def parse_fragment(text: str) -> dict:
    from graphify.llm import _parse_llm_json

    return _parse_llm_json(text)


def cache_path(cache_dir: Path, key: str) -> Path:
    h = hashlib.sha256(key.encode()).hexdigest()
    return cache_dir / f"{h}.json"


def merge_caches_into(base: dict, cache_dir: Path) -> tuple[dict, int]:
    merged = base
    applied = 0
    if not cache_dir.is_dir():
        return merged, 0
    for path in sorted(cache_dir.glob("*.json")):
        try:
            frag = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        before = len(merged.get("nodes", []))
        merged = merge_graph(merged, frag)
        if len(merged.get("nodes", [])) > before:
            applied += 1
    return merged, applied


def update_manifest(raw_dir: Path = RAW) -> dict:
    files: dict = {}
    for p in sorted(raw_dir.glob("*.md")):
        data = p.read_bytes()
        files[p.name] = {
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()[:16],
            "path": f"raw/{p.name}",
        }
    doc = {"sources": files, "count": len(files)}
    MANIFEST.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return doc


def slugify_title(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9\s_\-]", "", name)
    s = re.sub(r"[\s_\-]+", "_", s).strip("_")
    return s[:80] or "untitled"
