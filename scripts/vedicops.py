#!/usr/bin/env python3
"""
VedicOps — Master orchestrator for VedicAstro maintenance.

Run the full VedicOps system:
- Commit Agent (smart git commits)
- Performance Monitor (health + timing checks)
- Context & Handoff docs updater
- Global Knowledge refresh (via KnowledgeEngine)

Usage (CLI):
  python scripts/vedicops.py --help
  python scripts/vedicops.py run --all
  python scripts/vedicops.py refresh --reason "post-ingest"
  python scripts/vedicops.py monitor --json

Cron example (every 6h):
  0 */6 * * * cd /path/to/VedicAstro && python scripts/vedicops.py run --all --quiet >> /var/log/vedicops.log 2>&1

Requires: Python 3.10+, git in PATH. KnowledgeEngine optional (falls back gracefully).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

# Optional KnowledgeEngine integration (graceful if unavailable)
try:
    from cvce.knowledge_engine.integration import get_knowledge_engine
    KE_AVAILABLE = True
except Exception:
    KE_AVAILABLE = False

REPO_ROOT = Path(__file__).resolve().parents[2]
LOG = logging.getLogger("vedicops")


def setup_logging(quiet: bool = False) -> None:
    level = logging.WARNING if quiet else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Commit Agent
# ──────────────────────────────────────────────────────────────────────────────

def run_commit_agent(dry_run: bool = False) -> dict[str, Any]:
    """Trigger Commit Agent: stage changes, create conventional commit."""
    result: dict[str, Any] = {"action": "commit", "status": "skipped", "reason": None}

    try:
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO_ROOT, text=True).strip()
        if not status:
            result["reason"] = "no changes"
            return result

        if dry_run:
            result.update({"status": "dry-run", "changes": status.splitlines()})
            return result

        # Simple conventional commit heuristic
        if any("knowledge" in f.lower() or "graph" in f.lower() for f in status.splitlines()):
            msg = "chore(knowledge): update graph and refresh artifacts"
        elif any("doc" in f.lower() or "handoff" in f.lower() for f in status.splitlines()):
            msg = "docs: update context and handoff"
        else:
            msg = "chore: maintenance run via VedicOps"

        subprocess.check_call(["git", "add", "-A"], cwd=REPO_ROOT)
        subprocess.check_call(["git", "commit", "-m", msg], cwd=REPO_ROOT)
        result.update({"status": "committed", "message": msg})
    except subprocess.CalledProcessError as e:
        result.update({"status": "error", "reason": str(e)})
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Performance Monitor
# ──────────────────────────────────────────────────────────────────────────────

def run_performance_monitor(json_out: bool = False) -> dict[str, Any]:
    """Run lightweight performance + health monitor."""
    monitor: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "repo": str(REPO_ROOT),
        "checks": {},
    }

    # Git stats
    try:
        commits = subprocess.check_output(["git", "rev-list", "--count", "HEAD"], cwd=REPO_ROOT, text=True).strip()
        monitor["checks"]["git_commits"] = int(commits)
    except Exception as e:
        monitor["checks"]["git_commits"] = f"error: {e}"

    # Knowledge health (if available)
    if KE_AVAILABLE:
        try:
            ke = get_knowledge_engine()
            monitor["checks"]["knowledge_engine"] = ke.health()
        except Exception as e:
            monitor["checks"]["knowledge_engine"] = f"error: {e}"
    else:
        monitor["checks"]["knowledge_engine"] = "unavailable (import failed)"

    # Simple disk usage
    try:
        du = subprocess.check_output(["du", "-sh", "."], cwd=REPO_ROOT, text=True).strip().split()[0]
        monitor["checks"]["disk_usage"] = du
    except Exception:
        pass

    if json_out:
        print(json.dumps(monitor, indent=2))
    else:
        LOG.info("Performance Monitor Report")
        for k, v in monitor["checks"].items():
            LOG.info(f"  {k}: {v}")
    return monitor


# ──────────────────────────────────────────────────────────────────────────────
# Context & Handoff Docs Updater
# ──────────────────────────────────────────────────────────────────────────────

def update_context_handoff(dry_run: bool = False) -> dict[str, Any]:
    """Update Context & Handoff docs (timestamp + basic stats injection)."""
    result = {"action": "update-docs", "files": []}
    handoff = REPO_ROOT / "docs/archive/HANDOFF.md"
    if not handoff.exists():
        result["status"] = "skipped"
        result["reason"] = "no HANDOFF.md"
        return result

    if dry_run:
        result.update({"status": "dry-run", "would_update": str(handoff)})
        return result

    content = handoff.read_text(encoding="utf-8")
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    # Simple replacement for date line
    if "**Date:**" in content:
        new_content = content.replace(
            content.split("**Date:**")[1].split("\n")[0].strip(),
            today,
        )
    else:
        new_content = f"**Date:** {today}\n" + content

    # Append a VedicOps run note if missing
    if "VedicOps run" not in new_content:
        new_content += f"\n\n---\n*Last VedicOps maintenance: {datetime.now(UTC).isoformat()}*\n"

    handoff.write_text(new_content, encoding="utf-8")
    result.update({"status": "updated", "files": [str(handoff)]})
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Global Knowledge Refresh
# ──────────────────────────────────────────────────────────────────────────────

def trigger_knowledge_refresh(reason: str = "vedicops") -> dict[str, Any]:
    """Trigger global Knowledge refresh when needed."""
    if not KE_AVAILABLE:
        return {"status": "unavailable", "reason": "KnowledgeEngine import failed"}

    try:
        ke = get_knowledge_engine()
        res = ke.trigger_global_refresh(reason=reason)
        LOG.info(f"Knowledge refresh triggered: {res}")
        return {"status": "success", **res}
    except Exception as e:
        LOG.error(f"Refresh failed: {e}")
        return {"status": "error", "reason": str(e)}


# ──────────────────────────────────────────────────────────────────────────────
# Main Orchestrator
# ──────────────────────────────────────────────────────────────────────────────

def run_full_ops(dry_run: bool = False, quiet: bool = False, refresh: bool = True) -> None:
    """Run the complete VedicOps pipeline."""
    setup_logging(quiet)
    LOG.info("=== VedicOps Master Run Started ===")

    commit_res = run_commit_agent(dry_run=dry_run)
    LOG.info(f"Commit Agent: {commit_res['status']}")

    monitor_res = run_performance_monitor(json_out=False)
    LOG.info("Performance Monitor: complete")

    docs_res = update_context_handoff(dry_run=dry_run)
    LOG.info(f"Docs Update: {docs_res.get('status', 'done')}")

    if refresh:
        refresh_res = trigger_knowledge_refresh(reason="vedicops-full-run")
        LOG.info(f"Knowledge Refresh: {refresh_res.get('status')}")

    LOG.info("=== VedicOps Master Run Complete ===")


def main() -> None:
    parser = argparse.ArgumentParser(description="VedicOps master orchestrator")
    sub = parser.add_subparsers(dest="cmd")

    # Full run
    p_run = sub.add_parser("run", help="Execute full VedicOps pipeline")
    p_run.add_argument("--all", action="store_true", help="Run every component")
    p_run.add_argument("--dry-run", action="store_true")
    p_run.add_argument("--quiet", action="store_true")
    p_run.add_argument("--no-refresh", action="store_true", help="Skip knowledge refresh")

    # Individual
    sub.add_parser("commit", help="Trigger Commit Agent only")
    sub.add_parser("monitor", help="Run Performance Monitor").add_argument("--json", action="store_true")
    sub.add_parser("update-docs", help="Update Context & Handoff docs")
    p_refresh = sub.add_parser("refresh", help="Trigger global Knowledge refresh")
    p_refresh.add_argument("--reason", default="manual", help="Reason for refresh")

    args = parser.parse_args()

    if args.cmd == "run":
        run_full_ops(dry_run=args.dry_run, quiet=args.quiet, refresh=not args.no_refresh)
    elif args.cmd == "commit":
        print(run_commit_agent(dry_run=False))
    elif args.cmd == "monitor":
        run_performance_monitor(json_out=args.json)
    elif args.cmd == "update-docs":
        print(update_context_handoff(dry_run=False))
    elif args.cmd == "refresh":
        print(trigger_knowledge_refresh(reason=args.reason))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
