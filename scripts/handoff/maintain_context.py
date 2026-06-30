#!/usr/bin/env python3
"""
VedicAstro Handoff Documentation Maintainer

Detects significant changes (new engines, KG version bump, major features)
and automatically refreshes:
- CONTEXT.md (engines table, KG stats, health)
- docs/handoff/AI_TAKEOVER_PACK.md (clean, self-contained handoff artifact)

Usage:
  python scripts/handoff/maintain_context.py --update-all
  python scripts/handoff/maintain_context.py --generate-pack-only

Run after any ingestion (`merge --promote`) or engine registration change.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

# Ensure we can import from cvce/ when run from repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
CVCE_DIR = REPO_ROOT / "cvce"
if str(CVCE_DIR) not in sys.path:
    sys.path.insert(0, str(CVCE_DIR))

from knowledge_engine.integration import get_knowledge_engine  # type: ignore
from knowledge_engine.refresh_auditor import KnowledgeRefreshAuditor  # type: ignore


MARKER_BEGIN = "<!-- BEGIN AUTO {section} -->"
MARKER_END = "<!-- END AUTO {section} -->"


def get_current_state() -> dict[str, Any]:
    """Introspect live KnowledgeEngine + registry + graph stats."""
    ke = get_knowledge_engine()
    auditor = KnowledgeRefreshAuditor(ke)
    registered = ke.registry.registered_names()

    # Safe stats (works for both Supabase and file store)
    try:
        stats = ke.store.get_stats()
    except Exception:
        stats = {"node_count": 0, "link_count": 0}

    version = getattr(ke.current_version, "version", "unknown")
    node_count = stats.get("node_count", stats.get("nodes", 0))
    link_count = stats.get("link_count", stats.get("links", 0))

    # Registered engines with probe hints
    engines = []
    for name in sorted(registered):
        probe = "supported" if name in KnowledgeRefreshAuditor.supported_engines() else "generic"
        engines.append({"name": name, "probe": probe})

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "graph_version": version,
        "node_count": node_count,
        "link_count": link_count,
        "registered_engines": engines,
        "registered_names": registered,
        "health": "Healthy" if ke.store.health_check() else "Degraded",
    }


def build_engines_table(state: dict[str, Any]) -> str:
    """Generate markdown table for CONTEXT.md section 8."""
    lines = [
        "| Engine | File (representative) | Purpose | Last KG Feed | Status |",
        "|--------|-----------------------|---------|--------------|--------|",
    ]
    for eng in state["registered_engines"]:
        name = eng["name"]
        # Heuristic file mapping (extend as new engines appear)
        file_map = {
            "gochar": "graph_rag/rules_provider.py",
            "muhurta": "graph_rag/muhurta_rules_provider.py",
            "report": "graph_rag/enhancer.py",
            "dasha": "vedic_engine/prediction/dasha.py",
            "yoga": "vedic_engine/prediction/yoga.py",
        }
        file = file_map.get(name, "knowledge_engine/integration.py (via register)")
        purpose = {
            "gochar": "Transit rules + GPD consensus",
            "muhurta": "Activity-level muhurta verdicts",
            "report": "Citation injection + GraphRAG",
            "dasha": "Vimshottari / Yogini / Kaksha",
            "yoga": "Natal + Muhurta yogas",
        }.get(name, "Registered consumer of Knowledge Graph")
        last = f"{state['timestamp'][:10]} ({state['node_count']:,} nodes)"
        status = "Live (auto-refresh)"
        lines.append(f"| {name.title()} | `{file}` | {purpose} | {last} | {status} |")
    return "\n".join(lines)


def update_context_md(state: dict[str, Any], dry_run: bool = False) -> bool:
    """Replace auto-generated sections in CONTEXT.md using markers."""
    context_path = REPO_ROOT / "CONTEXT.md"
    if not context_path.exists():
        print("ERROR: CONTEXT.md not found")
        return False

    content = context_path.read_text(encoding="utf-8")

    # Section 6: KG stats (simple replace of the production line)
    kg_line = (
        f"**Production graph: {state['node_count']:,} nodes / "
        f"{state['link_count']:,} links** (version `{state['graph_version']}`)"
    )
    content = re.sub(
        r"\*\*Production graph:.*nodes.*links.*\*\*",
        kg_line,
        content,
    )

    # Section 8: Engines table
    engines_md = build_engines_table(state)
    begin = MARKER_BEGIN.format(section="ENGINES")
    end = MARKER_END.format(section="ENGINES")
    pattern = re.compile(rf"{re.escape(begin)}.*?{re.escape(end)}", re.DOTALL)
    replacement = f"{begin}\n{engines_md}\n{end}"
    if pattern.search(content):
        content = pattern.sub(replacement, content)
    else:
        # First run: insert after the header line of section 8
        header = "## 8. Engines — Status & Last Knowledge-Graph Feed"
        if header in content:
            idx = content.find(header) + len(header)
            content = content[:idx] + f"\n\n{begin}\n{engines_md}\n{end}" + content[idx:]

    # Section 6 health note
    health_note = f"**KnowledgeEngine Health:** {state['health']}"
    content = re.sub(r"\*\*KnowledgeEngine Health:\*\* .*", health_note, content)

    if dry_run:
        print("DRY RUN — would write updated CONTEXT.md")
        return True

    context_path.write_text(content, encoding="utf-8")
    print(f"Updated CONTEXT.md (engines: {len(state['registered_names'])}, nodes: {state['node_count']})")
    return True


def generate_takeover_pack(state: dict[str, Any], dry_run: bool = False) -> Path:
    """Generate the clean, self-contained AI Takeover Pack."""
    pack_path = REPO_ROOT / "docs/handoff/AI_TAKEOVER_PACK.md"
    pack_dir = pack_path.parent
    pack_dir.mkdir(parents=True, exist_ok=True)

    engines_list = "\n".join(
        f"- **{e['name'].title()}** — {e['probe']} probe, registered for on_refresh cascade"
        for e in state["registered_engines"]
    )

    content = f"""# VedicAstro — AI Takeover Pack

**Generated:** {state['timestamp']}  
**Graph Version:** `{state['graph_version']}`  
**Nodes / Links:** {state['node_count']:,} / {state['link_count']:,}  
**Registered Engines:** {len(state['registered_names'])}  
**KnowledgeEngine Health:** {state['health']}

---

**🚨 MANDATORY MULTI-AGENT PROTOCOL (ALWAYS APPLY)**  
**NEVER start substantial work with fewer than 5 parallel agents.** Use `Task` multiple times in the opening response to launch ≥5 specialized sub-agents. One of the first 5 **MUST** be a Multi-Agent Compliance/Reminder/Orchestrator.  
**Rule file (permanent):** `.cursor/rules/multi-agent-mandatory-protocol.mdc` (alwaysApply: true)  
See `docs/MULTI_AGENT_MANDATORY_RULE.md` and `docs/agents-launched.log`. Scale to 8–12 normally or 15–30+ for large tasks. Sequential execution violates project protocol.

---

## 0. Multi-Agent Health (for this snapshot)

| Aspect                    | Status                              | Evidence |
|---------------------------|-------------------------------------|----------|
| Protocol Rule             | Active (alwaysApply)                | `.cursor/rules/multi-agent-mandatory-protocol.mdc` |
| Minimum Agents            | 5+ in parallel, first response      | `Task` tool; orchestrator required in wave 1 |
| Handoff References        | Required in all major status files  | CONTEXT.md, STATUS.md, knowledge-engine-status.md, KNOWLEDGE_CATALOG.md, this pack |
| Maintainer Obligation     | This script must surface the rule   | Future generations of this pack + CONTEXT auto-sections cite the protocol |
| Last Launch Record        | See `docs/agents-launched.log`      | Records sessions that started with 6+ agents (scaling beyond baseline) |

---

## 1. One-Sentence Summary
VedicAstro is a FastAPI (CVCE) + Next.js (Portal) system with a central **KnowledgeEngine** that owns the Vedic Knowledge Graph (Supabase + graph.json) and cascades refreshes to all registered prediction engines.

## 2. Current Live State
- Graph: `{state['graph_version']}` ({state['node_count']:,} nodes)
- Engines registered: {', '.join(state['registered_names']) or 'none'}
- Primary store: Supabase (with file fallback)
- Refresh mechanism: `POST /knowledge/refresh` or `ke.trigger_global_refresh()`

## 3. Registered Engines (auto-refreshed on KG change)
{engines_list}

## 4. How to Trigger a Full Refresh (from any AI / CLI)
```bash
# Via API (production)
curl -X POST https://vedicastro-cvce.fly.dev/knowledge/refresh

# Via Python (local / dev)
cd cvce
.venv/bin/python -c "
from knowledge_engine.integration import get_knowledge_engine
ke = get_knowledge_engine()
print(ke.trigger_global_refresh(reason='handoff-audit'))
"
```

After refresh, run the maintainer:
```bash
python scripts/handoff/maintain_context.py --update-all
```

## 5. Pending / Next Natural Items (from CONTEXT.md §9)
1. Populate vector embeddings on `corpus_chunks`
2. Expand engine registration (Dasha extras, more dashas, Panchanga)
3. Admin UI for manual invalidation + refresh
4. Background revival cron (every 6–12h)

## 6. Critical Files for Any New AI
- `.cursor/rules/multi-agent-mandatory-protocol.mdc` — **MANDATORY: always launch ≥5 agents in parallel at start of work (alwaysApply: true)**
- `docs/MULTI_AGENT_MANDATORY_RULE.md` — human codex + enforcement notes for the protocol
- `CONTEXT.md` (root) — immutable guardrails + topology + Multi-Agent Health
- `STATUS.md` — live status + Multi-Agent Health section
- `docs/knowledge-engine-status.md` — KE status report + Multi-Agent Health
- `knowledge-graph/KNOWLEDGE_CATALOG.md` — texts + Multi-Agent Health
- `docs/handoff/AI_TAKEOVER_PACK.md` — this handoff pack (always declares the rule)
- `cvce/knowledge_engine/engine.py` + `registry.py` — core implementation
- `cvce/knowledge_engine/refresh_auditor.py` — impact scoring after refresh
- `scripts/handoff/maintain_context.py` — this script (keeps docs fresh; bakes protocol refs into snapshots)

## 7. Verification Checklist (run before any change)
```bash
curl https://vedicastro-cvce.fly.dev/health
cd cvce && .venv/bin/python -m pytest tests/golden/ -q
python scripts/handoff/maintain_context.py --dry-run
```

**This pack + the three docs/ files above are sufficient for any new AI to take over without reading 200+ source files.**

---
*Auto-generated by VedicAstro handoff maintainer. Never edit manually.*
"""

    if dry_run:
        print("DRY RUN — takeover pack would be written to", pack_path)
    else:
        pack_path.write_text(content, encoding="utf-8")
        print(f"Generated {pack_path}")

    return pack_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Keep CONTEXT.md and handoff docs current")
    parser.add_argument("--update-context", action="store_true", help="Update CONTEXT.md sections")
    parser.add_argument("--generate-pack", action="store_true", help="Generate AI_TAKEOVER_PACK.md")
    parser.add_argument("--update-all", action="store_true", help="Do both + print summary")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing")
    args = parser.parse_args()

    if not any([args.update_context, args.generate_pack, args.update_all]):
        args.update_all = True

    print("Introspecting KnowledgeEngine...")
    state = get_current_state()
    print(f"  Graph: {state['graph_version']} ({state['node_count']:,} nodes)")
    print(f"  Engines: {state['registered_names']}")

    changed = False
    if args.update_context or args.update_all:
        changed = update_context_md(state, dry_run=args.dry_run) or changed
    if args.generate_pack or args.update_all:
        generate_takeover_pack(state, dry_run=args.dry_run)
        changed = True

    if changed and not args.dry_run:
        print("\nHandoff documentation is now up to date.")
        print("Commit the changes so the next AI sees the latest state.")


if __name__ == "__main__":
    main()
