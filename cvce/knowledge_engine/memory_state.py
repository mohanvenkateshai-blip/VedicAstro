"""Shared runtime state for the self-evolving memory subsystem.

Holds the latest auto-map batch, pending schema mutations, and ingest log
so the /memory/* HTTP endpoints and the ingest-watcher daemon share one
in-process view. Persists lightly to disk so a process restart doesn't
lose the last proposal set.
"""

from __future__ import annotations

import json
import os
import threading
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

_LOCK = threading.RLock()

_DEFAULT_STATE_DIR = Path(
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

_state: dict[str, Any] = {
    "latest_map": None,  # AutoMapper result dict
    "latest_mutations": None,  # SchemaMutator proposal dict
    "pending_mutations": [],  # list of undecided proposals (flattened)
    "mutation_history": [],  # accept/reject decisions
    "ingest_log": [],  # recent ingest events
    "latest_batch_nodes": [],  # raw new nodes from last ingest
    "latest_batch_links": [],
    "updated_at": None,
}


def _state_path() -> Path:
    _DEFAULT_STATE_DIR.mkdir(parents=True, exist_ok=True)
    return _DEFAULT_STATE_DIR / "runtime.json"


def load() -> dict[str, Any]:
    """Load state from disk if present; return a deep copy."""
    path = _state_path()
    with _LOCK:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    _state.update(data)
            except Exception:
                pass
        return deepcopy(_state)


def save() -> None:
    path = _state_path()
    with _LOCK:
        _state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        path.write_text(json.dumps(_state, indent=2, default=str), encoding="utf-8")


def get() -> dict[str, Any]:
    with _LOCK:
        if _state.get("updated_at") is None:
            load()
        return deepcopy(_state)


def set_latest_map(result: dict[str, Any]) -> None:
    with _LOCK:
        _state["latest_map"] = result
        save()


def set_latest_mutations(proposal: dict[str, Any]) -> None:
    """Store a full mutation proposal and flatten items into pending queue."""
    with _LOCK:
        _state["latest_mutations"] = proposal
        pending: list[dict[str, Any]] = []
        for kind, key in (
            ("community", "new_communities"),
            ("relation_type", "new_relation_types"),
            ("node_type", "new_node_types"),
        ):
            for item in proposal.get(key) or []:
                entry = dict(item)
                entry["kind"] = kind
                entry["status"] = "pending"
                entry["proposal_id"] = (
                    f"{kind}:{entry.get('name') or entry.get('label') or entry.get('id') or len(pending)}"
                )
                pending.append(entry)
        _state["pending_mutations"] = pending
        save()


def set_latest_batch(nodes: list[dict], links: list[dict] | None = None) -> None:
    with _LOCK:
        _state["latest_batch_nodes"] = list(nodes or [])
        _state["latest_batch_links"] = list(links or [])
        save()


def log_ingest(event: dict[str, Any]) -> None:
    with _LOCK:
        log = list(_state.get("ingest_log") or [])
        event = dict(event)
        event.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        log.append(event)
        _state["ingest_log"] = log[-200:]  # keep last 200
        save()


def decide_mutation(proposal_id: str, accept: bool, note: str = "") -> dict[str, Any]:
    """Accept or reject a pending mutation by proposal_id."""
    with _LOCK:
        pending = list(_state.get("pending_mutations") or [])
        found = None
        remaining = []
        for p in pending:
            if p.get("proposal_id") == proposal_id:
                found = dict(p)
            else:
                remaining.append(p)
        if found is None:
            return {"ok": False, "error": f"proposal_id not found: {proposal_id}"}
        found["status"] = "accepted" if accept else "rejected"
        found["decided_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if note:
            found["note"] = note
        history = list(_state.get("mutation_history") or [])
        history.append(found)
        _state["mutation_history"] = history[-500:]
        _state["pending_mutations"] = remaining
        save()
        return {"ok": True, "decision": found}


def decide_all(accept: bool, note: str = "") -> dict[str, Any]:
    """Accept or reject every pending mutation."""
    with _LOCK:
        pending = list(_state.get("pending_mutations") or [])
        results = []
        for p in pending:
            item = dict(p)
            item["status"] = "accepted" if accept else "rejected"
            item["decided_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            if note:
                item["note"] = note
            results.append(item)
        history = list(_state.get("mutation_history") or [])
        history.extend(results)
        _state["mutation_history"] = history[-500:]
        _state["pending_mutations"] = []
        save()
        return {"ok": True, "count": len(results), "decisions": results}
