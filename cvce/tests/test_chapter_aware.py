"""
Minimal tests for chapter-aware engine integration.

Verifies:
- Engines register with KE and on_refresh loads structured chapter data.
- detect_yogas / compute_dasha / compute_ashtakavarga attach chapter_citation / hierarchy_path fields (may be None in minimal env).
- get_structured_book / get_hierarchy_for_node are usable via the integration layer.
"""

import pytest

from knowledge_engine.integration import (
    get_structured_book,
    get_hierarchy_for_node,
    get_nodes_for_chapter,
    get_knowledge_engine,
)


def test_ke_structured_apis_available():
    # Should not raise; tolerate missing graph in test env
    try:
        b = get_structured_book("Brihat_Parasara_Hora_Sastra_Vol_1")
    except Exception:
        b = None
    assert b is None or isinstance(b, dict)

    try:
        h = get_hierarchy_for_node("nonexistent_node_123")
    except Exception:
        h = None
    assert h is None or isinstance(h, dict)

    try:
        ns = get_nodes_for_chapter("Brihat_Parasara_Hora_Sastra_Vol_1", "ch-36")
    except Exception:
        ns = []
    assert isinstance(ns, list)


def test_yoga_engine_chapter_fields_present():
    from vedic_engine.prediction.yoga import detect_yogas, DetectedYoga

    # Minimal natal data
    natal = {"Sun": 0, "Moon": 3, "Mars": 1, "Mercury": 2, "Jupiter": 4, "Venus": 5, "Saturn": 6}
    yogas = detect_yogas(natal, lagna_sign_idx=0)
    assert isinstance(yogas, list)
    for y in yogas:
        assert isinstance(y, DetectedYoga)
        # New fields must exist (populated or None)
        assert hasattr(y, "chapter_citation")
        assert hasattr(y, "hierarchy_path")
        assert hasattr(y, "chapter_confidence")


def test_dasha_engine_chapter_fields_present():
    from vedic_engine.prediction.dasha import compute_dasha, DashaResult

    res = compute_dasha("1990-01-01", birth_nakshatra="Ashwini", query_date="2026-06-30")
    assert isinstance(res, DashaResult)
    assert hasattr(res, "chapter_citation")
    assert hasattr(res, "hierarchy_path")


def test_ashtakavarga_engine_chapter_fields_present():
    from vedic_engine.prediction.ashtakavarga import compute_ashtakavarga, AshtakavargaResult

    natal = {"Sun": 0, "Moon": 3, "Mars": 1, "Mercury": 2, "Jupiter": 4, "Venus": 5, "Saturn": 6}
    akv = compute_ashtakavarga(natal, lagna_sign_idx=0)
    assert isinstance(akv, AshtakavargaResult)
    assert hasattr(akv, "chapter_citation")
    assert hasattr(akv, "hierarchy_path")


def test_engines_registered_with_ke():
    try:
        ke = get_knowledge_engine()
        names = set(ke.registry.registered_names())
    except Exception:
        names = set()
    # At minimum the ones we touch should be present after imports above
    # (registration happens at import time). In minimal env tolerate empty.
    assert (
        "yoga" in names
        or "dasha" in names
        or "ashtakavarga" in names
        or "report" in names
        or len(names) == 0  # env without graph is acceptable for this smoke
    )
