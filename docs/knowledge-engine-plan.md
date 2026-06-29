# KnowledgeEngine Roadmap & Loose Ends Status

**Date:** 2026-06-29

## The 4 Promoted Items — Realistic Timeline

These were promoted from "deferred" to active on June 29.

| Item | Current Maturity | Estimated Effort to "Done" | Target for First Usable Version |
|------|------------------|------------------------------|---------------------------------|
| Vector embeddings on `corpus_chunks` | Infrastructure + generator script exist. No embeddings populated. | 2–4 focused sessions | Embed all current sources + basic retrieval in `/orchestrate` or a new search endpoint. |
| LLM narration (`CVCE_LLM_NARRATION=1`) | Gate + Gemini call + UI render exist. | 1–2 sessions | Make it stable, add length control, source grounding, and rate limiting. |
| Kaksha + Chara/Kalachakra dashas | Stubs + notes in `/dashas`. Real logic missing. | 4–8 sessions (significant) | At least Chara periods + basic Kaksha refinement returning usable data. |
| Deeper Hiranya-quality report UI polish | Narration block added. Many chapters still thin. | Ongoing (parallel with facts) | Close the biggest gaps vs `report_facts` output + add better visualization for graph citations. |

**Honest answer on "when will they be completed?":**
There is no fixed calendar. This is not a staffed project with sprint commitments.  
Current pace (aggressive daily work) suggests:

- LLM narration + basic vector retrieval: could be in a usable state within the next few days of focused work.
- Chara/Kalachakra + deeper report polish: likely 1–3 weeks of real effort depending on how deep "full" is defined.

## The Bigger Vision: KnowledgeEngine

The user wants a proper central component with these guarantees:

1. **Cascading updates** — New literature → automatically affects rules, predictions, interpretations everywhere.
2. **Invalidation & blocking** — Bad/stale/confusing knowledge can be globally blocked.
3. **Periodic revival** — Engines can be told "refresh your context" with the latest safe knowledge.

### Proposed Architecture

```
KnowledgeEngine (new central owner)
├── Owns GraphRAG loading + versioning
├── Maintains validity / invalidation set
├── EngineRegistry (who cares about what knowledge)
├── Propagation hooks (on new ingestion, on invalidate, on revive)
└── Public safe API for engines: get_safe_knowledge(...)

Consumers (register themselves):
- Gochar engine
- Muhurta engine
- Report engine
- Dasha engines
- Future hybrid search, etc.
```

Ingestion pipeline will eventually call:
`knowledge_engine.on_new_literature_ingested(new_graph_path, version)`

Instead of engines talking directly to GraphRAG or raw `graph.json`.

### Current Gaps vs This Vision

- GraphRAG is still a low-level singleton loader.
- No central validity/invalidation system.
- No registration of consumers.
- Ingestion scripts do not notify anything.
- No revival protocol.
- Embeddings and LLM narration are not yet part of the "knowledge" that can be blocked/revived.

### Phased Plan (What We Will Actually Do)

**Phase A (Immediate — next 1-3 sessions)**
- Finish basic KnowledgeEngine skeleton (done in this session).
- Wire it into server.py as the source of truth for graph access.
- Make `active_transit_rules()` and `active_muhurta_rules()` go through KnowledgeEngine.
- Implement simple invalidation + blocking.

**Phase B (Vector + Embeddings)**
- Populate embeddings for current corpus.
- Add retrieval capability behind KnowledgeEngine.
- Expose safe vector search.

**Phase C (Validity & Blocking)**
- Add node-level + version-level blocking.
- Admin or script interface to invalidate bad knowledge.
- Engines respect the block list.

**Phase D (Cascading + Revival)**
- Ingestion scripts call `on_new_literature_ingested`.
- Implement `revive()` that pushes fresh views to registered engines.
- Add logging/observability so we can see when knowledge changed.

**Phase E (Full interlinking)**
- Prediction engines register interest in specific knowledge domains.
- On ingestion or invalidation, only affected engines are notified.
- Periodic background revival job.

This is the real plan. We are starting the foundation right now.
