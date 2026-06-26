# VedicAstro — Complete System Architecture

## Flow Diagram

```mermaid
graph TB
    subgraph User["👤 User Browser"]
        direction LR
        A[Opens portal-omega-two-10.vercel.app/vedicastro]
        B[Enters DOB + Place in BirthForm]
        C[Views Chart + Explorers + Predictions]
    end

    subgraph Portal["🎨 Portal (Vercel) · Next.js 16 · React 19"]
        direction TB
        PC[vedicastro/page.tsx<br/>Server Component]
        BF[BirthForm.tsx<br/>DOB + Place + Presets]
        CV[ChartViewer<br/>North/South · D1-D60]
        KC[KundaliChart<br/>SVG Kundali]

        subgraph Explorers["🧭 Explorers Panel"]
            NE[NakshatraExplorer<br/>27 stars · filterable]
            RE[RashiExplorer<br/>12 signs · dignity table]
            DD[DashaDeepTree<br/>5-level Vimshottari]
            AD[AllDashasPanel<br/>Vim+Yog+Ash]
            VP[VarshaphalaPanel<br/>Solar Return]
            SP[SpecialPointsPanel<br/>Bindu·Mandi·Gulika]
            KM[KootaMatcher<br/>36-point compatibility]
            AT[AnimatedTransitEngine<br/>12-month timeline]
            GE[GraphicalEphemeris<br/>SVG year view]
            KP[KPExplorer<br/>Placidus cusps]
            MC[MultiChartWorksheet<br/>D1/D9/D10/D12]
            PD[ExportPDFButton<br/>Print/PDF]
        end

        GI[GraphInsights<br/>Transit·Yoga·Conflicts·God Nodes]
        SB[SaveChartButton → Neon DB]
        AU[Auth · NextAuth v5 Google OAuth]
        DB[(Neon Postgres<br/>users + horoscopes)]
    end

    subgraph CVCE["🔧 CVCE (Fly.io) · Python 3.12 · FastAPI"]
        direction TB

        subgraph ORCH["🎯 Orchestration Engine"]
            OR[POST /orchestrate<br/>Routes query → engine]
            OM[GET /orchestrate/manifest<br/>Engine registry]
            OF[GET /orchestrate/engine/{name}<br/>Engine capability lookup]
        end

        subgraph ENGINES["⚙️ 8 Servant Engines"]
            JK[Janma Kundali<br/>POST /chart<br/>Full birth chart]
            GP[Gochar Phala<br/>POST /predict<br/>Transit predictions]
            DP[Dasha Phala<br/>POST /dashas<br/>Multi-system dasha]
            YP[Yoga Phala<br/>POST /yogas<br/>284-yoga detection]
            BN[Bala Nirnaya<br/>POST /shadbala<br/>Planetary strength]
            MN[Muhurta Nirnaya<br/>MuhurtaCosmos standalone<br/>Electional windows]
            KM2[Koota Milan<br/>POST /koota-match<br/>Compatibility]
            SPM[Shastra Pramana<br/>POST /rules/query<br/>Classical citations]
        end

        subgraph CORE["📦 Core Modules"]
            RE2[Rules Engine<br/>rules.json · O(1) lookups]
            GR[GraphRAG<br/>graph.json · 553 nodes]
            EP[Ephem Engine<br/>PyJHora · Swiss Ephemeris]
            CH[Chart Geometry<br/>D1-D60 · Ashtakavarga]
        end
    end

    subgraph INFRA["☁️ Infrastructure"]
        VERCEL[Vercel · Global CDN<br/>portal-omega-two-10.vercel.app]
        FLY[Fly.io · London · 1GB VM<br/>vedicastro-cvce.fly.dev]
        NEON[Neon · Serverless Postgres<br/>users + horoscopes + RLS]
        GOOGLE[Google OAuth<br/>AUTH_GOOGLE_ID/SECRET]
        MUHURTA[Muhurta Standalone<br/>muhurtha.uvwx.me · Fly.io]
    end

    subgraph DATA["📚 Data Sources"]
        RJ[rules.json<br/>All astrological rules · Single truth]
        GJ[graph.json<br/>Knowledge graph · 4 classical texts]
        SE[Swiss Ephemeris<br/>NASA JPL · 4700BC-5400AD]
    end

    %% User → Portal
    A --> B --> PC
    PC -->|getChart()| JK
    PC -->|getGraphInsights()| GP
    PC --> CV --> KC
    PC --> GI
    PC --> SB --> DB
    PC -->|on vedicastro page| Explorers

    %% Portal → CVCE
    PC -->|"POST /chart"| JK
    PC -->|"POST /predict"| GP
    DD -->|"POST /dashas"| DP
    AD -->|"POST /dashas"| DP
    SP -->|"POST /special-points"| CVCE
    KM -->|"POST /koota-match"| KM2
    KP -->|"POST /kp-system"| CVCE
    VP -->|"POST /varshaphala"| CVCE
    AT -->|"POST /positions ×12"| CVCE
    GE -->|"POST /positions ×12"| CVCE

    %% CVCE Internal
    OR --> JK & GP & DP & YP & BN & KM2 & SPM
    JK --> EP & CH
    GP --> RE2 & GR
    DP --> RE2
    YP --> RE2
    BN --> RE2 & EP
    KM2 --> RE2
    SPM --> GR & RE2
    RE2 --> RJ
    GR --> GJ
    EP --> SE

    %% Explorers → CVCE
    NE -.->|static data| RJ
    RE -.->|static data| RJ
    MC -->|existing KundaliChart| KC

    %% Infrastructure
    PC -.-> VERCEL
    JK -.-> FLY
    GP -.-> FLY
    DP -.-> FLY
    SB -.-> NEON
    AU --> GOOGLE
    MN -.-> MUHURTA

    style OR fill:#8b5cf6,color:#fff
    style RE2 fill:#f59e0b,color:#000
    style GR fill:#5EE6D0,color:#000
    style JK fill:#6366f1,color:#fff
    style GP fill:#6366f1,color:#fff
    style DP fill:#6366f1,color:#fff
    style YP fill:#6366f1,color:#fff
    style BN fill:#6366f1,color:#fff
    style KM2 fill:#6366f1,color:#fff
    style SPM fill:#6366f1,color:#fff
    style MN fill:#6366f1,color:#fff
    style RJ fill:#f59e0b,color:#000
    style GJ fill:#5EE6D0,color:#000
    style SE fill:#4ade80,color:#000
```

## Query Flow: "What will happen to me today?"

```
User types "What will happen to me today?"
        │
        ▼
POST /orchestrate {query: "what will happen to me today?"}
        │
        ▼
Orchestrator resolves keywords: "today", "prediction", "transit", "gochar"
        │
        ▼ matches Gochar Phala Engine (score: 2 matched keywords)
        │
        ▼
POST /predict {chart_data, date, time}
        │
        ├─► Rules Engine: transit("Jupiter", 5) → "good"
        ├─► Rules Engine: vedha_check("Sun", 3) → "cancelled by house 12"
        ├─► Rules Engine: moorthi(8) → "Loha (Iron) — worst"
        ├─► Rules Engine: tara("Purva Phalguni", "Swati") → "Pratyak Tara"
        ├─► GraphRAG: transit_effects("Jupiter", 5) → classical text citations
        │
        ▼
Returns: {verdict: "Mixed", score: 5, transit_breakdown: [...], warnings: [...], graph_citations: [...]}
```

## Engine Dependency Chain

```
Janma Kundali (base — all others depend on it)
    ├─► Gochar Phala (needs birth chart + query date)
    │       └─► Muhurta Nirnaya (needs transit + birth)
    ├─► Dasha Phala (needs birth chart + query date)
    ├─► Yoga Phala (needs birth chart only)
    ├─► Bala Nirnaya (needs birth chart only)
    ├─► Koota Milan (needs two birth charts)
    └─► Shastra Pramana (needs concept/rule name)

All engines query:
    ├─► Rules Engine (rules.json) — for rule lookups
    └─► GraphRAG (graph.json) — for classical citations
```

## Data Architecture

```
rules.json (20KB)                    graph.json (835KB)
    ├─ transit rules                     ├─ 553 nodes
    ├─ panchanga rules                   ├─ 1439 links
    ├─ yoga rules                        ├─ 45 hyperedges
    ├─ dasha rules                       ├─ 36 communities
    └─ dignity rules                     └─ 4 classical texts

    │                                        │
    ▼                                        ▼
Rules Engine (O(1) lookups)          GraphRAG (semantic search)
    │                                        │
    └────────────────┬───────────────────────┘
                     │
                     ▼
              Prediction Output
         {verdict, score, factors, warnings, citations}
```

## Infrastructure Map

```
https://portal-omega-two-10.vercel.app (Vercel)
    │
    ├─► https://vedicastro-cvce.fly.dev (Fly.io · London)
    │       ├─ [Ephemeris: PyJHora → Swiss Ephemeris JPL]
    │       ├─ [Rules: rules.json · in-memory]
    │       └─ [Graph: graph.json · in-memory]
    │
    ├─► https://muhurtha.uvwx.me (Fly.io · US East)
    │       └─ [MuhurtaCosmos standalone · Frozen]
    │
    ├─► Neon Postgres (serverless)
    │       ├─ users table
    │       └─ horoscopes table (AES-256-GCM encrypted PII)
    │
    └─► Google OAuth (NextAuth v5)
            └─ session JWT cookie
```
