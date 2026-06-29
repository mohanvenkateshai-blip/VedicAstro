# Knowledge Graph → Engines Connection (Runtime Flow)

This document shows exactly how the Knowledge Graph is wired into the various engines.

---

## 1. High-Level Architecture

```mermaid
flowchart TB
    subgraph Ingestion["Offline Ingestion (not runtime)"]
        Texts["Classical Texts<br/>(raw/*.md + newbooks)"]
        Extract["Extraction Scripts<br/>(gyan-corpus-extract + LLM batch)"]
        GraphJSON["graph.json<br/>(26,722 nodes)"]
        Texts --> Extract --> GraphJSON
    end

    subgraph Runtime["CVCE Runtime (FastAPI)"]
        GraphRAG["GraphRAG (singleton)<br/>cvce/graph_rag/graph.py"]
        GraphJSON -.->|"loaded at startup<br/>(or baked in container)"| GraphRAG

        subgraph GraphRAG_Layer["GraphRAG Layer"]
            TransitRules["active_transit_rules()<br/>graph_rag/rules_provider.py"]
            MuhurtaRules["active_muhurta_rules()<br/>graph_rag/muhurta_rules_provider.py"]
            Enhancer["PredictionEnhancer<br/>graph_rag/enhancer.py"]
        end

        GraphRAG --> TransitRules
        GraphRAG --> MuhurtaRules
        GraphRAG --> Enhancer

        subgraph Calculation_Engines["Pure Calculation Engines (PyJHora)"]
            Panchanga["Panchanga"]
            Positions["Positions / Vargas"]
            BasicDasha["Basic Dasha (Vimshottari etc.)"]
            Ashtakavarga["Ashtakavarga"]
        end

        subgraph Synthesis["Synthesis + Intelligence Layer"]
            VedicPredictor["VedicPredictor<br/>vedic_engine/synthesis/engine.py"]
            Gochar["compute_gochar()"]
            ReportFacts["build_report_facts()"]
        end

        TransitRules --> Gochar
        MuhurtaRules --> VedicPredictor
        Enhancer --> ReportFacts
        Enhancer --> VedicPredictor

        subgraph API["API Layer (cvce/app/server.py)"]
            Predict["/predict"]
            Orchestrate["/orchestrate"]
            Report["/report/facts"]
            Rules["/rules"]
            Dashas["/dashas"]
            Health["/predict/health"]
        end

        VedicPredictor --> Predict
        VedicPredictor --> Orchestrate
        ReportFacts --> Report
        Gochar --> Predict
        TransitRules --> Rules
        Rules --> Health
    end

    subgraph Clients["Clients"]
        Portal["Portal (Next.js)"]
        Direct["Direct API consumers"]
    end

    API --> Portal
    API --> Direct
```

---

## 2. Detailed Runtime Flow (Most Important)

```mermaid
sequenceDiagram
    participant Client as Portal / API Client
    participant Server as CVCE (server.py)
    participant Predictor as VedicPredictor
    participant Graph as GraphRAG (singleton)
    participant Rules as Rules Providers
    participant Enhancer as PredictionEnhancer

    Client->>Server: POST /predict or /orchestrate
    Server->>Predictor: predict(...)

    Note over Predictor: 1. Always compute core astronomy
    Predictor->>Predictor: compute_panchanga() [PyJHora]

    Note over Predictor: 2. Pull rules from Knowledge Graph
    Predictor->>Rules: active_muhurta_rules()
    Rules->>Graph: load graph.json (once)
    Graph-->>Rules: nodes + links
    Rules-->>Predictor: muhurta yoga hits (with citations)

    Note over Predictor: 3. Compute Gochar (may use graph rules)
    Predictor->>Rules: active_transit_rules()
    Rules-->>Predictor: transit house tables from GPD + HS
    Predictor->>Predictor: compute_gochar()

    Note over Predictor: 4. Other calculations (pure astronomy)
    Predictor->>Predictor: compute_dasha(), detect_yogas(), ashtakavarga()

    Note over Predictor: 5. Enrich with classical citations
    Predictor->>Enhancer: enhance(result)
    Enhancer->>Graph: query relevant nodes
    Graph-->>Enhancer: citations + effects
    Enhancer-->>Predictor: enriched result with graph_citations

    Predictor-->>Server: VedicPrediction (with graph data)
    Server-->>Client: JSON response (includes citations, rules_source, etc.)
```

---

## 3. Where the Graph Is Actually Used

| Component                        | File                                      | How it uses the Knowledge Graph                          | Output to caller                  |
|----------------------------------|-------------------------------------------|----------------------------------------------------------|-----------------------------------|
| `active_transit_rules()`         | `graph_rag/rules_provider.py`             | Reads GPD + Hora Sara nodes for planet-in-house effects  | Transit verdict tables + sources  |
| `active_muhurta_rules()`         | `graph_rag/muhurta_rules_provider.py`     | Reads Vara/Tithi/Nakshatra yoga nodes                    | Matching classical yogas          |
| `PredictionEnhancer.enhance()`   | `graph_rag/enhancer.py`                   | Full graph search for citations, conflicts, god nodes    | `transit_citations`, `yoga_citations`, etc. |
| `VedicPredictor.predict()`       | `vedic_engine/synthesis/engine.py`        | Calls muhurta rules + passes data to enhancer            | Enriched prediction object        |
| `compute_gochar()`               | `vedic_engine/prediction/gochar.py`       | Uses `active_transit_rules()` when enabled               | Gochar result with graph backing  |
| `build_report_facts()`           | `app/report_facts.py`                     | Uses `PredictionEnhancer`                                | Full report with citations        |
| `/predict`, `/orchestrate`       | `app/server.py`                           | Exposes graph-enriched data + `rules_source`             | API response                      |
| `/rules`, `/rules/{category}`    | `app/server.py`                           | Direct access to graph rules                             | Raw or filtered rules             |

---

## 4. Key Points

- The **Knowledge Graph is the source of classical Vedic laws and interpretations**.
- The **calculation engines** (PyJHora) provide the astronomical facts.
- The **GraphRAG layer** sits *on top* and supplies the "what the texts say about these facts".
- It is **not** a standalone module — it is actively injected into:
  - Transit / Gochar
  - Muhurta
  - Report generation
  - Direct rule queries
- Control is via environment variable `CVCE_GRAPH_AS_RULES` (default = true in production).

---

## 5. Data vs Computation Separation

```mermaid
flowchart LR
    subgraph Astro["Astronomical Facts (PyJHora)"]
        A1[Positions]
        A2[Houses]
        A3[Dasha periods]
        A4[Panchanga elements]
    end

    subgraph Knowledge["Classical Knowledge (Graph.json)"]
        K1[Transit effects per text]
        K2[Muhurta yogas]
        K3[Yoga definitions]
        K4[Conflicts between texts]
    end

    subgraph Synthesis["Combined Output"]
        S1["This dasha + this transit = verdict<br/>(with citation)"]
    end

    A1 & A2 & A3 & A4 --> Synthesis
    K1 & K2 & K3 & K4 --> Synthesis
```

This separation is intentional: calculations stay deterministic and precise; reasoning and classical authority come from the curated knowledge graph.

---

*Generated from actual code paths in `cvce/graph_rag/`, `vedic_engine/`, and `app/server.py` as of 2026-06-29.*
