# KnowledgeEngine Architecture (Final)

**Date:** 2026-06-29  
**Status:** Supabase is the default backend. KnowledgeEngine is the single source of truth.

---

## High-Level Architecture

```mermaid
flowchart TB
    subgraph Clients["Clients"]
        Portal["Portal (Vercel)"]
        Admin["Admin / CLI / CI"]
    end

    subgraph CVCE["CVCE Runtime (Fly.io)"]
        Server["FastAPI Server"]
        subgraph Engines["Engines (registered with KE)"]
            Gochar["Gochar Engine"]
            Muhurta["Muhurta Engine"]
            Report["Report Engine"]
            Dasha["Dasha Engines"]
            Future["Future Engines..."]
        end
    end

    subgraph Knowledge["Knowledge Layer"]
        KE["KnowledgeEngine (cvce/knowledge_engine)"]
        subgraph Store["Pluggable Store"]
            SupabaseStore["SupabaseKnowledgeStore"]
            FileStore["FileKnowledgeStore (dev)"]
        end
    end

    subgraph Data["Data Layer"]
        Supabase["Supabase (Primary)"]
        subgraph Tables["Tables + Vector"]
            graph_nodes
            graph_links
            corpus_chunks["corpus_chunks (pgvector)"]
        end
        Bucket["corpus-vault (private bucket)"]
        GraphFile["graph.json (committed)"]
    end

    Portal --> Server
    Admin --> KE

    Server --> KE
    Gochar --> KE
    Muhurta --> KE
    Report --> KE
    Dasha --> KE

    KE --> SupabaseStore
    KE --> FileStore

    SupabaseStore --> Supabase
    FileStore --> GraphFile

    Supabase --> Tables
    Supabase --> Bucket
```

---

## Detailed Runtime Flow

```mermaid
sequenceDiagram
    participant Client
    participant Server as CVCE Server
    participant KE as KnowledgeEngine
    participant Store as SupabaseKnowledgeStore
    participant GraphRAG as GraphRAG (via KE)

    Client->>Server: POST /predict or /report/facts
    Server->>KE: get_safe_transit_rules() / get_safe_muhurta_rules()
    KE->>Store: health_check + get_safe_rules()
    Store-->>KE: validated rules + version
    KE-->>Server: rules (or blocked)

    Server->>KE: get_prediction_enhancer()
    KE-->>Server: PredictionEnhancer (graph-backed)
    Server->>Server: build_report_facts() / predict()

    Note over Server: Engines may call ke.trigger_global_refresh() or ke.revive()
```

---

## Key Components

| Component                        | Responsibility                                      | File |
|----------------------------------|-----------------------------------------------------|------|
| `KnowledgeEngine`                | Central owner, health, invalidation, revival, cascade | `engine.py` |
| `SupabaseKnowledgeStore`         | Secure DB access + vector search                    | `store/supabase_store.py` |
| `EngineRegistry`                 | Tracks dependent engines + callbacks                | `registry.py` |
| `integration.py`                 | Safe public API used by the rest of the system      | `integration.py` |
| `trigger_global_refresh()`       | Force refresh across all engines                    | `engine.py` + `/knowledge/refresh` |
| `on_new_literature_ingested()`   | Cascade hook called by ingestion scripts            | `engine.py` |

---

## Security Model

- All database access goes through `SupabaseKnowledgeStore`
- Service role key is used, but encapsulated
- Future improvements:
  - Dedicated `KNOWLEDGE_ENGINE_KEY`
  - Request logging + audit
  - Per-engine permissions

---

## Refresh & Cascade Mechanism

1. New texts ingested → `merge --promote`
2. Ingestion script calls `KE.on_new_literature_ingested(...)`
3. `KnowledgeEngine` updates version + notifies all registered engines
4. Engines implement `on_refresh()` to drop caches and rebuild

Alternatively, anyone can call:

```
POST /knowledge/refresh
```

to force a global recalculation.

---

*This architecture cleanly separates astronomical calculation (PyJHora) from classical Vedic knowledge (Knowledge Graph via KnowledgeEngine).*