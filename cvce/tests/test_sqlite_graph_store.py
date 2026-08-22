"""
Tests for SQLiteKnowledgeStore + build_graph_db.py (B-56 durable fix).

Uses a small synthetic fixture graph (not the 21MB real corpus) so this runs
fast and doesn't depend on graph_rag/graph.json being present/current.
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from knowledge_engine.store.sqlite_store import SQLiteKnowledgeStore  # noqa: E402

FIXTURE_GRAPH = {
    "directed": False,
    "multigraph": False,
    "graph": {},
    "nodes": [
        {"id": "n1", "file_type": "concept", "label": "Mars", "source_file": "raw/a.md", "nature": "malefic"},
        {"id": "n2", "file_type": "document", "label": "BPHS", "source_file": "raw/b.md"},
        {"id": "n3", "file_type": "concept", "label": "Mangal Dosha", "source_file": "raw/a.md", "rule_text": "..."},
    ],
    "links": [
        {"source": "n1", "target": "n3", "relation": "causes", "confidence": "EXTRACTED", "confidence_score": Decimal("1.0"), "source_file": "raw/a.md"},
        {"source": "n2", "target": "n3", "relation": "cites", "confidence": "EXTRACTED", "confidence_score": Decimal("0.9"), "source_file": "raw/b.md"},
        # dangling target on purpose — real graph.json has these (58/157), must not crash the build
        {"source": "n1", "target": "ghost_node", "relation": "references", "confidence": "AMBIGUOUS", "confidence_score": Decimal("0.5"), "source_file": "raw/a.md"},
    ],
    "hyperedges": [
        {"id": "h1", "label": "Triad", "nodes": ["n1", "n2", "n3"], "relation": "compose", "confidence": "EXTRACTED"},
    ],
    "built_at_commit": "deadbeef",
}


@pytest.fixture()
def built_db(tmp_path):
    from build_graph_db import build  # imports scripts/build_graph_db.py

    src = tmp_path / "graph.json"

    def _decimal_default(o):
        if isinstance(o, Decimal):
            return float(o)
        raise TypeError

    src.write_text(json.dumps(FIXTURE_GRAPH, default=_decimal_default))
    db = tmp_path / "graph.db"
    build(str(src), str(db))
    return db


def test_build_produces_expected_counts(built_db):
    store = SQLiteKnowledgeStore(db_path=built_db)
    stats = store.get_stats()
    assert stats["node_count"] == 3
    assert stats["link_count"] == 3
    assert stats["hyperedge_count"] == 1
    assert stats["source"] == "sqlite"


def test_dangling_link_does_not_crash_build(built_db):
    # ghost_node is referenced by a link's target but never defined as a node
    store = SQLiteKnowledgeStore(db_path=built_db)
    assert store.get_node("ghost_node") is None
    # the link itself still round-trips
    links = store.get_links(source_id="n1")
    targets = {l["target"] for l in links}
    assert "ghost_node" in targets


def test_get_node_round_trips_all_fields(built_db):
    store = SQLiteKnowledgeStore(db_path=built_db)
    node = store.get_node("n1")
    assert node["label"] == "Mars"
    assert node["file_type"] == "concept"
    assert node["nature"] == "malefic"  # sparse field preserved via props blob


def test_get_links_filters_by_source(built_db):
    store = SQLiteKnowledgeStore(db_path=built_db)
    links = store.get_links(source_id="n2")
    assert len(links) == 1
    assert links[0]["target"] == "n3"
    assert links[0]["relation"] == "cites"
    assert links[0]["confidence_score"] == pytest.approx(0.9)


def test_get_nodes_page_pagination(built_db):
    store = SQLiteKnowledgeStore(db_path=built_db)
    page1 = store.get_nodes_page(limit=2, offset=0)
    page2 = store.get_nodes_page(limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 1
    assert {n["id"] for n in page1} | {n["id"] for n in page2} == {"n1", "n2", "n3"}


def test_health_check_true_when_db_present(built_db):
    assert SQLiteKnowledgeStore(db_path=built_db).health_check() is True


def test_health_check_false_when_db_missing(tmp_path):
    store = SQLiteKnowledgeStore(db_path=tmp_path / "does_not_exist.db")
    assert store.health_check() is False


def test_get_version_includes_built_at_commit(built_db):
    version = SQLiteKnowledgeStore(db_path=built_db).get_version()
    assert "deadbeef" in version


def test_supports_incremental_pagination_is_false(built_db):
    # A baked snapshot is atomic per build/deploy — no live cursor concept.
    assert SQLiteKnowledgeStore(db_path=built_db).supports_incremental_pagination() is False
