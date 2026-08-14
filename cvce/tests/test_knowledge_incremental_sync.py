"""B-egress-01: prove the incremental (updated_at, id) keyset sync actually
avoids re-walking the whole graph_nodes table on every reconcile.

Context: KnowledgeEngine._enumerate_current_research_nodes() used to do a
full unfiltered store scan (get_nodes_page, 500-row pages) on *every* call
where the cheap get_stats() row count differed from the cached one -- which
is guaranteed on every real ingest. Production logs showed ~13 full
26,500-row traversals in 24h from routine ingest activity. This file proves
the fix: a store that supports_incremental_pagination() only ever gets a
full table scan for (a) the very first call on a fresh engine, or (b) a
suspected deletion (count dropped, or a delta merge that doesn't reconcile
against the authoritative count) -- never for a routine additive ingest,
and never twice in a row for the same unchanged state.
"""

from __future__ import annotations

import copy
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from knowledge_engine.engine import KnowledgeEngine
from knowledge_engine.store.base import KnowledgeStore


def _ts(offset_seconds: float) -> str:
    """A strictly increasing ISO8601 UTC timestamp, offset from a fixed epoch."""
    base = datetime(2026, 1, 1, tzinfo=UTC)
    return (base + timedelta(seconds=offset_seconds)).isoformat()


class IncrementalStore(KnowledgeStore):
    """Test double for a backend that supports real (updated_at, id) keyset
    delta pagination, mirroring SupabaseKnowledgeStore's contract. Tracks
    call counts so tests can assert exactly what was and wasn't fetched."""

    def __init__(self, nodes: list[dict] | None = None) -> None:
        self.nodes: dict[str, dict] = {n["id"]: dict(n) for n in (nodes or [])}
        self.full_scan_calls = 0
        self.full_scan_offsets: list[int] = []
        self.delta_calls = 0
        self.delta_offsets: list[int] = []
        self.fail_full_at_offset: int | None = None
        self.fail_delta_at_offset: int | None = None
        self._lock = threading.Lock()

    # -- KnowledgeStore interface -----------------------------------------
    def get_version(self) -> str:
        return "incremental-test-v1"

    def get_stats(self) -> dict:
        with self._lock:
            max_updated_at = max(
                (n["updated_at"] for n in self.nodes.values()), default=None
            )
            return {"node_count": len(self.nodes), "max_updated_at": max_updated_at}

    def get_node(self, node_id: str) -> dict | None:
        with self._lock:
            node = self.nodes.get(node_id)
            return copy.deepcopy(node) if node else None

    def get_nodes(self, limit: int = 100) -> list[dict]:
        return self._sorted()[:limit]

    def get_links(self, source_id: str | None = None, limit: int = 100) -> list[dict]:
        return []

    def health_check(self) -> bool:
        return True

    def _sorted(self) -> list[dict]:
        with self._lock:
            rows = list(self.nodes.values())
        rows.sort(key=lambda n: (n["updated_at"], n["id"]))
        return [copy.deepcopy(n) for n in rows]

    def get_nodes_page(self, limit: int = 500, offset: int = 0) -> list[dict]:
        self.full_scan_calls += 1
        self.full_scan_offsets.append(offset)
        if self.fail_full_at_offset == offset:
            self.fail_full_at_offset = None
            raise RuntimeError("simulated full-scan interruption")
        return self._sorted()[offset : offset + limit]

    def supports_incremental_pagination(self) -> bool:
        return True

    def get_nodes_page_since(
        self, cursor: tuple[str, str] | None, limit: int = 500, offset: int = 0
    ) -> list[dict]:
        self.delta_calls += 1
        self.delta_offsets.append(offset)
        if self.fail_delta_at_offset == offset:
            self.fail_delta_at_offset = None
            raise RuntimeError("simulated delta interruption")
        rows = self._sorted()
        if cursor is not None:
            rows = [n for n in rows if (n["updated_at"], n["id"]) > cursor]
        return rows[offset : offset + limit]

    # -- test helpers -------------------------------------------------------
    def upsert(self, node_id: str, **fields) -> None:
        with self._lock:
            self.nodes[node_id] = {"id": node_id, "updated_at": _ts(0), **fields}

    def delete(self, node_id: str) -> None:
        with self._lock:
            self.nodes.pop(node_id, None)

    def reset_counters(self) -> None:
        self.full_scan_calls = 0
        self.full_scan_offsets = []
        self.delta_calls = 0
        self.delta_offsets = []


def _baseline_store(n: int = 3) -> IncrementalStore:
    nodes = [
        {"id": f"node-{i:03d}", "updated_at": _ts(i), "content": f"body {i}"}
        for i in range(n)
    ]
    return IncrementalStore(nodes)


def _engine(store: IncrementalStore) -> KnowledgeEngine:
    ke = KnowledgeEngine(store=store)
    # __post_init__ already ran _reconcile_research_snapshot("engine_start")
    # against whatever self.graph was at construction time -- in this venv
    # that's the *real* GraphRAG singleton, eagerly loading the actual
    # production graph (tens of thousands of real nodes) before we get a
    # chance to swap in a clean local graph for the test. Reset the
    # snapshot state to match the overridden graph, or the next
    # _reconcile_research_snapshot() call would diff against that stale
    # real-production snapshot and "archive" tens of thousands of nodes
    # that were never part of this test.
    ke.graph = type("EmptyLocalGraph", (), {"nodes": [], "links": []})()
    ke._research_graph_snapshot = {}
    ke._research_graph_snapshot_version = None
    return ke


# ---------------------------------------------------------------------------
# no-repeat-full-scan: the core required proof
# ---------------------------------------------------------------------------


def test_second_unchanged_query_performs_zero_full_table_reads() -> None:
    store = _baseline_store(5)
    ke = _engine(store)

    first = ke.query_research_nodes()
    assert first["status"]["returned_count"] == 5
    assert store.full_scan_calls == 1  # unavoidable baseline

    store.reset_counters()
    second = ke.query_research_nodes()
    assert second["status"]["returned_count"] == 5
    assert store.full_scan_calls == 0
    assert store.delta_calls == 0


def test_changed_ingest_fetches_only_the_delta_not_a_full_scan() -> None:
    store = _baseline_store(3)
    ke = _engine(store)
    ke.query_research_nodes()  # baseline
    assert store.full_scan_calls == 1

    store.reset_counters()
    store.upsert("node-new", updated_at=_ts(1000), content="freshly ingested")

    result = ke.query_research_nodes()
    assert result["status"]["returned_count"] == 4
    ids = {n["id"] for n in result["nodes"]}
    assert "node-new" in ids
    assert store.full_scan_calls == 0
    assert store.delta_calls >= 1

    # And the cursor advanced correctly: a further unchanged call is a pure
    # cache hit again, not a repeat delta fetch.
    store.reset_counters()
    ke.query_research_nodes()
    assert store.full_scan_calls == 0
    assert store.delta_calls == 0


def test_two_sequential_ingests_each_fetch_only_their_own_delta() -> None:
    store = _baseline_store(2)
    ke = _engine(store)
    ke.query_research_nodes()

    store.reset_counters()
    store.upsert("node-a", updated_at=_ts(500), content="first new doc")
    result_a = ke.query_research_nodes()
    assert result_a["status"]["returned_count"] == 3
    assert store.full_scan_calls == 0
    delta_calls_after_a = store.delta_calls
    assert delta_calls_after_a >= 1

    store.reset_counters()
    store.upsert("node-b", updated_at=_ts(600), content="second new doc")
    result_b = ke.query_research_nodes()
    assert result_b["status"]["returned_count"] == 4
    assert store.full_scan_calls == 0
    assert store.delta_calls >= 1


# ---------------------------------------------------------------------------
# explicit deletion handling
# ---------------------------------------------------------------------------


def test_deletion_triggers_full_scan_and_explicitly_archives_the_node() -> None:
    store = _baseline_store(3)
    ke = _engine(store)
    ke.query_research_nodes()
    assert store.full_scan_calls == 1

    store.reset_counters()
    store.delete("node-001")

    result = ke.query_research_nodes()
    # A deletion is a real signal a pure-additive delta can't observe -- it
    # must be reconciled via a real full scan, not silently missed.
    assert store.full_scan_calls == 1
    assert store.delta_calls == 0

    by_id = {n["id"]: n for n in result["nodes"]}
    # Research queries deliberately retain removed captures (annotated), so
    # node-001 is still present in the default result -- but explicitly
    # flagged as archived, and the two untouched nodes are not.
    assert by_id["node-001"]["research_status"]["archived_capture"] is True
    assert by_id["node-001"]["research_status"]["removal"]["reason"] == "removed_from_store"
    assert by_id["node-001"]["research_status"]["removal"]["removed_at"]
    assert by_id["node-000"]["research_status"]["archived_capture"] is False
    assert by_id["node-002"]["research_status"]["archived_capture"] is False


def test_delete_and_reinsert_netting_same_count_still_reconciles() -> None:
    """A delete + a same-count insert can't be told apart from 'nothing
    happened' by the cheap row-count check alone. The delta-merge total
    must still catch it and fall back to a full scan."""
    store = _baseline_store(3)
    ke = _engine(store)
    ke.query_research_nodes()

    store.reset_counters()
    store.delete("node-001")
    store.upsert("node-999", updated_at=_ts(2000), content="replacement row")
    # Net count is unchanged (3), so the cheap deletion-count shortcut can't
    # fire -- this must be caught by the delta/expected-count reconciliation.

    result = ke.query_research_nodes()
    by_id = {n["id"]: n for n in result["nodes"]}
    assert by_id["node-001"]["research_status"]["archived_capture"] is True
    assert by_id["node-999"]["research_status"]["archived_capture"] is False
    live_ids = {
        n["id"] for n in result["nodes"] if not n["research_status"]["archived_capture"]
    }
    assert live_ids == {"node-000", "node-002", "node-999"}
    assert store.full_scan_calls == 1  # reconciliation fallback, not a silent miss


# ---------------------------------------------------------------------------
# interruption / retry
# ---------------------------------------------------------------------------


def test_delta_interruption_falls_back_to_full_scan_and_recovers() -> None:
    store = _baseline_store(3)
    ke = _engine(store)
    ke.query_research_nodes()

    store.reset_counters()
    store.upsert("node-new", updated_at=_ts(1000), content="new doc")
    store.fail_delta_at_offset = 0  # delta fetch breaks mid-flight

    result = ke.query_research_nodes()
    # Delta failed -> fell back to a full scan this call -> still correct.
    assert result["status"]["returned_count"] == 4
    assert result["status"]["source_enumeration_complete"] is True
    assert store.delta_calls == 1  # attempted, failed
    assert store.full_scan_calls == 1  # recovered via fallback

    # Cache/cursor state must be left consistent -- a further unchanged call
    # is a pure cache hit, not another scan.
    store.reset_counters()
    ke.query_research_nodes()
    assert store.full_scan_calls == 0
    assert store.delta_calls == 0


def test_full_scan_failure_reports_incomplete_without_crashing_or_poisoning_state() -> None:
    store = _baseline_store(3)
    store.fail_full_at_offset = 0
    # KnowledgeEngine.__post_init__ runs its own engine_start reconcile
    # immediately, so construction itself is the attempt that hits the
    # simulated interruption (the fail flag fires exactly once).
    ke = _engine(store)

    diag = ke._research_enumeration_cache_diagnostics
    assert diag is not None
    assert diag["enumeration_complete"] is False
    assert "simulated full-scan interruption" in (diag["source_error"] or "")
    # Nothing was successfully retrieved -- an empty/no cache, not a
    # poisoned one masquerading as real data.
    assert ke._research_enumeration_cache in (None, [])


def test_retry_after_transient_full_scan_failure_recovers_cleanly() -> None:
    store = _baseline_store(3)
    store.fail_full_at_offset = 0
    # Construction's own engine_start reconcile is the attempt that fails
    # (fail flag fires exactly once, then clears itself).
    ke = _engine(store)
    assert ke._research_enumeration_cache_diagnostics["enumeration_complete"] is False

    # Retry via an explicit query -- the transient failure is gone now.
    recovered = ke.query_research_nodes()
    assert recovered["status"]["source_enumeration_complete"] is True
    assert recovered["status"]["returned_count"] == 3


# ---------------------------------------------------------------------------
# duplicate ingest (idempotency)
# ---------------------------------------------------------------------------


def test_duplicate_ingest_of_unchanged_content_is_a_pure_cache_hit() -> None:
    store = _baseline_store(3)
    ke = _engine(store)
    first = ke.query_research_nodes()
    assert first["status"]["returned_count"] == 3

    store.reset_counters()
    # Re-running ingest for content that didn't actually change: no new row,
    # row count identical -- must not grow the result or force any read.
    second = ke.query_research_nodes()
    third = ke.query_research_nodes()
    assert second["status"]["returned_count"] == 3
    assert third["status"]["returned_count"] == 3
    assert store.full_scan_calls == 0
    assert store.delta_calls == 0


def test_duplicate_ingest_that_rewrites_an_existing_node_stays_idempotent() -> None:
    """Re-ingesting an existing node with a bumped updated_at (the real
    corpus-sync writer stamps updated_at on every upsert, changed or not)
    must merge in place -- no duplication, no growth -- via the delta path
    when it happens to accompany a genuine net-new row, its ordinary case."""
    store = _baseline_store(3)
    ke = _engine(store)
    ke.query_research_nodes()

    store.reset_counters()
    store.upsert("node-000", updated_at=_ts(9999), content="body 0 (re-synced, identical)")
    store.upsert("node-new", updated_at=_ts(10000), content="a real new doc")
    result = ke.query_research_nodes()
    assert result["status"]["returned_count"] == 4  # no duplication of node-000
    ids = [n["id"] for n in result["nodes"]]
    assert ids.count("node-000") == 1
    assert store.full_scan_calls == 0


# ---------------------------------------------------------------------------
# concurrent ingest
# ---------------------------------------------------------------------------


def test_concurrent_reconciles_during_ingest_stay_consistent_and_thread_safe() -> None:
    store = _baseline_store(2)
    ke = _engine(store)
    ke.query_research_nodes()  # baseline

    def ingest_one(i: int) -> None:
        store.upsert(f"concurrent-{i:03d}", updated_at=_ts(2000 + i), content=f"doc {i}")
        ke._reconcile_research_snapshot(f"concurrent-ingest-{i}")

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(ingest_one, range(24)))

    final = ke.query_research_nodes()
    # 2 baseline + 24 concurrently ingested, all observed, none lost, no
    # duplicates, and nothing crashed under concurrent lock contention.
    assert final["status"]["returned_count"] == 26
    ids = [n["id"] for n in final["nodes"]]
    assert len(ids) == len(set(ids))
    for i in range(24):
        assert f"concurrent-{i:03d}" in ids
