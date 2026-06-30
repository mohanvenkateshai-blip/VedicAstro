# KE Full Knowledge Update Wave — 2026-06-30

**Goal (user directive):** Trigger knowledge update from *each and every module/feature*. Update corresponding program logic, calculations, and algorithms to reflect the *latest* in the Knowledge Graph (KE). Thorough, supervised, tracked end-to-end. No cracks between walls.

**Protocol:** Multi-agent parallel execution (5–8 agents, non-overlapping scopes). Script-first verification. Narrow reads. Report counts + pass/fail only. Update this tracker at every stage.

**Single source of truth for access:** `cvce/knowledge_engine/integration.py` (get_knowledge_engine, get_safe_*, get_structured_book, clear_knowledge_engine_cache, etc.)

**Registry:** Engines *must* register via `ke.register_engine(name, on_refresh=...)` so that `ke.refresh_knowledge(...)` or graph updates cascade.

**Current baseline (pre-wave):** Several engines register (panchanga, dasha, yoga, ashtakavarga, gochar, muhurta, report, kp, prashna). Many pull `get_structured_book` for context. Rules for transit/muhurta have graph providers with fallback to hardcoded. Not every *algorithm/decision* is yet enriched or re-derived from latest structured + graph nodes/links/patches.

---

## Master Matrix (update rows as work progresses)

Format per row (agents append status + short evidence):
`Module | Key Files | KE integration today | Hardcoded / stale gaps | Target (this wave) | Agent | Status | Evidence (counts, hashes, tests) | Next concrete`

| Module              | Key Files (narrow)                                      | KE today                                      | Gaps (examples)                                                                 | Target this wave                                                                 | Agent | Status     | Evidence                          | Notes |
|---------------------|---------------------------------------------------------|-----------------------------------------------|---------------------------------------------------------------------------------|----------------------------------------------------------------------------------|-------|------------|-----------------------------------|-------|
| Core Panchanga     | cvce/vedic_engine/core/panchanga.py, astronomy.py      | get_structured_book; registers "panchanga"; on_refresh calls _load_panchang_attributes_from_ke | Static NAKSHATRAS/TITHI/NITYA_YOGAS lists; limited attributes pulled from texts; astronomy is pure math | Enrich with tithi lords/specials from panchang handbooks; provenance on result; full register + revive that reloads attrs | P     | DONE       | 7 panch/tithi books; loaded 28 tithi_lords+28 effects+13 yoga_attrs+2 karana from get_structured_book; source_notes cites Tithi Master#ch-the_5...; on_refresh clears+reloads; 1/1 refresh prove (len+fp diff); compute before/after PASS | enriched attrs table + provenance + register |
| Dasha Systems      | prediction/dasha.py, dasha_*.py, synthesis/dasha_analyzer.py | get_structured + register "dasha"; _on_dasha_refresh calls _revive_dasha_rules | Effect descriptions + some conditionals still static; not all BPHS/Saravali variants wired | Load variant effects/conditions from structured Parasara + digests; on_refresh rebuilds tables | D     | DONE    | 7 dasha structured JSONs; revive loads from BPHS+Laghu+Yogini; 3 periods carry ch citations (e.g. Brihat_Parasara_Hora_Sastra_Vol_1:ch-8); result.variant_notes + [KE variants] in summary after clear/refresh/recompute; dasha reg calls revive that changes output | report: docs/agent-reports/KE-wave-dasha.md |
| Muhurta & Yogas    | prediction/muhurta_yogas.py, graph_rag/muhurta_rules_provider.py, synthesis | GraphMuhurtaRules + register (via synthesis + muhurta_yogas self-reg) + on_refresh clears+rebuilds provider | 18 structured + 36 raw muhurta/panchang-auspicious books present. Before: 128 yoga_nodes/27 combo, 0-1 hits typical. After expand: 283 yoga_nodes (Celestial/Tithi-Vara/Tara/DoGhati/muhurta_yogas etc now feed explicit nodes with nature), 150+ hits with book citations for same inputs. evaluate() now self-fetches latest GraphMuhurtaRules if needed and attaches provenance. Full "muhurta" reg + revive reloads provider data. | Expand extraction (done); more corpus now drives electional hits+citations; iframe external at muhurtha.uvwx.me uses KE v indirectly (documented; small note added in page). See docs/agent-reports/KE-wave-muhurta.md | M     | PARTIAL (core done; iframe is external frozen) | yoga_nodes 283 (was 128), hits e.g. Venus/Nanda=157 with Celestial cites; evaluate 160 active w/ sources; revive stable+citations; 4/4 verify PASS | Tracker+report updated |
| Transit/Gochar     | prediction/gochar.py, rules/transit_rules.py, graph_rag/rules_provider.py, synthesis/transit_analyzer | GraphTransitRules + register "gochar"; on_refresh clears+rebuilds | House tables from GPD+HS; deeper effects/exceptions partial | Richer effect nodes + per-planet citations attached (Sun/Moon/Jup + 6 others); transit_analyzer now routes via graph rules; no raw GraphRAG bypass left in path; rebuild_transit_rules on refresh | T     | DONE       | GOCHARA_NODES=1021, RELATED_LINKS=1900; houses_enriched=9 (all planets); cites=2 per planet in compute_gochar; analyzer classical_basis includes graph: nodes; on_refresh increments build_id + moderate impact via auditor probe; before/after compute+analyze PASS (cites present post) | effect snippets + citations + refresh rebuild + auditor moderate |
| Yogas Detection    | prediction/yoga.py                                     | get_structured + register "yoga"             | detect_yogas conditions mostly code; limited chapter-backed citations | Pull additional yoga definitions/conditions from graph + Jataka texts; return node provenance | Y     | PLANNED    | -                                 | - |
| Ashtakavarga       | prediction/ashtakavarga.py                             | get_structured + register "ashtakavarga"     | Point systems + interpretations; handbook exists in corpus but not driving variants | Parameterize or validate AV tables via Ashtakavarga handbook nodes; add citations | A     | PLANNED    | -                                 | - |
| Special Systems    | kp_system.py, prashna.py, varshaphala (explorers + logic) | kp/prashna register + on_refresh (no structured load) | KP/Prashna/Varsha had pockets of static + no revive-from-books | kp+prashna now revive 6 Jaimini/Prasna books (all 6 load post-revive); 4 special endpoints + /version emit ke_version; varsha surface updated | S     | DONE       | books=6/6 (full list incl mandook); kp/prashna get_*_context() + revive(force) verified; ke in shapes | static koota noted |
| Synthesis Engine   | synthesis/engine.py, report_facts.py                   | Partial cache clear + some register "report" | Unified predict may mix fresh/stale sub-results | Gochar subcall now receives graph citations + enriched effects; analyzer uses graph house_quality; synthesis transit summary inherits richer data via gochar result; on_refresh for gochar propagates to predict path | Syn   | PARTIAL  | gochar citations flow into VedicPrediction.gochar; transit_analyzer graph path active inside synthesis.analyzer; 9/9 planets carry cites post-refresh | gochar enrichment visible in synthesis |
| GraphRAG / Integration / Floor | knowledge_engine/* (engine, integration, registry, refresh_auditor), graph_rag/*, production_floor | Central gateway; auditor probes gochar/muhurta | Auditor coverage incomplete; not all modules go through safe_* ; some direct GraphRAG() | Complete auditor probes for all; force safe wrappers; one refresh path; add full registration audit script | G     | PARTIAL    | src=9 engines; probes=10; cracks=4; ke_wave_status.py + run_all_probes() + get_registered_engines_with_status(); script: engines=9 probed=10 cracks=4 (run 2026-06-30) | upgrade 4 cache-only on_refresh; re-run script for PASS |
| Portal Surface     | app/muhurta (iframe), compatibility (KootaMatcher), chart/* pages, api/cvce, admin/knowledge | calls /api/cvce proxy passthrough | No visible "KE version", source citations | cvce proxy now enriches ke_version (from engine + /version); koota+compatibility + varshaphala + kp chart subpage surface "Knowledge source" note + version; admin/knowledge has note | UI    | DONE       | proxy: 2 fns (POST/GET) + cache; 3 UI surfaces (KootaMatcher, VarshaphalaPanel, admin); /api/cvce/version allowed; pages touched: 4 | Koota static tables surfaced with version |
| Orchestration / CVCE App | app/server.py, orchestrator/, tests/                   | Startup registrations attempted              | Some engines miss registration at import time; golden tests not yet KE-versioned | Ensure all on app start; extend golden to snapshot ke_version + fingerprint | O     | PARTIAL    | src=9; 4/9 real_reload (dasha/yoga/ashtakavarga/report); 4 cracks flagged by ke_wave_status.py (engines=9 probed=10 cracks=4) | ensure app-start + golden ke_version |

**Status legend:** PLANNED | IN_PROGRESS | PARTIAL (code + gaps listed) | DONE (with verification counts) | BLOCKED (note why)

---

## Supervision & Tracking Process (no cracks)

1. **Start of wave:** This doc + todo list created. 5+ agents launched in parallel with non-overlapping scopes.
2. **Per agent contract (mandatory):**
   - Read narrow slices only (grep + ≤80 line reads).
   - Use scripts for counts/verification (e.g. `python3 -c 'from ... import ...; print(len(...))'` or existing verify_*).
   - Update your matrix row (Status + Evidence + Notes).
   - Append a 1–2 page agent report to `docs/agent-reports/KE-wave-<short>.md` (or create dir).
   - Make at least one concrete logic/algorithm or wiring change that pulls more from KE.
   - Run area-specific verification (pytest for your files or targeted -c snippet). Report PASS/FAIL counts.
   - Call clear + re-compute after changes to prove refresh works.
3. **Central checkpoints (owner or any agent can run):**
   - `python3 -m cvce.knowledge_engine.refresh_auditor` (extend if needed)
   - `cd cvce && python -m pytest tests/ -q --tb=line | tail -5`
   - `node portal/scripts/verify-all-learn-books.mjs` (for structured side)
   - `python3 scripts/verify_harden.py` (if applicable)
   - `scripts/smoke-learn-production.sh` only if Learn surface changes (per token rules)
4. **"No cracks" checklist (every row must address before DONE):**
   - [ ] Registered with unique name + on_refresh that actually clears *and* reloads new data/logic
   - [ ] Uses `integration.get_safe_*` or documented wrappers (no raw `GraphRAG()` outside controlled providers)
   - [ ] Structured book / node provenance attached to relevant outputs
   - [ ] Auditor probe exists or extended for this module
   - [ ] At least one algorithm/interpretation table/condition now sourced or validated from KE corpus (not just "context")
   - [ ] Verification numbers reported (e.g. "12 new yoga conditions loaded from 3 books, 4/4 tests pass")
   - [ ] Tracker row + short report written
5. **Reporting style:** Counts + pass/fail. Example: "Structured books referenced: 61. Graph nodes used for transit: 47. Refresh cascade tested: PASS (3 engines notified)."

---

## Quick Commands (run anytime)

```bash
# Baseline KE health + stats (narrow)
python3 -c "
from cvce.knowledge_engine.integration import get_knowledge_engine
ke = get_knowledge_engine()
print('healthy:', ke.is_healthy())
print('stats:', ke.get_stats())
print('registered:', ke.registry.registered_names())
"

# Force refresh (will notify all)
python3 -c "
from cvce.knowledge_engine.integration import get_knowledge_engine
ke = get_knowledge_engine()
ke.refresh_knowledge(reason='manual-wave')
print('refreshed')
"

# Auditor (will grow)
python3 -m cvce.knowledge_engine.refresh_auditor 2>&1 | head -30

# Targeted module reload test (example)
python3 -c "
from cvce.vedic_engine.core.panchanga import compute_panchanga
from cvce.knowledge_engine.integration import clear_knowledge_engine_cache
clear_knowledge_engine_cache()
r = compute_panchanga('2026-06-30', '12:00', 12.3, 76.65, 5.5)
print('panch keys:', list(r.__dict__.keys())[:8])
"
```

---

## Agent Reports (populated by agents)

See `docs/agent-reports/` (create on first use).

---

## Exit Criteria (before marking wave complete)

- All matrix rows at least PARTIAL; critical paths (panchanga, dasha, muhurta, gochar, synthesis) at DONE.
- Every registered engine's on_refresh demonstrably changes a data-driven output (fingerprint diff before/after or new node count in result).
- Auditor covers ≥90% of registered engines (script count).
- No direct GraphRAG singleton bypasses left in calc paths.
- Portal surfaces KE corpus version in at least one key feature response or header.
- This doc + status.md updated with summary counts.
- Git status clean or intentionally staged changes with clear commit message.
- Production smoke (if Learn/portal surface touched) passes via script.

**Start date:** 2026-06-30  
**Owner:** Multi-agent wave (no single human gate)  
**Next after baseline:** Agents execute in parallel.

---

*Do not paste full graph.json or large structured blobs here. Use counts, fingerprints, file lists, and script outputs only.*
