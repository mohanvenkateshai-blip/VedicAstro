"""Session memory bridge — CONTEXT.md → queryable graph nodes + semantic search.

Reads the panchanga_muhurtha agent memory file (docs/CONTEXT.md) and converts
its structured sections (function map, tables, gotchas, conventions, rules)
into graph-shaped nodes with links. Exposes:

  build_session_graph()       → {nodes, links}
  query_session_memory(q, k)  → top-k functions / gotchas / patterns
  merge_into_graph_rag()      → optional overlay onto GraphRAG search space

Uses the local BGE embedder for semantic search (with hash fallback).
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_CONTEXT_PATH = Path(
    os.environ.get(
        "SESSION_CONTEXT_PATH",
        str(
            Path(__file__).resolve().parents[3]  # up from cvce/knowledge_engine → VedicAstro
            / ".."
            / "Panchang"
            / "panchanga_muhurtha"
            / "docs"
            / "CONTEXT.md"
        ),
    )
).resolve()

# Also try the absolute path the task specified
_TASK_CONTEXT = Path(
    "/Users/ganesha/Projects/04-UX-Practice/Panchang/panchanga_muhurtha/docs/CONTEXT.md"
)
if _TASK_CONTEXT.exists():
    DEFAULT_CONTEXT_PATH = _TASK_CONTEXT


# ── Parsing ────────────────────────────────────────────────────────────────

_H2 = re.compile(r"^##\s+(.+?)\s*$")
_H3 = re.compile(r"^###\s+(.+?)\s*$")
_FUNC = re.compile(
    r"^###\s+`?([A-Za-z_][A-Za-z0-9_]*)\(\)`?(?:\s*→\s*L?(\d+))?",
)
_BULLET = re.compile(r"^[-*]\s+\*?\*?(.+?)\*?\*?(?:\s*[—:-]\s*(.+))?$")
_NUMBERED = re.compile(r"^\d+\.\s+\*?\*?(.+?)(?:\*?\*?)?(?:\s*[—:-]\s*(.+))?$")
_TABLE_ROW = re.compile(r"^\|(.+)\|$")
_CODE_LINE = re.compile(r"^`([^`]+)`\s*[—:-]\s*(.+)$")


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", (text or "").strip().lower()).strip("_")
    return s[:80] or "item"


def _split_sections(md: str) -> list[tuple[str, str]]:
    """Split markdown into (h2_title, body) pairs; preamble is ('__preamble__', ...)."""
    lines = md.splitlines()
    sections: list[tuple[str, str]] = []
    current_title = "__preamble__"
    buf: list[str] = []
    for line in lines:
        m = _H2.match(line)
        if m:
            sections.append((current_title, "\n".join(buf).strip()))
            current_title = m.group(1).strip()
            buf = []
        else:
            buf.append(line)
    sections.append((current_title, "\n".join(buf).strip()))
    return sections


def _parse_functions(body: str, section: str) -> list[dict[str, Any]]:
    """Extract ### name() → Lnnn blocks with following description."""
    items: list[dict[str, Any]] = []
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        m = _FUNC.match(lines[i])
        if not m:
            # Also accept ### Name without ()
            h3 = _H3.match(lines[i])
            if h3 and "(" not in h3.group(1):
                i += 1
                continue
            i += 1
            continue
        name = m.group(1)
        line_no = m.group(2)
        desc_lines: list[str] = []
        i += 1
        while i < len(lines) and not lines[i].startswith("#") and not _FUNC.match(lines[i]):
            if lines[i].strip():
                desc_lines.append(lines[i].strip())
            i += 1
            if len(desc_lines) >= 6:
                # keep reading until blank or next header
                if i < len(lines) and not lines[i].strip():
                    break
        desc = " ".join(desc_lines).strip()
        items.append(
            {
                "kind": "function",
                "name": name,
                "line": int(line_no) if line_no else None,
                "description": desc,
                "section": section,
            }
        )
    return items


def _parse_bullets(body: str, section: str, kind: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        m = _NUMBERED.match(line) or _BULLET.match(line)
        if not m:
            continue
        title = (m.group(1) or "").strip().strip("*").strip()
        rest = (m.group(2) or "").strip() if m.lastindex and m.lastindex >= 2 else ""
        # For "**key** — value" patterns already in group1
        if " — " in title and not rest:
            title, rest = title.split(" — ", 1)
        if " - " in title and not rest:
            title, rest = title.split(" - ", 1)
        title = title.strip().strip("*").strip("`")
        if len(title) < 2:
            continue
        items.append(
            {
                "kind": kind,
                "name": title[:200],
                "description": rest or title,
                "section": section,
            }
        )
    return items


def _parse_table(body: str, section: str, kind: str = "table_row") -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    rows = []
    for line in body.splitlines():
        m = _TABLE_ROW.match(line.strip())
        if not m:
            continue
        cells = [c.strip() for c in m.group(1).split("|")]
        if all(re.match(r"^:?-+:?$", c or "") for c in cells):
            continue  # separator
        rows.append(cells)
    if len(rows) < 2:
        return items
    headers = [h.lower() for h in rows[0]]
    for row in rows[1:]:
        while len(row) < len(headers):
            row.append("")
        data = {headers[i]: row[i] for i in range(len(headers))}
        # Prefer name / path / key columns
        name = (
            data.get("name")
            or data.get("path")
            or data.get("function")
            or data.get("key")
            or (row[0] if row else "row")
        )
        name = str(name).strip("`").strip()
        desc_parts = [f"{k}: {v}" for k, v in data.items() if v and k != "name"]
        items.append(
            {
                "kind": kind,
                "name": name[:200],
                "description": " | ".join(desc_parts)[:500],
                "section": section,
                "fields": data,
            }
        )
    return items


def parse_context_md(text: str) -> list[dict[str, Any]]:
    """Parse CONTEXT.md into a flat list of memory items."""
    sections = _split_sections(text)
    items: list[dict[str, Any]] = []

    for title, body in sections:
        t_up = title.upper()
        if "CORE ENGINE" in t_up or "FUNCTION" in t_up:
            items.extend(_parse_functions(body, title))
            # also tables in that section
            items.extend(_parse_table(body, title, kind="function_table"))
        elif "LOOKUP TABLE" in t_up or "KEY LOOKUP" in t_up:
            items.extend(_parse_table(body, title, kind="table"))
        elif "GOTCHA" in t_up:
            items.extend(_parse_bullets(body, title, kind="gotcha"))
        elif "RULE" in t_up:
            items.extend(_parse_bullets(body, title, kind="rule"))
        elif "CONVENTION" in t_up:
            items.extend(_parse_bullets(body, title, kind="convention"))
        elif "FILE MAP" in t_up:
            items.extend(_parse_table(body, title, kind="file"))
        elif "QUICK-START" in t_up:
            # parse key: value lines inside code fences and bullets
            for line in body.splitlines():
                line = line.strip().strip("`")
                if ":" in line and not line.startswith("#"):
                    key, _, val = line.partition(":")
                    key, val = key.strip(), val.strip()
                    if key and val and len(key) < 40:
                        items.append(
                            {
                                "kind": "pattern",
                                "name": key,
                                "description": val,
                                "section": title,
                            }
                        )
        elif "ASTRONOMY" in t_up or "BUILD PIPELINE" in t_up:
            items.append(
                {
                    "kind": "pattern",
                    "name": title,
                    "description": body[:800],
                    "section": title,
                }
            )
        elif "CURRENT STATE" in t_up or "MEMORY UPDATE" in t_up:
            items.append(
                {
                    "kind": "pattern",
                    "name": title,
                    "description": body[:800],
                    "section": title,
                }
            )
            items.extend(_parse_bullets(body, title, kind="pattern"))
        else:
            # generic: capture h3 + bullets
            items.extend(_parse_functions(body, title))
            items.extend(_parse_bullets(body, title, kind="pattern"))

    # Dedup by kind+name
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for it in items:
        key = f"{it.get('kind')}:{str(it.get('name') or '').lower()}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(it)
    return unique


# ── Graph conversion ───────────────────────────────────────────────────────

def items_to_graph(items: list[dict[str, Any]]) -> dict[str, list[dict]]:
    """Convert memory items to graphify-shaped {nodes, links}."""
    nodes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []

    # Root
    root_id = "session_memory_root"
    nodes.append(
        {
            "id": root_id,
            "label": "panchanga_muhurtha session memory (CONTEXT.md)",
            "file_type": "document",
            "source_file": "docs/CONTEXT.md",
            "community": "session_memory",
            "norm_label": "session memory root",
        }
    )

    section_ids: dict[str, str] = {}
    kind_ids: dict[str, str] = {}

    for kind in sorted({it["kind"] for it in items}):
        kid = f"session_kind_{_slug(kind)}"
        kind_ids[kind] = kid
        nodes.append(
            {
                "id": kid,
                "label": f"Session memory kind: {kind}",
                "file_type": "concept",
                "source_file": "docs/CONTEXT.md",
                "community": "session_memory",
                "norm_label": kind,
            }
        )
        links.append(
            {
                "source": root_id,
                "target": kid,
                "relation": "contains_section",
                "confidence": "EXTRACTED",
                "confidence_score": 1.0,
                "source_file": "docs/CONTEXT.md",
                "weight": 1.0,
            }
        )

    for it in items:
        section = it.get("section") or "unknown"
        if section not in section_ids:
            sid = f"session_section_{_slug(section)}"
            section_ids[section] = sid
            nodes.append(
                {
                    "id": sid,
                    "label": f"CONTEXT section: {section}",
                    "file_type": "document",
                    "source_file": "docs/CONTEXT.md",
                    "community": "session_memory",
                    "norm_label": section.lower(),
                }
            )
            links.append(
                {
                    "source": root_id,
                    "target": sid,
                    "relation": "contains_section",
                    "confidence": "EXTRACTED",
                    "confidence_score": 1.0,
                    "source_file": "docs/CONTEXT.md",
                    "weight": 1.0,
                }
            )

        nid = f"session_{it['kind']}_{_slug(str(it.get('name')))}"
        label = str(it.get("name") or nid)
        if it.get("kind") == "function" and it.get("line"):
            label = f"{label}() → L{it['line']}"
        desc = str(it.get("description") or "")
        node = {
            "id": nid,
            "label": label,
            "description": desc,
            "file_type": "code" if it["kind"] == "function" else "concept",
            "source_file": "docs/CONTEXT.md",
            "source_location": section,
            "community": "session_memory",
            "norm_label": label.lower(),
            "memory_kind": it["kind"],
            "memory_name": it.get("name"),
            "line": it.get("line"),
        }
        nodes.append(node)

        # link to section + kind
        links.append(
            {
                "source": section_ids[section],
                "target": nid,
                "relation": "defines",
                "confidence": "EXTRACTED",
                "confidence_score": 1.0,
                "source_file": "docs/CONTEXT.md",
                "weight": 1.0,
            }
        )
        links.append(
            {
                "source": kind_ids[it["kind"]],
                "target": nid,
                "relation": "member_of",
                "confidence": "EXTRACTED",
                "confidence_score": 1.0,
                "source_file": "docs/CONTEXT.md",
                "weight": 1.0,
            }
        )

    # Cross-link functions mentioned inside descriptions
    name_to_id = {
        str(it.get("name")).lower(): f"session_{it['kind']}_{_slug(str(it.get('name')))}"
        for it in items
        if it.get("name")
    }
    for it in items:
        desc = str(it.get("description") or "")
        src = f"session_{it['kind']}_{_slug(str(it.get('name')))}"
        for other_name, other_id in name_to_id.items():
            if other_id == src:
                continue
            if len(other_name) >= 4 and re.search(
                rf"\b{re.escape(other_name)}\b", desc, re.I
            ):
                links.append(
                    {
                        "source": src,
                        "target": other_id,
                        "relation": "references",
                        "confidence": "INFERRED",
                        "confidence_score": 0.7,
                        "source_file": "docs/CONTEXT.md",
                        "weight": 0.7,
                    }
                )

    return {"nodes": nodes, "links": links}


def build_session_graph(context_path: Path | str | None = None) -> dict[str, Any]:
    """Read CONTEXT.md and return {nodes, links, items, meta}."""
    path = Path(context_path) if context_path else DEFAULT_CONTEXT_PATH
    if not path.exists():
        return {
            "nodes": [],
            "links": [],
            "items": [],
            "meta": {"error": f"CONTEXT.md not found: {path}"},
        }
    text = path.read_text(encoding="utf-8")
    items = parse_context_md(text)
    graph = items_to_graph(items)
    graph["items"] = items
    graph["meta"] = {
        "source": str(path),
        "item_count": len(items),
        "node_count": len(graph["nodes"]),
        "link_count": len(graph["links"]),
        "kinds": sorted({it["kind"] for it in items}),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return graph


# ── Semantic index ─────────────────────────────────────────────────────────

class SessionMemoryIndex:
    """In-memory embedding index over session memory items."""

    def __init__(self):
        self.items: list[dict[str, Any]] = []
        self.matrix: np.ndarray | None = None
        self._loaded_from: str | None = None

    def build(self, items: list[dict[str, Any]]) -> "SessionMemoryIndex":
        self.items = list(items)
        texts = [
            f"{it.get('kind')}: {it.get('name')} — {it.get('description') or ''}"
            for it in self.items
        ]
        self.matrix = _embed(texts)
        return self

    def query(self, q: str, top_k: int = 8) -> list[dict[str, Any]]:
        if not self.items or self.matrix is None or self.matrix.shape[0] == 0:
            return []
        qv = _embed([q])
        if qv.shape[0] == 0:
            return []
        a = qv / (np.linalg.norm(qv, axis=1, keepdims=True) + 1e-12)
        b = self.matrix / (np.linalg.norm(self.matrix, axis=1, keepdims=True) + 1e-12)
        sims = (a @ b.T)[0]
        # Hybrid: cosine + lexical boost for exact token hits in name/description.
        # Functions/tables get a small prior so CORE ENGINES beat vague patterns.
        q_tokens = set(re.findall(r"[a-z0-9]+", (q or "").lower()))
        kind_prior = {
            "function": 0.08,
            "table": 0.05,
            "function_table": 0.05,
            "gotcha": 0.04,
            "rule": 0.03,
            "convention": 0.02,
            "pattern": 0.0,
            "file": 0.01,
        }
        scores = np.array(sims, dtype=np.float64)
        for j, it in enumerate(self.items):
            blob = f"{it.get('name') or ''} {it.get('description') or ''}".lower()
            tokens = set(re.findall(r"[a-z0-9]+", blob))
            if q_tokens:
                overlap = len(q_tokens & tokens) / max(len(q_tokens), 1)
                scores[j] += 0.15 * overlap
                # Strong boost when multi-word query phrase appears verbatim
                if len(q) >= 4 and q.lower() in blob:
                    scores[j] += 0.12
            scores[j] += kind_prior.get(str(it.get("kind")), 0.0)
        order = np.argsort(-scores)[: max(1, top_k)]
        out: list[dict[str, Any]] = []
        for j in order:
            it = dict(self.items[int(j)])
            it["score"] = round(float(scores[int(j)]), 6)
            out.append(it)
        return out


_INDEX: SessionMemoryIndex | None = None
_GRAPH_CACHE: dict[str, Any] | None = None


def _hash_embed(text: str, dim: int = 384) -> list[float]:
    vec = np.zeros(dim, dtype=np.float64)
    tokens = re.findall(r"[a-zA-Z0-9_]+", (text or "").lower()) or ["empty"]
    for tok in tokens:
        h = hashlib.sha256(tok.encode("utf-8")).digest()
        for i in range(0, 32, 4):
            idx = int.from_bytes(h[i : i + 4], "little") % dim
            sign = 1.0 if (h[i] & 1) == 0 else -1.0
            vec[idx] += sign
    n = np.linalg.norm(vec)
    if n > 0:
        vec /= n
    return [float(x) for x in vec]


def _embed(texts: list[str]) -> np.ndarray:
    try:
        from vedic_knowledge.knowledge.local_embedder import LOCAL_EMBED_DIM, embed_documents

        cleaned = [t if (t or "").strip() else " " for t in texts]
        vecs = embed_documents(cleaned)
        return np.asarray(vecs, dtype=np.float32)
    except Exception as exc:
        logger.warning("session_memory embed fallback: %s", exc)
        try:
            from vedic_knowledge.knowledge.local_embedder import LOCAL_EMBED_DIM
            dim = LOCAL_EMBED_DIM
        except Exception:
            dim = 384
        return np.asarray([_hash_embed(t, dim) for t in texts], dtype=np.float32)


def ensure_index(context_path: Path | str | None = None, *, force: bool = False) -> SessionMemoryIndex:
    global _INDEX, _GRAPH_CACHE
    path = str(Path(context_path) if context_path else DEFAULT_CONTEXT_PATH)
    if _INDEX is not None and _INDEX._loaded_from == path and not force:
        return _INDEX
    graph = build_session_graph(path)
    _GRAPH_CACHE = graph
    idx = SessionMemoryIndex().build(graph.get("items") or [])
    idx._loaded_from = path
    _INDEX = idx
    return idx


def get_session_graph(context_path: Path | str | None = None) -> dict[str, Any]:
    global _GRAPH_CACHE
    ensure_index(context_path)
    return _GRAPH_CACHE or build_session_graph(context_path)


def query_session_memory(
    query: str,
    top_k: int = 8,
    *,
    context_path: Path | str | None = None,
    kinds: list[str] | None = None,
) -> dict[str, Any]:
    """
    Semantic search over session memory.

    Returns top-k relevant function names, gotchas, and patterns from past
    sessions (CONTEXT.md), with scores.
    """
    q = (query or "").strip()
    if not q:
        return {"query": q, "results": [], "functions": [], "gotchas": [], "patterns": []}

    idx = ensure_index(context_path)
    # Over-fetch then filter by kind if requested
    raw = idx.query(q, top_k=max(top_k * 3, top_k))
    if kinds:
        kind_set = set(kinds)
        raw = [r for r in raw if r.get("kind") in kind_set]
    raw = raw[:top_k]

    functions = [r for r in raw if r.get("kind") in ("function", "function_table", "table")]
    gotchas = [r for r in raw if r.get("kind") == "gotcha"]
    patterns = [
        r
        for r in raw
        if r.get("kind") in ("pattern", "convention", "rule", "file")
    ]

    # If category lists are thin, backfill from a broader query slice
    if len(functions) < min(3, top_k):
        more = idx.query(q, top_k=top_k * 4)
        for r in more:
            if r.get("kind") in ("function", "function_table", "table") and r not in functions:
                functions.append(r)
            if len(functions) >= top_k:
                break

    return {
        "query": q,
        "results": raw,
        "functions": [
            {
                "name": r.get("name"),
                "line": r.get("line"),
                "description": r.get("description"),
                "score": r.get("score"),
                "section": r.get("section"),
            }
            for r in functions[:top_k]
        ],
        "gotchas": [
            {
                "name": r.get("name"),
                "description": r.get("description"),
                "score": r.get("score"),
            }
            for r in gotchas[:top_k]
        ],
        "patterns": [
            {
                "name": r.get("name"),
                "kind": r.get("kind"),
                "description": r.get("description"),
                "score": r.get("score"),
            }
            for r in patterns[:top_k]
        ],
        "meta": {
            "index_size": len(idx.items),
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    }


def hybrid_memory_query(
    query: str,
    top_k: int = 8,
    *,
    include_graph: bool = True,
) -> dict[str, Any]:
    """Search session memory and (optionally) the GraphRAG keyword index."""
    session = query_session_memory(query, top_k=top_k)
    graph_hits: list[dict[str, Any]] = []
    if include_graph:
        try:
            from vedic_knowledge.graph.graph import GraphRAG

            g = GraphRAG()
            graph_hits = g.search(query, top_n=top_k)
        except Exception as exc:
            logger.debug("GraphRAG search unavailable: %s", exc)
            # Fallback: direct keyword over session graph labels
            sg = get_session_graph()
            q_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
            scored = []
            for n in sg.get("nodes") or []:
                lab = str(n.get("label") or "").lower()
                tokens = set(re.findall(r"[a-z0-9]+", lab))
                overlap = len(q_tokens & tokens)
                if overlap:
                    scored.append((overlap, n))
            scored.sort(key=lambda x: -x[0])
            graph_hits = [
                {
                    "id": n.get("id"),
                    "label": n.get("label"),
                    "score": float(s),
                    "community": n.get("community"),
                    "source_file": n.get("source_file"),
                }
                for s, n in scored[:top_k]
            ]

    return {
        "query": query,
        "session_memory": session,
        "graph_hits": graph_hits,
        "top_functions": session.get("functions") or [],
        "top_gotchas": session.get("gotchas") or [],
        "top_patterns": session.get("patterns") or [],
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    g = build_session_graph()
    print("meta:", g["meta"])
    print("kinds:", g["meta"].get("kinds"))
    print("sample nodes:")
    for n in g["nodes"][:12]:
        print(f"  {n['id']}: {n['label'][:70]}")
    print("\nquery: Sade Sati scoring")
    res = query_session_memory("Sade Sati scoring", top_k=8)
    for f in res["functions"]:
        print(f"  [{f.get('score'):.3f}] {f.get('name')} — {(f.get('description') or '')[:80]}")
    for x in res["results"][:8]:
        print(f"  * {x.get('kind')}: {x.get('name')} ({x.get('score'):.3f})")
