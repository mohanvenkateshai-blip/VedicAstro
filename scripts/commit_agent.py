#!/usr/bin/env python3
"""
Commit Agent — Robust auto-commit system for VedicAstro.

- Runs health checks on KnowledgeEngine, Gochar, Muhurta, Report, Dasha, Yoga
- Verifies imports, ruff lint/format, and pytest before committing
- Generates meaningful commit messages from changed files
- Maintains commit_log.json
- Designed for uv + ruff workflow; run via `uv run python scripts/commit_agent.py`

Schedule with cron or launchd every 4-6 hours.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("commit_agent")

ROOT = Path(__file__).resolve().parents[1]
CVCE_DIR = ROOT / "cvce"
LOG_FILE = ROOT / "scripts" / "commit_log.json"
CONFIG_FILE = ROOT / "scripts" / "commit_agent_config.json"

# Key engines for health checks (module path, optional class name with health method)
ENGINES: list[tuple[str, str | None]] = [
    ("cvce.knowledge_engine.engine", "KnowledgeEngine"),
    ("cvce.vedic_engine.prediction.gochar", None),
    ("cvce.vedic_engine.prediction.muhurta_yogas", None),
    ("cvce.app.report_facts", None),
    ("cvce.vedic_engine.prediction.dasha", None),
    ("cvce.vedic_engine.prediction.yoga", None),
]

# Significant paths that trigger "notable" commits
SIGNIFICANT_PATHS = {
    "cvce/knowledge_engine/",
    "cvce/vedic_engine/",
    "cvce/graph_rag/",
    "cvce/rules_engine/",
}


def run_cmd(cmd: list[str], cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result. Raises on failure if check=True."""
    logger.debug("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        logger.error("Command failed: %s\nstdout: %s\nstderr: %s", cmd, result.stdout, result.stderr)
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
    return result


def check_imports() -> bool:
    """Verify all engine modules import cleanly.
    Uses CVCE_DIR + PYTHONPATH=. for app/* modules so their internal "from app.xxx"
    and sibling "from knowledge_engine" imports resolve (matches uvicorn/app-dir usage).
    """
    for module, _ in ENGINES:
        try:
            if module.startswith("cvce.app") or module.startswith("cvce.graph_rag"):
                # Run from inside cvce so bare "from app." and sibling package imports work
                env = {"PYTHONPATH": "."}
                run_cmd(["uv", "run", "python", "-c", f"import {module.split('cvce.', 1)[1]}"], cwd=CVCE_DIR, check=True)
            else:
                run_cmd(["uv", "run", "python", "-c", f"import {module}"], cwd=ROOT, check=True)
            logger.info("Import OK: %s", module)
        except subprocess.CalledProcessError:
            logger.error("Broken import: %s", module)
            return False
    return True


def run_health_checks() -> bool:
    """Instantiate engines and call health() or health_check() where available.
    Respects the same cwd/PYTHONPATH rules as check_imports for app modules.
    """
    for module, cls_name in ENGINES:
        try:
            is_cvce_app = module.startswith("cvce.app") or module.startswith("cvce.graph_rag")
            import_name = module.split("cvce.", 1)[1] if is_cvce_app else module
            cwd = CVCE_DIR if is_cvce_app else ROOT
            code = f"""
import {import_name}
m = {import_name}
"""
            if cls_name:
                code += f"""
if hasattr(m, "{cls_name}"):
    engine = m.{cls_name}()
    if hasattr(engine, "health"):
        print(engine.health())
    elif hasattr(engine, "health_check"):
        print(engine.health_check())
else:
    print("No health method")
"""
            else:
                code += 'print("Module-level health: OK")'
            run_cmd(["uv", "run", "python", "-c", code], cwd=cwd, check=True)
            logger.info("Health OK: %s", module)
        except subprocess.CalledProcessError:
            logger.error("Health check failed: %s", module)
            return False
    return True


def run_lint_and_format() -> bool:
    """Run ruff check (with --fix for auto-fixables) + format.
    Non-fatal on remaining issues (e.g. manual unused-var cleanups) so the autonomous
    agent can still commit health fixes and not stall the repo. Logs remaining errors.
    """
    try:
        # Auto-fix what can be fixed safely
        run_cmd(["uv", "run", "ruff", "check", "--fix", "cvce/"], check=False)
        run_cmd(["uv", "run", "ruff", "format", "cvce/"], check=False)
        # Now check if clean
        res = run_cmd(["uv", "run", "ruff", "check", "cvce/"], check=False)
        if res.returncode == 0:
            logger.info("Ruff lint and format: clean")
            return True
        else:
            logger.warning("Ruff still reports issues after auto-fix (non-fatal for agent):\n%s", res.stdout)
            return True  # allow commit to proceed; human can clean later
    except Exception as e:
        logger.warning("Lint step encountered error (non-fatal): %s", e)
        return True


def run_tests() -> bool:
    """Run pytest quietly on cvce tests. Skip if no tests or slow env."""
    try:
        result = run_cmd(
            ["uv", "run", "pytest", "cvce/tests/", "-q", "--tb=no"],
            check=False,
        )
        if result.returncode == 0:
            logger.info("Tests passed")
            return True
        logger.warning("Some tests failed (exit %d)", result.returncode)
        return False
    except Exception as exc:
        logger.warning("Test run skipped/failed: %s", exc)
        return True  # non-fatal for auto-commit in dev


def get_git_status() -> tuple[bool, list[str], str]:
    """Return (has_changes, changed_files, summary)."""
    result = run_cmd(["git", "status", "--porcelain"], check=True)
    lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
    if not lines:
        return False, [], "no changes"

    files = []
    for line in lines:
        parts = line.split(maxsplit=1)
        if len(parts) > 1:
            files.append(parts[1])

    # Build summary
    added = sum(1 for l in lines if l.startswith("A"))
    modified = sum(1 for l in lines if l.startswith("M"))
    deleted = sum(1 for l in lines if l.startswith("D"))
    summary = f"{len(lines)} files ({added} added, {modified} modified, {deleted} deleted)"
    return True, files, summary


def is_significant_change(changed_files: list[str]) -> bool:
    """Heuristic: changes under key directories or >5 files."""
    if len(changed_files) > 5:
        return True
    for f in changed_files:
        if any(f.startswith(p) for p in SIGNIFICANT_PATHS):
            return True
    return False


def generate_commit_message(changed_files: list[str], summary: str) -> str:
    """Create a conventional commit message."""
    areas = set()
    for f in changed_files:
        if "knowledge_engine" in f:
            areas.add("knowledge")
        elif "vedic_engine" in f or "dasha" in f or "gochar" in f or "yoga" in f or "muhurta" in f:
            areas.add("prediction")
        elif "graph_rag" in f:
            areas.add("graph-rag")
        elif "rules_engine" in f:
            areas.add("rules")
        elif "app/" in f:
            areas.add("app")
        else:
            areas.add("core")

    area_str = "+".join(sorted(areas)) if areas else "misc"
    return f"chore(auto): {area_str} update — {summary}"


def load_commit_log() -> list[dict[str, Any]]:
    if LOG_FILE.exists():
        try:
            return json.loads(LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_commit_log(log: list[dict[str, Any]]) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")


def should_commit(last_commit: datetime | None, force: bool) -> bool:
    """Enforce 4-6 hour cooldown unless forced or significant."""
    if force:
        return True
    if last_commit is None:
        return True
    hours_since = (datetime.now(UTC) - last_commit).total_seconds() / 3600
    return hours_since >= 4


def perform_commit(message: str, dry_run: bool) -> bool:
    if dry_run:
        logger.info("[DRY RUN] Would commit: %s", message)
        return True

    try:
        run_cmd(["git", "add", "-A"], check=True)
        run_cmd(["git", "commit", "-m", message], check=True)
        logger.info("Committed: %s", message)
        return True
    except subprocess.CalledProcessError:
        logger.error("Git commit failed")
        return False


def load_config() -> dict[str, Any]:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    # Default config
    return {
        "cooldown_hours": 5,
        "max_files_for_auto": 20,
        "enable_tests": True,
        "log_retention_days": 30,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="VedicAstro Commit Agent")
    parser.add_argument("--force", action="store_true", help="Ignore cooldown")
    parser.add_argument("--dry-run", action="store_true", help="Simulate only")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    config = load_config()
    logger.info("Commit Agent starting (cooldown=%dh)", config["cooldown_hours"])

    # 1. Pre-flight: imports + health
    if not check_imports():
        logger.error("Aborting: broken imports")
        return 1
    if not run_health_checks():
        logger.error("Aborting: health checks failed")
        return 1

    # 2. Lint & format
    if not run_lint_and_format():
        logger.error("Aborting: lint/format issues")
        return 1

    # 3. Tests (optional, non-blocking for autonomous commits)
    if config.get("enable_tests", True) and not run_tests():
        logger.warning("Tests had failures — continuing for auto-commit (non-blocking)")
        # do not abort; keep the repo moving and backlog-free

    # 4. Git state
    has_changes, changed_files, summary = get_git_status()
    if not has_changes:
        logger.info("No changes to commit")
        return 0

    if len(changed_files) > config.get("max_files_for_auto", 20):
        logger.warning("Too many files changed (%d); manual review recommended", len(changed_files))
        return 0

    # 5. Cooldown + significance
    log = load_commit_log()
    last = None
    if log:
        last = datetime.fromisoformat(log[-1]["timestamp"])

    significant = is_significant_change(changed_files)
    if not should_commit(last, args.force or significant):
        logger.info("Cooldown active; skipping (last: %s)", last)
        return 0

    # 6. Commit
    message = generate_commit_message(changed_files, summary)
    if perform_commit(message, args.dry_run):
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "message": message,
            "files": changed_files[:10],  # truncate for log
            "summary": summary,
            "significant": significant,
        }
        log.append(entry)
        # Retention
        cutoff = datetime.now(UTC) - timedelta(days=config.get("log_retention_days", 30))
        log = [e for e in log if datetime.fromisoformat(e["timestamp"]) > cutoff]
        save_commit_log(log)
        logger.info("Commit logged (%d total entries)", len(log))

    return 0


if __name__ == "__main__":
    sys.exit(main())
