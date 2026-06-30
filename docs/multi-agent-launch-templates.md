# Multi-Agent Launch Templates, Prompts & Enforcement Kit

**Purpose:** Reusable, copy-paste infrastructure so the main agent (or any future session) can autonomously honor the mandatory protocol and launch 5–15+ specialized sub-agents at the very first step of post-reorg workstreams.

**Mandatory references (always cite):**
- `.cursor/rules/multi-agent-mandatory-protocol.mdc` (alwaysApply: true)
- `docs/MULTI_AGENT_MANDATORY_RULE.md`
- Example successful wave: `docs/multi-agent-wave-gyan-structured-2026-06-30.md`
- Handoff contract: `docs/handoff/AI_TAKEOVER_PACK.md` + `scripts/handoff/maintain_context.py`

**Core rule (verbatim from protocol):** NEVER start a substantial task sequentially or with fewer than 5 agents. ALWAYS launch a minimum of 5 specialized sub-agents in parallel at the very beginning using the `Task` tool. One of the initial agents MUST be a "Multi-Agent Compliance / Reminder / Orchestrator".

**Substantial =** code changes, data processing (embeddings, Supabase writes, patches), audits, scripts (admin CLI, visualizer), verification, docs that touch the knowledge surface, etc.

---

## (a) Ready-to-Paste "Launch 8+ Agents" Block (Post-Reorg Workstreams)

**Usage:** At the absolute first response for any new task touching embeddings, Supabase apply, visualizer, admin CLI, verification, or related KE/structured work — immediately emit the block below (or a close variant with 8–12+). Do not ask clarifying questions first. Customize only the focused prompts and titles.

All launches happen in one parallel burst. Follow with status updates using `UpdateCurrentStep`.

```xml
<!-- BEGIN LAUNCH BLOCK: emit ALL of these (or 8+ equivalents) in a SINGLE response as your very first actions. Do not interleave other work. -->
<!-- 01 Orchestrator / Compliance (MANDATORY in first 5) -->
tool request Task with subagent_type is generalPurpose
description is Multi-Agent Compliance / Reminder / Orchestrator for post-reorg wave
prompt is You are the dedicated Multi-Agent Reminder / Compliance / Orchestrator sub-agent. This is a substantial task in the VedicAstro post-reorg phase (embeddings population, Supabase patch apply, visualizer updates, admin CLI, verification). Confirm at start of session that a minimum of 5 specialized agents (including yourself) were launched in true parallel using multiple Task calls in the opening response. Scan for any sequential drift in the parent or siblings. If active specialized agents drop below 5 or work becomes linear, immediately propose and trigger additional parallel Task launches. Maintain a running "Multi-Agent Health" log (agents spawned, types, phases covered, artifacts). Force scaling to 8–12 for normal feature work or 15+ for broad verification. Update handoff/status files (knowledge-engine-status.md, AI_TAKEOVER_PACK context if relevant, new wave doc) with concise protocol adherence notes at major steps. Never let the wave complete without an explicit "Multi-agent protocol honored" close. Coordinate lightly; do not do the domain work yourself.

<!-- 02 State Explorer (embeddings + Supabase + current graph state) -->
tool request Task with subagent_type is explore
description is Embeddings / Supabase / Graph State Auditor
prompt is You are an explore sub-agent. Audit current state for vector embeddings and Supabase readiness: (1) Confirm pgvector + corpus_chunks table schema and any existing embeddings count. (2) Locate the embeddings generator code (likely under cvce or scripts) and note entrypoints, env vars, model choice. (3) Check Supabase connection from cvce (env, client). (4) Sample 5–10 corpus_chunks and graph_nodes to see current chapter/provenance fields. (5) Produce a concise STATE_AUDIT.json + recommended next commands for population and apply. Be quantitative. Output only findings + commands + file list. Do not apply changes.

<!-- 03 Supabase / Patch Applier (shell + safe writes) -->
tool request Task with subagent_type is shell
description is Node-Chapter Patch Applier + Supabase Backfill
prompt is You are a shell/data sub-agent focused on safe application. Using existing patches in knowledge-graph/patches/ (COVERAGE_MATRIX, per-book patch-*.json, node-chapter-map), (1) Create or refine `scripts/apply_node_chapter_patches.py` (or equivalent) that can target Supabase `graph_nodes` (add chapter_id, section_id, hierarchy_path, map_method, map_conf, source_book) and also update local graph.json fallback. (2) Support --dry-run, --book, --all, --verify. (3) Run dry-run on 3+ high-value books first (e.g. Phaladeepika, Saravali, BPHS Vol1, Ashtakavarga, Jaimini if ready). (4) Produce RUN_APPLY_LOG.txt + UPDATED_COVERAGE.json + any delta patches. (5) After safe dry, execute targeted apply if Supabase creds allow (or document exact SQL/CLI). Never overwrite without backup note. Summarize coverage lift quantitatively.

<!-- 04 Embeddings Implementer (population under KE) -->
tool request Task with subagent_type is generalPurpose
description is Vector Embeddings Population Engineer (KE-owned)
prompt is You are a generalPurpose implementer. Own the embeddings workstream: (1) Ensure KnowledgeEngine (or a thin vector module) is the single owner of `search()` and population for corpus_chunks. (2) Wire or extend the generator so it respects KE version/refresh and writes to Supabase pgvector with proper metadata (book, chapter, section, node ids). (3) Add a one-shot populate script or `ke.populate_embeddings()` entry. (4) Handle incremental vs full, model config, batching. (5) After run, expose or confirm a `/knowledge/search` or equivalent path that uses real embeddings (or at minimum document the callable). Produce a short EMBEDDINGS_RUN_REPORT.md with counts before/after and any errors. Keep changes minimal and backward-compatible.

<!-- 05 Visualizer Updater -->
tool request Task with subagent_type is generalPurpose
description is Knowledge Graph Visualizer Chapter + Provenance Enhancer
prompt is You are a generalPurpose UI/visualization sub-agent. Update the standalone or main visualizer(s) (knowledge-graph-visualizer*.html, scripts/visualize-*.html) to: (1) Render chapter hierarchy when available (from structured or patch data). (2) Show node provenance badges/links ("Sourced from: <book> ch X / sec Y (method, conf)"). (3) Add filters or legends for parse_quality / review_needed. (4) Support deep links or selection that mirror the Learn reader behavior. (5) Keep the viz self-contained or easily runnable. Produce a VISUALIZER_UPDATE.md with before/after notes + any new static snapshot if useful. Test by loading real patch + structured data.

<!-- 06 Admin CLI / Ops Script Builder -->
tool request Task with subagent_type is shell
description is Admin CLI + Scriptable Ops for Structured + Mapping + Refresh
prompt is You are a shell/ops sub-agent. Build or extend a small admin surface: (1) Add commands to scripts/vedicops.py or a new `scripts/admin_structured.py` for: rebuild-structured [book], remap-book [book] [--supabase], invalidate-chapter, show-coverage, trigger-refresh. (2) Make it safe (dry-run default, confirmations, logging). (3) Wire common paths used in post-reorg (structured build + map + apply + embeddings stub). (4) Output a short ADMIN_CLI.md with usage examples. Ensure it can be called from handoff or CI notes.

<!-- 07 Verification & E2E Harness -->
tool request Task with subagent_type is generalPurpose
description is End-to-End Verification Harness (structured → map → Supabase → portal → viz)
prompt is You are a verification sub-agent. Create or extend a minimal harness (pytest or script under tests/ or scripts/verify_*.py): (1) For 3–5 representative books (mix handbook + classic), assert: structured chapters exist and have sections where expected, patch coverage >= threshold, Supabase (or local graph) nodes carry chapter provenance after apply, Learn reader renders the hierarchical TOC for the book, visualizer can load the data. (2) Add a "smoke" for embeddings presence if populated. (3) Run against both file fallback and Supabase where possible. (4) Produce VERIFICATION_REPORT.md + any golden updates. Fail loudly on regressions. Keep it fast and repeatable.

<!-- 08 Cross-Cutting Explorer / Auditor (for remaining gaps) -->
tool request Task with subagent_type is explore
description is Post-Reorg Gap Auditor (remaining books, engine registration, docs)
prompt is You are an explore sub-agent for completeness. (1) From the prior structured audit + patches, list the next 5–8 highest-value books still needing quality structured or remapping (use needs_review signals + node importance). (2) Check which engines (beyond Gochar/Muhurta/Report) should now consume chapter provenance or structured (Dasha, Yoga, Panchanga, Prashna, etc.) and note registration gaps. (3) Scan docs/ and status files for stale references to old chapter logic. (4) Emit a NEXT_WAVE_PLAN.md with prioritized parallel items + suggested agent counts. Quantitative only.

<!-- 09 Handoff / Status Synchronizer -->
tool request Task with subagent_type is generalPurpose
description is Handoff & Status Documentation Synchronizer
prompt is You are a documentation/handoff sub-agent. After the technical agents produce artifacts: (1) Ensure knowledge-engine-status.md, CONTEXT.md, KNOWLEDGE_CATALOG (if relevant) and a new wave summary (e.g. docs/post-reorg-wave-*.md) contain a "Multi-Agent Health" section declaring protocol adherence (N agents, types, start time). (2) If patches or embeddings changed state, note exact commands run. (3) Optionally trigger or document `python scripts/handoff/maintain_context.py --update-all` (do not run if it would require side effects you cannot control). Keep diffs minimal. Output the exact snippets that should be added.

<!-- 10 (Scale) Lightweight Test / Linter Guard (when 10+ desired) -->
tool request Task with subagent_type is generalPurpose
description is Lint + Type + Smoke Guard for changed surfaces
prompt is You are a guard sub-agent. After code/scripts are proposed by peers: run targeted lint/type checks on portal/, cvce/, scripts/ for the touched files. Run any existing golden tests or the new verification harness in dry mode. Report clean vs issues with exact commands to fix. Do not block final artifacts on non-critical issues; just surface them.
<!-- END LAUNCH BLOCK -->
```

**How to use the block:** Paste the entire XML-style block (with 8–12 entries) as the first content the main agent emits when a post-reorg workstream begins. The system will dispatch the sub-agents. Then monitor via transcripts and `UpdateCurrentStep` reports.

**Scaling note:** For "FAAASSTTT" add 4–6 more (e.g. dedicated Jaimini rescue, full corpus re-ingest verifier, performance on vector queries, deploy smoke, etc.).

---

## (b) Suggested Subagent Types + Focused Prompts for 3–4 New Workstreams

Use the exact style from successful waves: role sentence first, then numbered concrete tasks, expected artifacts, constraints (parallel-safe, no unnecessary edits, quantitative).

### Workstream 1: Embeddings Population (corpus_chunks + KE ownership)
- **Orchestrator** (generalPurpose) — use the template in (a) #01
- **Explorer** (explore) — use/adapt (a) #02
- **Implementer** (generalPurpose) — use/adapt (a) #04
- **Applier/Infra** (shell) — ensure Supabase writes + index + env
- **Verifier** (generalPurpose) — smoke a few semantic searches post-populate and confirm KE gating

**Focused prompt skeleton (for Implementer):**
```
You are a generalPurpose implementer. Own the embeddings workstream under KnowledgeEngine: ...
```
(See full in launch block.)

### Workstream 2: Supabase Patch Apply + Provenance Backfill
- **Orchestrator**
- **Auditor** (explore) — current patch coverage + Supabase column readiness
- **Applier** (shell) — the core safe apply script + execution (see (a) #03)
- **Portal/KE Bridge** (generalPurpose) — ensure readers and any direct KG consumers see the new fields without breakage
- **Verifier** (generalPurpose) — coverage delta + spot checks in UI

### Workstream 3: Visualizer + Chapter/Provenance UI
- **Orchestrator**
- **Code Explorer** (explore) — find all visualizer entrypoints and data loading paths
- **Enhancer** (generalPurpose) — the UI changes (see (a) #05)
- **Data Mapper** (shell) — small util if viz needs a preprocessed view of structured+patch
- **Cross-checker** (generalPurpose) — compare viz rendering vs Learn reader for 2–3 books

### Workstream 4: Admin CLI + Scriptable Ops
- **Orchestrator**
- **Ops Designer** (generalPurpose) — command surface + safety model
- **Script Author** (shell) — implementation + docs (see (a) #06)
- **Integration Tester** (generalPurpose) — wire the CLI into common post-reorg flows (rebuild → remap → apply → verify)
- **Handoff Writer** — ensure usage examples land in takeover pack / status

**Prompt pattern for any new shell sub-agent:**
```
You are a shell/data sub-agent. [3–7 numbered tasks with exact artifacts: RUN_*.txt, *.json reports, scripts, no destructive defaults].
Work in parallel-friendly way; batch when possible. Be safe...
```

**Prompt pattern for explore:**
```
You are an explore sub-agent. [Audit scope]. Produce quantitative STATE_*.json or REPORT. Do not edit.
```

**Prompt pattern for generalPurpose (feature/integration):**
```
You are a generalPurpose [role]. [Integration or build task list + compatibility constraints + final artifact names].
```

Always end sub prompts with: "UpdateCurrentStep at start and major phases. Output concise, actionable results only."

---

## (c) Minimal Checklist the Main Agent Must Follow to Enforce "Start with 5+" (No Drift)

Copy this checklist into the orchestrator prompt and re-read it at the beginning of every substantial session. The main agent should treat it as executable guardrails.

```markdown
- [ ] **Wave 1 trigger:** At the literal first sign of a substantial task (see protocol), BEFORE any single-threaded action or user Q&A, emit >=5 parallel `Task` tool calls.
- [ ] **Orchestrator included:** At least one of the first 5 is explicitly typed as the Compliance/Reminder/Orchestrator with the monitoring + force-spawn charter.
- [ ] **Varied types:** Use distinct subagent_type values (generalPurpose, explore, shell, ...). Never all the same.
- [ ] **Non-overlapping charters:** Each sub gets 3–7 concrete, scoped tasks + named artifacts. No "help with everything".
- [ ] **Self-contained prompts:** The prompt passed to each Task must be copy-paste runnable by a fresh sub-agent with no additional context.
- [ ] **Report immediately:** In the same opening turn or first follow-up, surface "Launched N agents (list with types and short labels)".
- [ ] **Mid-wave scaling:** If any status update shows <5 active or sequential pattern, emit more Task calls in that response without waiting.
- [ ] **Status hygiene:** Every major status file touched in the wave must gain or update a "Multi-Agent Health" table or paragraph citing agent count + protocol file.
- [ ] **Completion seal:** Final summary from orchestrator or main must contain the phrase "Multi-agent protocol honored: X agents in wave, no drift observed" (or documented exceptions + recovery).
- [ ] **Handoff continuity:** New wave docs or updates must link back to this templates file + the .mdc rule.
- [ ] **Never sleep:** The orchestrator prompt explicitly says it "must be re-spawned at the start of every session/task."
```

**Drift detection signals (orchestrator must watch):**
- Parent asks clarifying questions before launching.
- Only 1–3 agents visible after first response.
- Sub-agents finish and parent proceeds to do the next logical step itself instead of spawning for it.
- No UpdateCurrentStep or parallel reports.

**Recovery:** The moment drift is detected, the orchestrator (or main) must output additional `Task` calls + a short "Scaling now to correct sequential drift" note.

---

## Quick Reference: Agent Types Observed in Successful Waves
- `explore`: diagnosis, audit, gap analysis, state discovery (no or minimal writes)
- `shell`: heavy command execution, bulk runs, script creation + invocation, coverage math
- `generalPurpose`: integration work, parser/refiner logic, UI/reader changes, harnesses, docs sync

Add new ones only when a clear specialized need appears (e.g. `performance-optimizer`).

---

## How Future Waves Should Record Themselves (for agents-launched.log and wave docs)
Create or append to `docs/agents-launched.log` (or a dated wave doc):

```
2026-06-30Txx:xx  post-reorg-embeddings-supabase-viz-cli  agents=8+  types=generalPurpose,explore,shell  orchestrator=xxx  protocol=honored  artifacts=...
```

Link the orchestrator and key subs with their transcript uuids when available (as done in the structured Gyan wave).

---

**This file is the reusable artifact.** Main agent (or any sub) should read it at the start of post-reorg work and emit the launch block verbatim (with light tailoring) as its opening move. Combined with the permanent .mdc rule and the handoff pack declarations, this closes the loop for autonomous, drift-resistant multi-agent execution.

*Do not edit this file manually during a wave; treat it as the source of truth for launch patterns.*
