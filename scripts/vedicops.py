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


# Bootstrap: ensure repo root is on sys.path so "from cvce..." succeeds
# regardless of invocation (python scripts/vedicops.py vs from root).
import sys as _sys
from pathlib import Path as _Path
_REPO = _Path(__file__).resolve().parents[1]
if str(_REPO) not in _sys.path:
    _sys.path.insert(0, str(_REPO))
del _sys, _Path, _REPO

# Optional KnowledgeEngine integration (graceful if unavailable)
try:
    from cvce.knowledge_engine.integration import (
        get_knowledge_engine,
        rebuild_structured_library,
        remap_nodes_to_structured,
        rebuild_and_remap_structured,
        invalidate_nodes,
        invalidate_chapter,
        get_structured_coverage,
    )
    KE_AVAILABLE = True
except Exception:
    KE_AVAILABLE = False


REPO_ROOT = Path(__file__).resolve().parents[1]
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
# Structured Library Admin (priority #5 KE surface)
# Default to dry-run + logging. Wire to KE integration wrappers.
# ──────────────────────────────────────────────────────────────────────────────

def cmd_rebuild_structured(books: list[str] | None, all_books: bool = False, dry_run: bool = True, force: bool = False) -> dict[str, Any]:
    """Rebuild structured chapter JSONs. Dry-run by default."""
    if not KE_AVAILABLE:
        return {"status": "unavailable", "reason": "KnowledgeEngine not available"}

    target = None
    if all_books:
        target = None  # means all
    elif books:
        target = books

    if dry_run and not force:
        # Preview: call KE which will still execute scripts unless we short-circuit here
        # For safety we simulate by fetching current coverage instead of mutating
        cov = get_structured_coverage()
        return {
            "status": "dry-run",
            "action": "rebuild-structured",
            "would_target": "ALL" if target is None else target,
            "current_books": cov.get("books"),
            "current_chapters": cov.get("total_chapters"),
            "note": "Use --force to actually run build_structured_library.py",
        }

    try:
        res = rebuild_structured_library(books=target)
        LOG.info(f"rebuild-structured: {res.get('status')}")
        return {"status": "executed", "result": res}
    except Exception as e:
        LOG.error(f"rebuild-structured failed: {e}")
        return {"status": "error", "reason": str(e)}


def cmd_remap_book(book: str | None, use_supabase: bool = False, dry_run: bool = True, force: bool = False) -> dict[str, Any]:
    """Remap nodes to chapters for one or more books. Dry-run by default."""
    if not KE_AVAILABLE:
        return {"status": "unavailable", "reason": "KnowledgeEngine not available"}

    # Determine target books
    targets: list[str] | None = None
    if book:
        targets = [b.strip() for b in book.split(",") if b.strip()]

    if dry_run and not force:
        cov = get_structured_coverage()
        return {
            "status": "dry-run",
            "action": "remap-book",
            "would_target": targets or "ALL (from structured dir)",
            "patch_present": cov.get("patch", {}).get("present"),
            "patch_entries": cov.get("patch", {}).get("entries"),
            "note": "Use --force to actually run map_nodes_to_structured.py",
        }

    # For actual run we pass through; the underlying script accepts --dry-run but we already handled preview
    try:
        # Temporarily set env for supabase if requested (the wrapper checks env)
        import os
        prev = os.environ.get("SUPABASE_URL")
        if use_supabase and not prev:
            # best-effort: if portal/.env.local has it, the script inside will pick it; here we just hint
            LOG.info("remap-book: --supabase requested (ensure SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY in env)")
        res = remap_nodes_to_structured(books=targets)
        LOG.info(f"remap-book: {res.get('status')}")
        return {"status": "executed", "result": res}
    except Exception as e:
        LOG.error(f"remap-book failed: {e}")
        return {"status": "error", "reason": str(e)}


def cmd_show_structured_coverage(json_out: bool = False) -> dict[str, Any]:
    """Show snapshot of structured library coverage."""
    if not KE_AVAILABLE:
        res = {"status": "unavailable", "reason": "KnowledgeEngine not available"}
        if json_out:
            print(json.dumps(res, indent=2))
        else:
            print(res)
        return res

    try:
        cov = get_structured_coverage()
        out = {
            "status": "ok",
            "books": cov.get("books"),
            "total_chapters": cov.get("total_chapters"),
            "total_patched_nodes": cov.get("total_patched_nodes"),
            "patch": cov.get("patch"),
        }
        if json_out:
            print(json.dumps({**out, "sample_books": [b["book_id"] for b in cov.get("books_detail", [])][:10]}, indent=2))
        else:
            print("Structured Coverage")
            print(f"  books: {out['books']}")
            print(f"  total_chapters: {out['total_chapters']}")
            print(f"  total_patched_nodes: {out['total_patched_nodes']}")
            print(f"  patch_present: {out['patch'].get('present')}")
            print(f"  patch_entries: {out['patch'].get('entries')}")
            print(f"  patch_books_covered: {out['patch'].get('books_covered')}")
            # also emit a compact one-liner for scripts
            print(f"OK books={out['books']} chapters={out['total_chapters']} patched_nodes={out['total_patched_nodes']}")
        return out
    except Exception as e:
        LOG.error(f"show-structured-coverage failed: {e}")
        err = {"status": "error", "reason": str(e)}
        print(err)
        return err


def cmd_invalidate_chapter(book: str, chapter_id: str, dry_run: bool = True, force: bool = False, reason: str = "manual") -> dict[str, Any]:
    """Invalidate all KE nodes mapped to a given chapter. Dry-run by default."""
    if not KE_AVAILABLE:
        return {"status": "unavailable", "reason": "KnowledgeEngine not available"}

    if dry_run and not force:
        try:
            nodes = []  # preview via integration
            # Use direct get_nodes_for_chapter through the ke
            from cvce.knowledge_engine.integration import get_knowledge_engine
            ke = get_knowledge_engine()
            nodes = ke.get_nodes_for_chapter(book, chapter_id)
            nids = [n.get("id") for n in nodes if isinstance(n, dict) and n.get("id")]
            return {
                "status": "dry-run",
                "action": "invalidate-chapter",
                "book": book,
                "chapter_id": chapter_id,
                "nodes_that_would_be_invalidated": len(nids),
                "sample_node_ids": nids[:5],
                "note": "Use --force to actually call ke.invalidate()",
            }
        except Exception as e:
            return {"status": "dry-run-error", "reason": str(e)}

    try:
        res = invalidate_chapter(book_id=book, chapter_id=chapter_id, reason=reason, details=f"vedicops invalidate-chapter {book} {chapter_id}")
        LOG.info(f"invalidate-chapter: targeted={res.get('nodes_targeted')} invalidated={len(res.get('invalidated', []))}")
        return {"status": "executed", "result": res}
    except Exception as e:
        LOG.error(f"invalidate-chapter failed: {e}")
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

    # Structured admin (priority #5 KE surface) — default dry-run + logging
    p_struct = sub.add_parser("structured", help="Structured library admin commands (rebuild/remap/coverage/invalidate)")
    struct_sub = p_struct.add_subparsers(dest="struct_cmd")

    p_rs = struct_sub.add_parser("rebuild-structured", help="Rebuild structured chapter JSONs from raw sources")
    p_rs.add_argument("books", nargs="*", help="Specific book ids (or omit with --all)")
    p_rs.add_argument("--all", action="store_true", help="Target all books")
    p_rs.add_argument("--dry-run", action="store_true", default=True, help="Preview only (default)")
    p_rs.add_argument("--force", action="store_true", help="Actually execute the rebuild")

    p_rm = struct_sub.add_parser("remap-book", help="Remap KE nodes to structured chapters")
    p_rm.add_argument("book", nargs="?", help="Book id or comma list (omit for auto-discover)")
    p_rm.add_argument("--supabase", action="store_true", help="Prefer Supabase node source")
    p_rm.add_argument("--dry-run", action="store_true", default=True, help="Preview only (default)")
    p_rm.add_argument("--force", action="store_true", help="Actually execute the remap")

    struct_sub.add_parser("show-coverage", help="Show structured library coverage snapshot")

    p_inv = struct_sub.add_parser("invalidate-chapter", help="Invalidate all nodes mapped to a chapter (use with care)")
    p_inv.add_argument("book", help="Book id")
    p_inv.add_argument("chapter_id", help="Chapter id (e.g. ch-01)")
    p_inv.add_argument("--dry-run", action="store_true", default=True, help="Preview only (default)")
    p_inv.add_argument("--force", action="store_true", help="Actually perform invalidation")
    p_inv.add_argument("--reason", default="manual", help="Invalidation reason (manual|stale|conflict|...)")

    args = parser.parse_args()

    # Initialize logging for ad-hoc CLI commands (run sets its own)
    if args.cmd != "run":
        setup_logging(quiet=False)

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
    elif args.cmd == "structured":
        if args.struct_cmd == "rebuild-structured":
            books = args.books if args.books else None
            print(cmd_rebuild_structured(books=books, all_books=args.all, dry_run=args.dry_run, force=args.force))
        elif args.struct_cmd == "remap-book":
            print(cmd_remap_book(book=args.book, use_supabase=args.supabase, dry_run=args.dry_run, force=args.force))
        elif args.struct_cmd == "show-coverage":
            cmd_show_structured_coverage(json_out=False)
        elif args.struct_cmd == "invalidate-chapter":
            print(cmd_invalidate_chapter(book=args.book, chapter_id=args.chapter_id, dry_run=args.dry_run, force=args.force, reason=args.reason))
        else:
            p_struct.print_help()
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
