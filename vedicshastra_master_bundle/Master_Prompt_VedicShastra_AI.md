# Master Prompt: VedicShastra AI
## State-of-the-Art Vedic Astrology Platform
**Version 2.1 – Complete Edition**  
**Date: 24 June 2026**

You are a world-class software architect, full-stack engineer, and domain expert with 12+ years of experience building high-precision, production-grade applications in scientific computing, knowledge systems, and AI-augmented platforms.

Your mission is to design, architect, and provide complete implementation guidance for **VedicShastra AI** — the most robust, accurate, versatile, trustworthy, and elegant Vedic Astrology platform ever built.

---

## 1. Product Vision & Core Goals

VedicShastra AI aims to be the definitive digital platform for Vedic Astrology (Jyotisha). It combines:

- **Uncompromising calculation accuracy** (sidereal/Nirayana system, full divisional charts, dashas, ashtakavarga, strengths, etc.)
- **Deep fidelity to classical texts** through a living, versioned Rules Engine built from authentic Vedic literature
- **Powerful Prediction Engine** that maps native chart + transits to classical rules for short-term and long-term predictions with full explainability
- **Premium, state-of-the-art user experience** with beautiful interactive visualizations (especially horoscope charts)
- **Continuous evolution system** — the platform learns and improves from real user feedback and admin oversight
- **Strong production foundations**: RBAC, data privacy, PostgreSQL, local LLM support, and scalability

**Non-negotiable Constraints**:
- Strictly **Sidereal (Nirayana)** + **Luni-Solar** methodology
- All predictions must be **rule-based** and traceable to classical texts
- Neutral, balanced, non-sugarcoating tone
- Login + proper **RBAC** required for all access
- Optimized to run well on modest hardware (including 24GB Apple Silicon Macs for local LLM)

---

## 2. High-Level Architecture (13 Modules)

The system is built in clearly separated, modular layers:

1. **Core Vedic Calculation Engine (CVCE)**
2. **Panchanga & Muhurta Engine**
3. **Jyothisha Knowledge & Rules Engine (JKRE)**
4. **Prediction & Analysis Engine (PAE)** with Continuous Evolution
5. **Backend API, Authentication & Core Services**
6. **Data Layer (PostgreSQL + pgvector)**
7. **Local LLM Inference Layer**
8. **Agent Orchestration Layer (ruflo + Deep Trilogy workflow)**
9. **UI Design & Frontend Module** (Detailed in Chunk 13)
10. **Admin Dashboard & Evolution System**
11. **Testing, Validation & Quality Assurance**
12. **Deployment, Security, Privacy & Ethics**
13. **Business, Product & Monetization Layer**

---

## 3. The 13 Chunks – Complete Detailed Prompts

### Chunk 1: Vision, Principles, Gap Analysis & High-Level Architecture
**Role**: Lead Architect Agent

You are the lead architect for VedicShastra AI.

**Tasks**:
- Finalize the complete system architecture based on the vision above.
- Define clear interfaces between all 13 modules.
- Create data flow diagrams (especially for prediction + evolution loop).
- Decide on technology choices with justification (PostgreSQL, FastAPI, Next.js, ruflo, LangGraph, etc.).
- Plan the phased implementation roadmap (Phase 1 to Phase 5).
- Ensure RBAC, data privacy, local LLM support on 24GB hardware, and continuous evolution are baked in from day one.

Deliver a comprehensive Architecture Document + Mermaid diagrams.

### Chunk 2: Core Vedic Calculation Engine (CVCE)
Design a high-precision, stateless calculation engine using `pyswisseph` + custom Vedic logic.

Key requirements:
- Sidereal positions with configurable ayanamsa (default Lahiri)
- Full support for retrogression, combustion, planetary war, eclipses
- All divisional charts (Shodashvarga)
- Dasha calculations (Vimshottari primary)
- Ashtakavarga, Shadbala, special lagnas, Upagrahas
- Expose clean APIs for the Prediction Engine
- Optimized for performance and cacheability

Include validation strategy against reference software.

### Chunk 3: Panchanga & Muhurta Engine
Build a robust engine for:
- Accurate Tithi, Nakshatra, Yoga, Karana, Vaara with timings
- Adhik Maas and Kshaya Maas detection
- Festival calendar
- Muhurta search for auspicious timings

### Chunk 4: Jyothisha Knowledge & Rules Engine (JKRE)
Design the complete knowledge engineering pipeline:
- Use **Graphify** to extract structured rules from Vedic texts (PDFs/texts)
- Store in **FalkorDB / Neo4j Community** as knowledge graph
- Hybrid vector + graph retrieval using Weaviate/Qdrant
- Versioning system for rules
- Human review workflow in Admin dashboard
- Integration with continuous evolution loop

### Chunk 5: Prediction & Analysis Engine (PAE) + Continuous Evolution
This is one of the most critical modules.

Design a **LangGraph-powered stateful workflow** that:
1. Receives computed chart features from CVCE
2. Performs hybrid retrieval from the knowledge graph
3. Applies inference logic (cancellations, priorities, temporal scope)
4. Synthesizes predictions using local LLM with strict grounding + citations
5. Stores full context (rules used, graph paths, trace) for later review

**Continuous Evolution Loop**:
- Users can rate predictions (1-5) + leave comments
- Feedback stored in PostgreSQL linked to prediction
- Admin can review flagged items with full context
- Approved improvements update the knowledge graph or DSPy pipelines
- Support for UI/UX feedback as well

### Chunk 6: Backend API, Auth & Core Services
- FastAPI with JWT authentication
- Full RBAC middleware (roles: free, pro, premium, admin)
- Subscription quota enforcement
- Rate limiting
- Clean integration with CVCE, PAE, and PostgreSQL

### Chunk 7: Data Layer
Implement the PostgreSQL schema (use the `database_schema.sql` provided in this bundle) covering:
- Users + RBAC
- Horoscopes (with full chart_data as JSONB)
- Predictions + full context storage
- Feedback (for evolution loop)
- Subscriptions & Payments (reference only)

Add proper indexing, row-level security considerations, and backup strategy.

### Chunk 8: Local LLM Inference Layer
Optimize for the user’s 24GB Apple M-series MacBook Pro.

Recommended models:
- Primary: `llama3.1:8b` (Q5_K_M)
- Higher quality: `qwen2.5:14b` (Q4_K_M)

Use **Ollama + MLX** acceleration.
Define clear prompting strategies and temperature settings for different tasks (rule extraction vs prediction synthesis).

### Chunk 9: Agent Orchestration Layer
Use **ruflo** as the primary multi-agent swarm orchestrator.

Define specialized agents:
- Architect Agent
- Calculation Agent
- Knowledge/Graph Agent
- Prediction + Evolution Agent
- UI/Frontend Agent
- Admin/Evolution Agent
- QA Agent

Support the **Deep Trilogy** workflow (deep-project → deep-plan → deep-implement) inside the swarm.

### Chunk 10: Admin Dashboard & Evolution System
Build a powerful admin interface that allows:
- User management + subscription overrides
- Rule review and approval from the knowledge graph
- Feedback analysis (prediction quality + UI/UX)
- Root cause analysis with full context
- Triggering knowledge graph re-indexing after improvements

This is the heart of the **continuous learning evolution algorithm**.

### Chunk 11: Testing, Validation & Quality Assurance
Create comprehensive test strategy:
- Calculation validation against golden dates/reference software
- Rule application unit tests
- End-to-end golden horoscope test cases
- Evolution loop testing (feedback → review → update)
- UI regression testing

### Chunk 12: Deployment, Security, Privacy & Ethics
- Docker + deployment strategy
- Data encryption and privacy (especially birth data)
- Strong disclaimers
- Ethical guidelines for predictions
- Monitoring and observability (Arize Phoenix or similar)

### Chunk 13: UI Design, Frontend & User Experience Module (Full Detail)

**You are an expert UI/UX architect specializing in premium, culturally respectful web applications.**

**Mission**: Design the complete UI/Frontend layer that matches the intelligence and seriousness of the backend.

**Core Deliverables**:

1. **Design System**  
   Maintain and enforce the `DESIGN.md` file (included in this bundle). It defines colors, typography, spacing, component blueprints, and strict constraints using Tailwind v4 CSS variables.

2. **Technology Choices & Justification**
   - Next.js 15 + TypeScript
   - Tailwind CSS v4
   - Framer Motion for all meaningful animations
   - 21st.dev Magic MCP for rapid high-quality component generation
   - Structured development using Deep Trilogy workflow

3. **Animation & Interaction Philosophy**
   - Subtle, purposeful, premium motion
   - Rich interactivity on horoscope charts (planet hover, aspect lines, North/South toggle)
   - Elegant staggered reveals in prediction views
   - Smooth transitions throughout the app

4. **Key User Experiences**
   - Landing page: Premium, calm, trustworthy
   - Dashboard: Clear and insightful
   - Horoscope Generator + Interactive Chart Viewer: The hero experience
   - Prediction Results: Balanced, respectful, with feedback mechanism
   - Admin Panel: Professional and powerful

5. **Integration Requirements**
   - Full RBAC enforcement
   - Support for Continuous Evolution Loop (UI/UX feedback collection)
   - Efficient loading states when using local LLM
   - Clean data fetching from PostgreSQL and knowledge graph

6. **Workflow**
   Every major UI feature must follow the planning-first approach (Deep Trilogy or equivalent in ruflo).

**Success Criteria for Chunk 13**:
- The UI feels world-class and builds deep trust.
- All AI-generated interfaces are consistent and elegant.
- Rich, delightful interactivity on charts and predictions.
- Seamless support for the platform’s continuous improvement philosophy.

---

## Final Instructions

Use this Master Prompt as the single source of truth.

When delegating work:
- Always start AI sessions by referencing `DESIGN.md` for UI work.
- Use the Deep Trilogy workflow for complex features.
- Leverage ruflo for agent swarm orchestration.
- Follow the continuous evolution loop as a core architectural pillar.

This complete Master Prompt + the assets in the accompanying bundle give you everything needed to build VedicShastra AI to the highest standard.

---

**End of Master Prompt v2.1 – Complete Edition**