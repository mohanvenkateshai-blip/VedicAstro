"""Tests for KnowledgeRefreshAuditor."""

from unittest.mock import MagicMock

from knowledge_engine.refresh_auditor import (
    KnowledgeRefreshAuditor,
    RefreshImpact,
    score_refresh_impact,
)


def test_supported_engines():
    assert KnowledgeRefreshAuditor.supported_engines() == [
        "dasha",
        "gochar",
        "muhurta",
        "report",
        "yoga",
    ]


def test_score_impact_levels():
    unchanged = {"fingerprint": "abc", "rules": {"entry_count": 100}}
    assert score_refresh_impact(unchanged, dict(unchanged)) == RefreshImpact.MINIMAL

    moderate = {"fingerprint": "def", "rules": {"entry_count": 105}}
    assert score_refresh_impact(unchanged, moderate) == RefreshImpact.MODERATE

    quantum = {"fingerprint": "ghi", "rules": {"entry_count": 150}}
    assert score_refresh_impact(unchanged, quantum) == RefreshImpact.QUANTUM


def _mock_engine() -> MagicMock:
    ke = MagicMock()
    ke.registry.registered_names.return_value = ["gochar", "report"]
    ke.trigger_global_refresh.return_value = {
        "status": "triggered",
        "version": "test-v1",
        "engines_notified": ["gochar", "report"],
    }
    ke.get_safe_knowledge.return_value = {
        "version": "test-v1",
        "stats": {"nodes": 100, "links": 200},
        "invalidation_count": 0,
    }
    ke.get_safe_rules.return_value = None
    ke.query_nodes.return_value = []
    return ke


def test_run_audit_with_registered_engines():
    auditor = KnowledgeRefreshAuditor(engine=_mock_engine())
    report = auditor.run_audit(reason="test")

    assert report["status"] == "completed"
    assert set(report["audited_engines"]) == {"gochar", "report"}
    assert report["impact_summary"]["minimal"] == 2
    assert report["refresh"]["status"] == "triggered"


def test_compare_requires_captures():
    auditor = KnowledgeRefreshAuditor(engine=_mock_engine())
    try:
        auditor.compare_and_score()
        raised = False
    except ValueError:
        raised = True
    assert raised
