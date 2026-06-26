# Updated High-Level Architecture Diagram for VedicShastra AI
**Version 2.1 – Incorporating RBAC, Local LLM, Continuous Evolution, UI Module, and Agent Orchestration**

```mermaid
flowchart TD
    subgraph Client_Layer["Client Layer"]
        Web[Next.js Web App<br/>Fully RBAC Protected]
        Mobile[Future: Mobile Apps / PWA]
    end

    subgraph Auth_RBAC["Authentication & RBAC Layer"]
        NextAuth[NextAuth.js / JWT]
        RoleCheck[Role-Based Access Control<br/>free / pro / premium / admin]
        Quota[Subscription Quota Enforcement]
    end

    subgraph Backend["Backend Layer - FastAPI"]
        API[FastAPI + Middleware]
        CVCE[Core Vedic Calculation Engine<br/>pyswisseph + Custom Vedic Logic]
        PAE[Prediction & Analysis Engine<br/>LangGraph Stateful Workflows]
        Evolution[Continuous Evolution Loop]
    end

    subgraph Data_Layer["Data Layer"]
        Postgres[(PostgreSQL + pgvector<br/>Users • Horoscopes • Predictions<br/>Feedback • Subscriptions • Payments)]
        KnowledgeGraph[(FalkorDB / Neo4j Community<br/>Vedic Rules Knowledge Graph)]
        VectorStore[(Weaviate / Qdrant<br/>Hybrid Vector Search)]
    end

    subgraph LLM_Layer["Local LLM Layer"]
        Ollama[Ollama + MLX<br/>llama3.1:8b or qwen2.5:14b<br/>(Optimized for 24GB Mac)]
    end

    subgraph Orchestration["Agent Orchestration Layer (Build Phase)"]
        Ruflo[ruflo Multi-Agent Swarm]
        DeepTrilogy[Deep Trilogy Workflow<br/>deep-project → deep-plan → deep-implement]
        Graphify[Graphify<br/>Text → Knowledge Graph Extraction]
    end

    subgraph UI_Layer["UI Design & Frontend Module (Chunk 13)"]
        DESIGN[DESIGN.md<br/>Design System Enforcer]
        FramerMotion[Framer Motion<br/>Premium Animations]
        MagicMCP[21st.dev Magic MCP<br/>Rapid Component Generation]
        InteractiveCharts[Interactive Horoscope Charts<br/>North & South Indian Styles]
    end

    subgraph Admin_Evolution["Admin Dashboard & Evolution System"]
        FeedbackReview[Feedback Review<br/>Prediction + UI/UX]
        RuleApproval[Rule Approval & Graph Updates]
        RootCause[Root Cause Analysis with Full Context]
    end

    %% Connections
    Web --> Auth_RBAC
    Auth_RBAC --> API
    API --> CVCE
    API --> PAE
    PAE --> Evolution
    Evolution --> Postgres
    PAE --> KnowledgeGraph
    PAE --> VectorStore
    CVCE --> Ollama
    PAE --> Ollama

    Ruflo --> Graphify
    Graphify --> KnowledgeGraph
    Ruflo --> DeepTrilogy
    DeepTrilogy --> UI_Layer

    UI_Layer --> DESIGN
    UI_Layer --> FramerMotion
    UI_Layer --> MagicMCP
    UI_Layer --> InteractiveCharts

    Admin_Evolution --> Postgres
    Admin_Evolution --> KnowledgeGraph
    Admin_Evolution --> FeedbackReview

    style Ruflo fill:#e0f2fe
    style Graphify fill:#fef3c7
    style KnowledgeGraph fill:#dcfce7
    style PAE fill:#fce7f3
    style UI_Layer fill:#ede9fe
    style Evolution fill:#fefce8
```

## Key Highlights of This Architecture

- **RBAC enforced at every layer**
- **Continuous Evolution Loop** is a first-class citizen
- **Hybrid Knowledge Graph + Vector Store** for rules
- **Local LLM** optimized for your hardware
- **UI Module (Chunk 13)** with strong design system enforcement
- **Agent Orchestration** using ruflo + Deep Trilogy for high-quality development
- Clean separation between build-time agents and runtime prediction flow

This diagram reflects all requirements discussed: RBAC, PostgreSQL, local LLM on 24GB Mac, UI strategy, evolution loop, Graphify, ruflo, and premium frontend experience.