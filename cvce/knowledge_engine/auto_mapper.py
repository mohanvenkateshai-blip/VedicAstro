"""Auto-mapping engine — embed new graph nodes and propose links.

Given new graphify nodes, embeds each node's label+description with the
local BGE embedder, scores cosine similarity against the existing corpus,
and returns:
  - top-k nearest neighbours per new node
  - proposed links where similarity > threshold (default 0.75)
  - DUPLICATE flags where similarity > 0.95
  - CONTRADICTION flags where high-similarity pairs carry opposing claims
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Iterable

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_GRAPH_PATH = Path(
    os.environ.get(
        "GRAPHIFY_GRAPH_PATH",
        str(
            Path(__file__).resolve().parents[2]
            / "knowledge-graph"
            / "graphify-out"
            / "graph.json"
        ),
    )
)

DEFAULT_CACHE_DIR = Path(
    os.environ.get(
        "MEMORY_STATE_DIR",
        str(
            Path(__file__).resolve().parents[2]
            / "knowledge-graph"
            / "graphify-out"
            / "memory-state"
        ),
    )
)

DEFAULT_THRESHOLD = 0.75
DUPLICATE_THRESHOLD = 0.95
DEFAULT_TOP_K = 5
EMBED_BATCH = 64

# Polarity lexicon for cheap contradiction detection on Vedic claim text.
_POSITIVE = {
    "auspicious",
    "benefic",
    "favourable",
    "favorable",
    "shubha",
    "shubh",
    "good",
    "positive",
    "strengthens",
    "supports",
    "excellent",
    "recommended",
    "permitted",
    "gain",
    "prosperity",
    "success",
    "remedy",
    "protective",
}
_NEGATIVE = {
    "inauspicious",
    "malefic",
    "unfavourable",
    "unfavorable",
    "ashubha",
    "ashubh",
    "bad",
    "negative",
    "weakens",
    "destroys",
    "afflicts",
    "forbidden",
    "avoid",
    "loss",
    "death",
    "disease",
    "danger",
    "obstruction",
    "dosha",
    "affliction",
    "contraindicated",
}


def _node_text(node: dict[str, Any]) -> str:
    """Canonical text used for embedding a node."""
    parts: list[str] = []
    for key in ("label", "norm_label", "description", "summary", "text", "content"):
        val = node.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
    # source_file helps disambiguate same-label concepts from different texts
    src = node.get("source_file")
    if isinstance(src, str) and src.strip():
        parts.append(f"source:{src.strip()}")
    return " — ".join(parts) if parts else str(node.get("id") or "")


def _cosine_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Row-wise cosine similarity between A (n,d) and B (m,d) → (n,m)."""
    a_n = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-12)
    b_n = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-12)
    return a_n @ b_n.T


def _polarity(text: str) -> str:
    """Return 'pos', 'neg', 'mixed', or 'neutral' from claim wording."""
    tokens = set(re.findall(r"[a-zA-Z]+", (text or "").lower()))
    pos = bool(tokens & _POSITIVE)
    neg = bool(tokens & _NEGATIVE)
    if pos and neg:
        return "mixed"
    if pos:
        return "pos"
    if neg:
        return "neg"
    return "neutral"


def _opposing(a: str, b: str) -> bool:
    pa, pb = _polarity(a), _polarity(b)
    return (pa == "pos" and pb == "neg") or (pa == "neg" and pb == "pos")


def _embed_texts(texts: list[str]) -> np.ndarray:
    """Embed texts via local_embedder; returns float32 (n, dim)."""
    from knowledge_engine.local_embedder import LOCAL_EMBED_DIM, embed_documents

    if not texts:
        return np.zeros((0, LOCAL_EMBED_DIM), dtype=np.float32)

    vectors: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH):
        batch = texts[i : i + EMBED_BATCH]
        # Replace empties so positional alignment holds
        cleaned = [t if (t or "").strip() else " " for t in batch]
        try:
            vecs = embed_documents(cleaned)
        except Exception as exc:
            logger.warning("embed_documents failed, using hash fallback: %s", exc)
            vecs = [_hash_embed(t, LOCAL_EMBED_DIM) for t in cleaned]
        vectors.extend(vecs)
    arr = np.asarray(vectors, dtype=np.float32)
    return arr


def _hash_embed(text: str, dim: int = 384) -> list[float]:
    """Deterministic bag-of-hashes fallback when ONNX embedder is unavailable."""
    vec = np.zeros(dim, dtype=np.float64)
    tokens = re.findall(r"[a-zA-Z0-9_]+", (text or "").lower())
    if not tokens:
        tokens = ["empty"]
    for tok in tokens:
        h = hashlib.sha256(tok.encode("utf-8")).digest()
        # use 8 uint32s worth of entropy, folded into dim
        for i in range(0, 32, 4):
            idx = int.from_bytes(h[i : i + 4], "little") % dim
            sign = 1.0 if (h[i] & 1) == 0 else -1.0
            vec[idx] += sign
    n = np.linalg.norm(vec)
    if n > 0:
        vec = vec / n
    return [float(x) for x in vec]


def load_graph(path: Path | str | None = None) -> dict[str, Any]:
    p = Path(path) if path else DEFAULT_GRAPH_PATH
    with p.open(encoding="utf-8") as f:
        return json.load(f)


class EmbeddingIndex:
    """Disk-cached embedding matrix for the existing graph corpus."""

    def __init__(self, cache_dir: Path | str | None = None):
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ids: list[str] = []
        self.labels: list[str] = []
        self.texts: list[str] = []
        self.matrix: np.ndarray | None = None  # (n, dim)
        self._id_to_row: dict[str, int] = {}

    @property
    def cache_path(self) -> Path:
        return self.cache_dir / "node_embeddings.npz"

    def build(
        self,
        nodes: list[dict[str, Any]],
        *,
        force: bool = False,
        max_nodes: int | None = None,
        progress: bool = False,
    ) -> "EmbeddingIndex":
        """Build or load the embedding index for `nodes`."""
        use_nodes = list(nodes)
        if max_nodes is not None and max_nodes > 0:
            use_nodes = use_nodes[:max_nodes]

        fingerprint = hashlib.sha1(
            ("|".join(str(n.get("id") or "") for n in use_nodes)).encode("utf-8")
        ).hexdigest()[:16]

        if not force and self.cache_path.exists():
            try:
                data = np.load(self.cache_path, allow_pickle=True)
                if str(data.get("fingerprint", "")) == fingerprint:
                    self.ids = list(data["ids"].tolist())
                    self.labels = list(data["labels"].tolist())
                    self.texts = list(data["texts"].tolist())
                    self.matrix = np.asarray(data["matrix"], dtype=np.float32)
                    self._id_to_row = {i: r for r, i in enumerate(self.ids)}
                    logger.info(
                        "Loaded embedding cache: %d nodes from %s",
                        len(self.ids),
                        self.cache_path,
                    )
                    return self
            except Exception as exc:
                logger.warning("Embedding cache load failed: %s", exc)

        self.ids = [str(n.get("id") or f"anon_{i}") for i, n in enumerate(use_nodes)]
        self.labels = [str(n.get("label") or "") for n in use_nodes]
        self.texts = [_node_text(n) for n in use_nodes]
        if progress:
            logger.info("Embedding %d existing nodes…", len(self.texts))
        t0 = time.time()
        self.matrix = _embed_texts(self.texts)
        self._id_to_row = {i: r for r, i in enumerate(self.ids)}
        logger.info(
            "Embedded %d nodes in %.1fs (dim=%s)",
            len(self.ids),
            time.time() - t0,
            self.matrix.shape[1] if self.matrix is not None else "?",
        )
        try:
            np.savez_compressed(
                self.cache_path,
                fingerprint=np.asarray(fingerprint),
                ids=np.asarray(self.ids, dtype=object),
                labels=np.asarray(self.labels, dtype=object),
                texts=np.asarray(self.texts, dtype=object),
                matrix=self.matrix,
            )
        except Exception as exc:
            logger.warning("Failed to write embedding cache: %s", exc)
        return self

    def node_meta(self, row: int) -> dict[str, Any]:
        return {
            "id": self.ids[row],
            "label": self.labels[row],
            "text": self.texts[row],
        }


class AutoMapper:
    """Map new nodes onto the existing knowledge graph via cosine similarity."""

    def __init__(
        self,
        graph_path: Path | str | None = None,
        *,
        threshold: float = DEFAULT_THRESHOLD,
        duplicate_threshold: float = DUPLICATE_THRESHOLD,
        top_k: int = DEFAULT_TOP_K,
        cache_dir: Path | str | None = None,
    ):
        self.graph_path = Path(graph_path) if graph_path else DEFAULT_GRAPH_PATH
        self.threshold = float(threshold)
        self.duplicate_threshold = float(duplicate_threshold)
        self.top_k = int(top_k)
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self._index: EmbeddingIndex | None = None
        self._nodes_by_id: dict[str, dict] = {}
        self._graph_links: list[dict] = []

    def load_corpus(self, *, max_nodes: int | None = None, force_reembed: bool = False) -> int:
        """Load graph.json and (re)build the embedding index. Returns node count."""
        data = load_graph(self.graph_path)
        nodes = list(data.get("nodes") or [])
        self._graph_links = list(data.get("links") or [])
        self._nodes_by_id = {
            str(n.get("id")): n for n in nodes if isinstance(n, dict) and n.get("id")
        }
        self._index = EmbeddingIndex(self.cache_dir).build(
            nodes, force=force_reembed, max_nodes=max_nodes, progress=True
        )
        return len(self._index.ids)

    @property
    def index(self) -> EmbeddingIndex:
        if self._index is None:
            self.load_corpus()
        assert self._index is not None
        return self._index

    def map_nodes(
        self,
        new_nodes: list[dict[str, Any]],
        *,
        threshold: float | None = None,
        top_k: int | None = None,
        exclude_self: bool = True,
    ) -> dict[str, Any]:
        """
        Embed `new_nodes` and score against the corpus.

        Returns a result dict:
          {
            matches: [{new_id, new_label, neighbours: [{id,label,score}]}],
            proposed_links: [...],
            duplicates: [...],
            contradictions: [...],
            meta: {...},
          }
        """
        thr = float(self.threshold if threshold is None else threshold)
        k = int(self.top_k if top_k is None else top_k)
        idx = self.index
        if idx.matrix is None or idx.matrix.shape[0] == 0:
            return {
                "matches": [],
                "proposed_links": [],
                "duplicates": [],
                "contradictions": [],
                "meta": {"error": "empty corpus index", "threshold": thr},
            }

        new_nodes = [n for n in (new_nodes or []) if isinstance(n, dict)]
        if not new_nodes:
            return {
                "matches": [],
                "proposed_links": [],
                "duplicates": [],
                "contradictions": [],
                "meta": {"new_count": 0, "corpus_count": idx.matrix.shape[0], "threshold": thr},
            }

        new_ids = [str(n.get("id") or f"new_{i}") for i, n in enumerate(new_nodes)]
        new_labels = [str(n.get("label") or "") for n in new_nodes]
        new_texts = [_node_text(n) for n in new_nodes]
        new_mat = _embed_texts(new_texts)

        sims = _cosine_matrix(new_mat, idx.matrix)  # (n_new, n_corpus)

        matches: list[dict[str, Any]] = []
        proposed_links: list[dict[str, Any]] = []
        duplicates: list[dict[str, Any]] = []
        contradictions: list[dict[str, Any]] = []

        for i, nid in enumerate(new_ids):
            row = sims[i]
            # argsort descending
            order = np.argsort(-row)
            neighbours: list[dict[str, Any]] = []
            for rank, j in enumerate(order):
                if exclude_self and idx.ids[j] == nid:
                    continue
                score = float(row[j])
                meta = idx.node_meta(int(j))
                entry = {
                    "id": meta["id"],
                    "label": meta["label"],
                    "score": round(score, 6),
                    "community": (self._nodes_by_id.get(meta["id"]) or {}).get("community"),
                    "source_file": (self._nodes_by_id.get(meta["id"]) or {}).get("source_file"),
                }
                if len(neighbours) < k:
                    neighbours.append(entry)

                if score >= thr:
                    link = {
                        "source": nid,
                        "target": meta["id"],
                        "relation": "semantically_related",
                        "confidence": "INFERRED",
                        "confidence_score": round(score, 6),
                        "source_label": new_labels[i],
                        "target_label": meta["label"],
                        "weight": round(score, 6),
                    }
                    proposed_links.append(link)

                    if score >= self.duplicate_threshold:
                        duplicates.append(
                            {
                                "new_id": nid,
                                "new_label": new_labels[i],
                                "existing_id": meta["id"],
                                "existing_label": meta["label"],
                                "score": round(score, 6),
                                "flag": "DUPLICATE",
                            }
                        )

                    # Contradiction: high sim + opposing polarity in claim text
                    if score >= thr and _opposing(new_texts[i], meta["text"]):
                        contradictions.append(
                            {
                                "new_id": nid,
                                "new_label": new_labels[i],
                                "new_text": new_texts[i][:240],
                                "existing_id": meta["id"],
                                "existing_label": meta["label"],
                                "existing_text": meta["text"][:240],
                                "score": round(score, 6),
                                "new_polarity": _polarity(new_texts[i]),
                                "existing_polarity": _polarity(meta["text"]),
                                "flag": "CONTRADICTION",
                            }
                        )

                # Once past top-k and below threshold we can stop scanning this row
                if len(neighbours) >= k and score < thr:
                    # still need full scan for thr matches? for large corpus full scan
                    # of sorted order is fine — break when score drops below thr and k filled
                    if score < thr:
                        break
                # safety: don't scan entire 26k if far below thr after top chunk
                if rank > max(k * 20, 200) and score < thr:
                    break

            matches.append(
                {
                    "new_id": nid,
                    "new_label": new_labels[i],
                    "neighbours": neighbours,
                }
            )

        # Also surface existing graph 'contradicts' edges touching the new set
        new_id_set = set(new_ids)
        for link in self._graph_links:
            if link.get("relation") != "contradicts":
                continue
            src, tgt = link.get("source"), link.get("target")
            if src in new_id_set or tgt in new_id_set:
                contradictions.append(
                    {
                        "new_id": src if src in new_id_set else tgt,
                        "existing_id": tgt if src in new_id_set else src,
                        "source_label": (self._nodes_by_id.get(src) or {}).get("label", src),
                        "target_label": (self._nodes_by_id.get(tgt) or {}).get("label", tgt),
                        "score": float(link.get("confidence_score") or 1.0),
                        "flag": "CONTRADICTION",
                        "origin": "graph_link",
                        "source_file": link.get("source_file"),
                    }
                )

        result = {
            "matches": matches,
            "proposed_links": proposed_links,
            "duplicates": duplicates,
            "contradictions": contradictions,
            "meta": {
                "new_count": len(new_nodes),
                "corpus_count": int(idx.matrix.shape[0]),
                "threshold": thr,
                "duplicate_threshold": self.duplicate_threshold,
                "top_k": k,
                "proposed_link_count": len(proposed_links),
                "duplicate_count": len(duplicates),
                "contradiction_count": len(contradictions),
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        }
        return result

    def map_and_store(
        self,
        new_nodes: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Run map_nodes and persist result into memory_state."""
        from knowledge_engine import memory_state

        result = self.map_nodes(new_nodes, **kwargs)
        memory_state.set_latest_batch(new_nodes)
        memory_state.set_latest_map(result)
        return result


def map_new_nodes(
    new_nodes: list[dict[str, Any]],
    *,
    graph_path: Path | str | None = None,
    threshold: float = DEFAULT_THRESHOLD,
    top_k: int = DEFAULT_TOP_K,
    max_corpus_nodes: int | None = None,
    store: bool = True,
) -> dict[str, Any]:
    """Convenience functional API used by the watcher and HTTP handlers."""
    mapper = AutoMapper(graph_path=graph_path, threshold=threshold, top_k=top_k)
    mapper.load_corpus(max_nodes=max_corpus_nodes)
    if store:
        return mapper.map_and_store(new_nodes, threshold=threshold, top_k=top_k)
    return mapper.map_nodes(new_nodes, threshold=threshold, top_k=top_k)


# ── CLI / self-test ─────────────────────────────────────────────────────────

def _demo_batch() -> list[dict[str, Any]]:
    return [
        {
            "id": "test_sade_sati_scoring",
            "label": "Sade Sati scoring — transit of Saturn over natal Moon",
            "description": (
                "Sade Sati is the 7.5-year period when Saturn transits the 12th, "
                "1st and 2nd from the natal Moon. Scoring uses Kaksha sub-periods "
                "and ashubha affliction weights."
            ),
            "file_type": "concept",
            "source_file": "test/sade_sati.md",
        },
        {
            "id": "test_kalachakra_dasha_start",
            "label": "Kalachakra dasha starting point from navamsa",
            "description": (
                "Kalachakra dasha begins from the navamsa of the Moon. "
                "Auspicious results when dasha lord is benefic and well placed."
            ),
            "file_type": "concept",
            "source_file": "test/kalachakra.md",
        },
        {
            "id": "test_malefic_transit_claim",
            "label": "Saturn transit over Moon is highly auspicious and beneficial",
            "description": (
                "This contrarian claim says Saturn over natal Moon is favourable, "
                "shubha and brings prosperity — opposing classical malefic view."
            ),
            "file_type": "concept",
            "source_file": "test/contrarian.md",
        },
    ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # Small corpus slice for a fast smoke test; full corpus uses cache after first build.
    max_n = int(os.environ.get("AUTO_MAPPER_MAX_NODES", "800"))
    mapper = AutoMapper(threshold=0.5, top_k=5)
    n = mapper.load_corpus(max_nodes=max_n)
    print(f"corpus_indexed={n}")
    result = mapper.map_nodes(_demo_batch(), threshold=0.45)
    print(json.dumps(result["meta"], indent=2))
    for m in result["matches"]:
        top = m["neighbours"][:3]
        print(f"\n{m['new_label'][:60]}")
        for nb in top:
            print(f"  {nb['score']:.4f}  {nb['label'][:70]}")
    print(f"\nduplicates={len(result['duplicates'])} contradictions={len(result['contradictions'])}")
    print(f"proposed_links={len(result['proposed_links'])}")
