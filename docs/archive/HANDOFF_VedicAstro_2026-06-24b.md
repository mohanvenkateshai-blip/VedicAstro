# VedicAstro — Session Handoff (2026-06-24, Session 2)

This continues from `HANDOFF_VedicAstro_2026-06-24.md`. Everything in that file is still valid.
New work this session is below.

---

## What Was Completed This Session

### 1. CONTEXT.md AI Constitution Created
`VedicAstro/CONTEXT.md` — the AI Constitution implementing the Gemini context management strategy.
Contains: system topology diagram, immutable guardrails, component constraints (Python/Next.js/Graph),
cross-system communication sequence, captured experience (known bugs), knowledge graph state,
token routing table, next phases, and verify-it-still-works checklist.

**Impact:** Should raise next-agent confidence from 78/100 → 90+.
**Rule:** Every AI session touching VedicAstro must read `CONTEXT.md` first.

### 2. Activity Mapping chunk_03 Extraction Dispatched
A background general-purpose subagent was dispatched to extract categories 13–23 + appendices
from `knowledge-graph/raw/Activity_Mapping.md` into:
`knowledge-graph/graphify-out/.graphify_chunk_03.json`

**Status:** In-flight at handoff time — check if the file exists at session start.

---

## IMMEDIATE NEXT STEPS (in order)

### Step 1: Verify chunk_03 was written
```bash
ls -la /Users/ganesha/Projects/04-UX-Practice/VedicAstro/knowledge-graph/graphify-out/.graphify_chunk_03.json
python3 -c "import json; d=json.load(open('VedicAstro/knowledge-graph/graphify-out/.graphify_chunk_03.json')); print(len(d['nodes']), 'nodes,', len(d['edges']), 'edges')"
```
If it doesn't exist: re-run the extraction (categories 13-23 content is in HANDOFF_VedicAstro_2026-06-24.md,
the Activity_Mapping.md file is at `knowledge-graph/raw/Activity_Mapping.md` lines 642-1150).

### Step 2: Merge chunk_03 into graph.json
The graphify python interpreter is at:
```bash
cat VedicAstro/knowledge-graph/graphify-out/.graphify_python
# → /Users/ganesha/Projects/04-UX-Practice/Panchang/.venv/bin/python3
```

Merge script (run from `VedicAstro/knowledge-graph/`):
```python
# merge_chunk03.py
import json
from pathlib import Path

out = Path("graphify-out")
g = json.loads((out / "graph.json").read_text())
c3 = json.loads((out / ".graphify_chunk_03.json").read_text())

# graph.json uses "links" not "edges"
existing_node_ids = {n["id"] for n in g["nodes"]}
new_nodes = [n for n in c3["nodes"] if n["id"] not in existing_node_ids]
g["nodes"].extend(new_nodes)
g["links"].extend(c3["edges"])  # chunk uses "edges", graph uses "links"
g.setdefault("hyperedges", []).extend(c3.get("hyperedges", []))

(out / "graph.json").write_text(json.dumps(g, indent=2))
print(f"After merge: {len(g['nodes'])} nodes, {len(g['links'])} links")
```
Run: `$(cat graphify-out/.graphify_python) merge_chunk03.py`

### Step 3: Rebuild clustering + HTML visualization
```bash
cd /Users/ganesha/Projects/04-UX-Practice/VedicAstro/knowledge-graph
PYTHON=$(cat graphify-out/.graphify_python)
$PYTHON -c "
import json
from pathlib import Path
from graphify.cluster import cluster
from graphify.visualize import visualize_html

g = json.loads(Path('graphify-out/graph.json').read_text())
g = cluster(g)
Path('graphify-out/graph.json').write_text(json.dumps(g, indent=2))
html = visualize_html(g)
Path('graphify-out/graph.html').write_text(html)
print('Done. Communities:', len(set(n.get(\"community\") for n in g[\"nodes\"])))
"
```

### Step 4: Update GRAPH_REPORT.md
Re-run the god-node analysis and append a section for the new categories 13-23.
Key questions to answer in the report:
- Does Ashwini's betweenness rise after adding Medical/Health categories? (It's prescribed for almost every medical activity)
- Does Rohiṇī maintain #1 betweenness after adding all 91 activities?
- Do the new categories form distinct communities or merge into existing ones?

### Step 5: Run Rohiṇī formal query trace
```bash
cd /Users/ganesha/Projects/04-UX-Practice/VedicAstro/knowledge-graph
```
Then invoke: `/graphify query "Why does Rohini bridge Business Finance, Wedding, Scoring, and Samskara muhurtas?"`
Document findings in: `knowledge-graph/graphify-out/FINDINGS.md` (create if not exists)

---

## NEXT PHASE (after graph is complete)

1. **Add BPHS + Phaladeepika** to knowledge graph
   - Files in: `/Users/ganesha/Projects/04-UX-Practice/Panchang/Gyan/extracted_markdown/`
   - Look for: `Brihat_Parasara_Hora_Sastra_Vol_1.md`, `Phaladeepika.md` or similar names
   - Focus: natal yogas (planet combinations for chart interpretation)

2. **Wire graph.json into `/predict` endpoint** as GraphRAG rules source
   - In `cvce/app/server.py` or `cvce/vedic_engine/`
   - Replace/augment hardcoded `transit_rules.py` with graph-query lookups

3. **Postgres + real auth/RBAC**
   - Schema in `panchanga_muhurtha/vedicshastra_master_bundle/database_schema.sql`
   - NextAuth → `portal/src/lib/auth.ts` seam (currently scaffold returning null)
   - Wire into `portal/src/proxy.ts` RBAC check
   - Encrypt birth PII, row-level security per role (free/pro/premium/admin)

---

## Context Management Strategy (Internalized)

From the Gemini research session, five strategies now guide this project:

1. **AI Constitution** → `VedicAstro/CONTEXT.md` (DONE)
2. **Hierarchical Segmentation** → `.ai/python-engine.md`, `.ai/nextjs-portal.md` (TODO — create these)
3. **On-Demand Retrieval** → GraphRAG queries instead of pasting full schemas
4. **Context Quarantine** → isolated git branches per sub-task (async agent → PR workflow)
5. **Captured Experience** → `docs/ai/` bug-rule files after every painful fix (see CONTEXT.md § 5)

The `.ai/` directory files are still TODO — lower priority than graph completion.

---

## System Verification

Before any new coding session, run:
```bash
curl https://vedicastro-cvce.fly.dev/health
cd /Users/ganesha/Projects/04-UX-Practice/VedicAstro/cvce && .venv/bin/python -m pytest tests/golden/ -q
```
Expected: `{"status":"ok"}` and `7 passed`.
