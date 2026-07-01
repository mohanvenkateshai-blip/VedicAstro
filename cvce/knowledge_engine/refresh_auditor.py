"""
KnowledgeRefreshAuditor — baseline / refresh / compare workflow for registered engines.

Captures lightweight output snapshots before and after a global refresh, then scores
per-engine impact as minimal, moderate, or quantum.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .engine import KnowledgeEngine


class RefreshImpact(str, Enum):
    MINIMAL = "minimal"
    MODERATE = "moderate"
    QUANTUM = "quantum"


ProbeFn = Callable[[KnowledgeEngine], dict[str, Any]]


def _fingerprint(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _safe_knowledge_snapshot(ke: KnowledgeEngine, engine_name: str) -> dict[str, Any]:
    try:
        return ke.get_safe_knowledge(engine_name)
    except Exception as exc:
        return {"error": str(exc)}


def _probe_gochar(ke: KnowledgeEngine) -> dict[str, Any]:
    snapshot: dict[str, Any] = {"knowledge": _safe_knowledge_snapshot(ke, "gochar")}
    rules_meta: dict[str, Any] = {"available": False}
    try:
        rules = ke.get_safe_rules("transit")
        if rules is None:
            rules_meta["source"] = "hardcoded"
        elif hasattr(rules, "_tables"):
            tables = rules._tables
            st = getattr(rules, "stats", {}) or {}
            # Capture enrichment + citation signals for impact scoring
            eff_nodes = sum(1 for t in tables.values() if t.get("_effect_good") or t.get("_per_house_notes"))
            cite_sample = 0
            try:
                if hasattr(rules, "get_citations"):
                    for p in ["Sun", "Moon", "Jupiter"]:
                        cite_sample += len(rules.get_citations(p, 3) or [])
            except Exception:
                pass
            bid = getattr(rules, "_build_id", 0)
            rules_meta = {
                "available": True,
                "source": "graph",
                "planet_count": len(tables),
                "entry_count": sum(len(v) for v in tables.values()),
                "houses_enriched": st.get("houses_enriched", eff_nodes),
                "citations_sample": cite_sample,
                "build_id": bid,
                "content_hash": _fingerprint(
                    {
                        "tables": tables,
                        "enriched": st.get("houses_enriched", eff_nodes),
                        "cites": cite_sample,
                        "bid": bid,
                    }
                ),
            }
        else:
            rules_meta = {"available": True, "source": type(rules).__name__}
    except Exception as exc:
        rules_meta["error"] = str(exc)
    snapshot["rules"] = rules_meta
    snapshot["fingerprint"] = _fingerprint(rules_meta)
    return snapshot


def _probe_muhurta(ke: KnowledgeEngine) -> dict[str, Any]:
    snapshot: dict[str, Any] = {"knowledge": _safe_knowledge_snapshot(ke, "muhurta")}
    rules_meta: dict[str, Any] = {"available": False}
    try:
        rules = ke.get_safe_rules("muhurta")
        if rules is None:
            rules_meta["source"] = "hardcoded"
        else:
            yoga_nodes = getattr(rules, "_yoga_nodes", []) or []
            combo_nodes = getattr(rules, "_combo_nodes", []) or []
            sav_bands = getattr(rules, "_sav_bands", []) or []
            rules_meta = {
                "available": True,
                "source": "graph",
                "yoga_node_count": len(yoga_nodes),
                "combo_node_count": len(combo_nodes),
                "sav_band_count": len(sav_bands),
                "content_hash": _fingerprint(
                    {
                        "yoga": len(yoga_nodes),
                        "combo": len(combo_nodes),
                        "sav": len(sav_bands),
                    }
                ),
            }
    except Exception as exc:
        rules_meta["error"] = str(exc)
    snapshot["rules"] = rules_meta
    snapshot["fingerprint"] = _fingerprint(rules_meta)
    return snapshot


def _probe_report(ke: KnowledgeEngine) -> dict[str, Any]:
    snapshot: dict[str, Any] = {"knowledge": _safe_knowledge_snapshot(ke, "report")}
    graph_meta: dict[str, Any] = {}
    try:
        stats = snapshot["knowledge"].get("stats") or {}
        graph_meta["stats"] = stats
        graph_meta["node_count"] = stats.get("nodes") or stats.get("node_count") or 0
        graph_meta["link_count"] = stats.get("links") or stats.get("link_count") or 0
    except Exception as exc:
        graph_meta["error"] = str(exc)
    snapshot["graph"] = graph_meta
    snapshot["fingerprint"] = _fingerprint(graph_meta)
    return snapshot


def _probe_dasha(ke: KnowledgeEngine) -> dict[str, Any]:
    snapshot: dict[str, Any] = {"knowledge": _safe_knowledge_snapshot(ke, "dasha")}
    try:
        nodes = ke.query_nodes(pattern="*dasha*", limit=500)
        snapshot["domain"] = {
            "pattern": "*dasha*",
            "node_count": len(nodes),
            "sample_ids": sorted(n.get("id", "") for n in nodes[:5]),
        }
    except Exception as exc:
        snapshot["domain"] = {"error": str(exc)}
    snapshot["fingerprint"] = _fingerprint(snapshot.get("domain", {}))
    return snapshot


def _probe_yoga(ke: KnowledgeEngine) -> dict[str, Any]:
    snapshot: dict[str, Any] = {"knowledge": _safe_knowledge_snapshot(ke, "yoga")}
    try:
        nodes = ke.query_nodes(pattern="*yoga*", limit=500)
        snapshot["domain"] = {
            "pattern": "*yoga*",
            "node_count": len(nodes),
            "sample_ids": sorted(n.get("id", "") for n in nodes[:5]),
        }
    except Exception as exc:
        snapshot["domain"] = {"error": str(exc)}
    snapshot["fingerprint"] = _fingerprint(snapshot.get("domain", {}))
    return snapshot


def _probe_generic(ke: KnowledgeEngine, engine_name: str) -> dict[str, Any]:
    knowledge = _safe_knowledge_snapshot(ke, engine_name)
    snapshot = {"knowledge": knowledge, "fingerprint": _fingerprint(knowledge)}
    return snapshot


def _probe_ashtakavarga(ke: KnowledgeEngine) -> dict[str, Any]:
    snapshot: dict[str, Any] = {"knowledge": _safe_knowledge_snapshot(ke, "ashtakavarga")}
    snapshot["safe_path"] = True
    try:
        nodes = ke.query_nodes(pattern="*ashtakavarga*", limit=500)
        books: list[str] = []
        try:
            # Best-effort: check if structured books are reachable via integration
            from .integration import get_structured_book
            for bid in ("BPHS", "Ashtakavarga_System_Comprehensive_Handbook"):
                if get_structured_book(bid):
                    books.append(bid)
        except Exception:
            pass
        src = "graph" if nodes else ("mixed" if books else "hardcoded")
        snapshot["domain"] = {
            "pattern": "*ashtakavarga*",
            "node_count": len(nodes),
            "structured_books": books,
            "source": src,
        }
    except Exception as exc:
        snapshot["domain"] = {"error": str(exc), "source": "error"}
    snapshot["fingerprint"] = _fingerprint(snapshot.get("domain", {}))
    return snapshot


def _probe_panchanga(ke: KnowledgeEngine) -> dict[str, Any]:
    snapshot: dict[str, Any] = {"knowledge": _safe_knowledge_snapshot(ke, "panchanga")}
    try:
        nodes = ke.query_nodes(pattern="*panchanga*", limit=300)
        # panchanga leans on astronomy math + some structured context
        src = "graph" if len(nodes) > 5 else ("mixed" if nodes else "hardcoded")
        snapshot["domain"] = {
            "pattern": "*panchanga*",
            "node_count": len(nodes),
            "source": src,
        }
    except Exception as exc:
        snapshot["domain"] = {"error": str(exc), "source": "error"}
    snapshot["fingerprint"] = _fingerprint(snapshot.get("domain", {}))
    return snapshot


def _probe_kp(ke: KnowledgeEngine) -> dict[str, Any]:
    snapshot: dict[str, Any] = {"knowledge": _safe_knowledge_snapshot(ke, "kp_system")}
    try:
        nodes = ke.query_nodes(pattern="*kp*", limit=500)
        src = "graph" if nodes else "hardcoded"
        snapshot["domain"] = {
            "pattern": "*kp*",
            "node_count": len(nodes),
            "source": src,
        }
    except Exception as exc:
        snapshot["domain"] = {"error": str(exc), "source": "error"}
    snapshot["fingerprint"] = _fingerprint(snapshot.get("domain", {}))
    return snapshot


def _probe_prashna(ke: KnowledgeEngine) -> dict[str, Any]:
    snapshot: dict[str, Any] = {"knowledge": _safe_knowledge_snapshot(ke, "prashna")}
    try:
        nodes = ke.query_nodes(pattern="*prashna*", limit=500)
        src = "graph" if nodes else "hardcoded"
        snapshot["domain"] = {
            "pattern": "*prashna*",
            "node_count": len(nodes),
            "source": src,
        }
    except Exception as exc:
        snapshot["domain"] = {"error": str(exc), "source": "error"}
    snapshot["fingerprint"] = _fingerprint(snapshot.get("domain", {}))
    return snapshot


ENGINE_PROBES: dict[str, ProbeFn] = {
    "gochar": _probe_gochar,
    "muhurta": _probe_muhurta,
    "report": _probe_report,
    "dasha": _probe_dasha,
    "yoga": _probe_yoga,
    "ashtakavarga": _probe_ashtakavarga,
    "panchanga": _probe_panchanga,
    "kp": _probe_kp,
    "kp_system": _probe_kp,
    "prashna": _probe_prashna,
}


def _extract_metrics(snapshot: dict[str, Any]) -> dict[str, int]:
    metrics: dict[str, int] = {}
    for section in ("rules", "domain", "graph"):
        block = snapshot.get(section) or {}
        for key in (
            "entry_count",
            "node_count",
            "yoga_node_count",
            "combo_node_count",
            "sav_band_count",
            "link_count",
            "planet_count",
        ):
            value = block.get(key)
            if isinstance(value, int):
                metrics[key] = value
    return metrics


def _max_delta_ratio(before: dict[str, Any], after: dict[str, Any]) -> float:
    b_metrics = _extract_metrics(before)
    a_metrics = _extract_metrics(after)
    if not b_metrics and not a_metrics:
        return 0.0
    ratios: list[float] = []
    all_keys = set(b_metrics) | set(a_metrics)
    for key in all_keys:
        b_val = b_metrics.get(key, 0)
        a_val = a_metrics.get(key, 0)
        if b_val == 0 and a_val == 0:
            continue
        ratio = abs(a_val - b_val) / max(b_val, 1)
        ratios.append(ratio)
    return max(ratios) if ratios else 0.0


def score_refresh_impact(before: dict[str, Any], after: dict[str, Any]) -> RefreshImpact:
    if before.get("fingerprint") == after.get("fingerprint"):
        return RefreshImpact.MINIMAL
    delta = _max_delta_ratio(before, after)
    fp_changed = before.get("fingerprint") != after.get("fingerprint")
    if delta >= 0.15:
        return RefreshImpact.QUANTUM
    if delta >= 0.03 or fp_changed:
        return RefreshImpact.MODERATE
    return RefreshImpact.MINIMAL


@dataclass
class KnowledgeRefreshAuditor:
    """
    Audits the effect of a global knowledge refresh on registered engines.

    Workflow:
        auditor.capture_baseline()
        auditor.trigger_refresh()
        auditor.capture_post_refresh()
        report = auditor.compare_and_score()
    """

    engine: KnowledgeEngine
    _baseline: dict[str, dict[str, Any]] = field(default_factory=dict)
    _post_refresh: dict[str, dict[str, Any]] = field(default_factory=dict)
    _last_refresh: dict[str, Any] | None = None

    @staticmethod
    def supported_engines() -> list[str]:
        """Engine names with dedicated output probes."""
        return sorted(ENGINE_PROBES.keys())

    def _registered_targets(self) -> list[str]:
        registered = set(self.engine.registry.registered_names())
        return sorted(name for name in ENGINE_PROBES if name in registered)

    def _capture_engine(self, engine_name: str) -> dict[str, Any]:
        probe = ENGINE_PROBES.get(engine_name)
        if probe:
            return probe(self.engine)
        return _probe_generic(self.engine, engine_name)

    def capture_baseline(self) -> dict[str, dict[str, Any]]:
        """Capture pre-refresh outputs for all registered, supported engines."""
        self._baseline = {name: self._capture_engine(name) for name in self._registered_targets()}
        return self._baseline

    def trigger_refresh(self, reason: str = "audit") -> dict[str, Any]:
        """Run the global refresh cascade via KnowledgeEngine."""
        self._last_refresh = self.engine.trigger_global_refresh(reason=reason)
        return self._last_refresh

    def capture_post_refresh(self) -> dict[str, dict[str, Any]]:
        """Capture post-refresh outputs for the same engine set."""
        self._post_refresh = {
            name: self._capture_engine(name) for name in self._registered_targets()
        }
        return self._post_refresh

    def compare_and_score(self) -> dict[str, Any]:
        """
        Compare baseline vs post-refresh snapshots and score per-engine impact.

        Returns a structured audit report. Raises ValueError if captures are missing.
        """
        if not self._baseline or not self._post_refresh:
            raise ValueError("Run capture_baseline() and capture_post_refresh() before scoring.")

        engines: dict[str, Any] = {}
        impact_counts = {level.value: 0 for level in RefreshImpact}

        for name in sorted(set(self._baseline) | set(self._post_refresh)):
            before = self._baseline.get(name, {})
            after = self._post_refresh.get(name, {})
            impact = score_refresh_impact(before, after)
            impact_counts[impact.value] += 1
            engines[name] = {
                "impact": impact.value,
                "baseline_fingerprint": before.get("fingerprint"),
                "post_fingerprint": after.get("fingerprint"),
                "baseline_version": (before.get("knowledge") or {}).get("version"),
                "post_version": (after.get("knowledge") or {}).get("version"),
                "changed": before.get("fingerprint") != after.get("fingerprint"),
            }

        return {
            "status": "completed",
            "supported_engines": self.supported_engines(),
            "audited_engines": sorted(engines.keys()),
            "registered_engines": self.engine.registry.registered_names(),
            "refresh": self._last_refresh,
            "impact_summary": impact_counts,
            "engines": engines,
        }

    def run_audit(self, reason: str = "audit") -> dict[str, Any]:
        """End-to-end audit: baseline → refresh → post-capture → score."""
        self.capture_baseline()
        self.trigger_refresh(reason=reason)
        self.capture_post_refresh()
        return self.compare_and_score()


def run_all_probes(ke: KnowledgeEngine | None = None) -> dict[str, Any]:
    """Machine-readable snapshot of current probe state for all supported + registered engines.

    Returns: {"probes_run": N, "results": {name: probe_dict, ...}, "supported": [...]}
    Does not trigger refresh. Safe to call from CLI scripts.
    """
    if ke is None:
        from .integration import get_knowledge_engine
        ke = get_knowledge_engine()
    results: dict[str, Any] = {}
    supported = sorted(ENGINE_PROBES.keys())
    registered = set(ke.registry.registered_names()) if ke and ke.registry else set()
    targets = sorted(set(supported) | (registered & set(supported)))
    # Also include registered names without dedicated probes via generic
    for name in sorted(registered):
        if name not in targets:
            targets.append(name)
    for name in targets:
        probe = ENGINE_PROBES.get(name)
        try:
            if probe:
                results[name] = probe(ke)
            else:
                results[name] = _probe_generic(ke, name)
        except Exception as exc:
            results[name] = {"error": str(exc), "source": "error"}
    return {
        "probes_run": len(results),
        "supported": supported,
        "registered": sorted(registered),
        "results": results,
    }
