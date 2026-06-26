# Free Stack Quick Start Guide for VedicShastra AI (Your 24GB MacBook Pro)

## Recommended Local Models
- Primary: `llama3.1:8b` (Q5_K_M) - Fast and capable
- Higher quality: `qwen2.5:14b` (Q4_K_M)

## Step-by-Step Setup

### 1. Install Ollama (Local LLM)
```bash
brew install ollama
ollama serve
ollama pull llama3.1:8b
```

### 2. Create Project
```bash
npx create-next-app@latest vedicshastra-ai --yes
cd vedicshastra-ai
```

### 3. Install Core Dependencies
```bash
npm install framer-motion
npm install tailwindcss@latest
```

### 4. Add DESIGN.md
Copy the `DESIGN.md` from this bundle into your project root.

### 5. Install ruflo (Agent Orchestration)
```bash
npx ruflo@latest init
```

### 6. (Optional but Recommended) Add 21st.dev Magic MCP
```bash
claude mcp add @21st-dev/magic
```

### 7. Database
Use Docker for PostgreSQL + pgvector:
```yaml
# docker-compose.yml (basic)
version: '3.8'
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: vedic
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: vedicshastra
    ports:
      - "5432:5432"
```

Run `docker compose up -d`

Then run the `database_schema.sql` from this bundle.

### 8. Start Building
Begin with **Chunk 13 (UI)** and **Chunk 2 (CVCE)** in parallel.

Use the Deep Trilogy workflow for all major features.

---

You now have a complete free/local foundation. 

Happy building!