# VedicAstro

Modern Vedic Astrology platform with Knowledge Graph.

## Development Setup (June 2026)

This project uses `uv` + `ruff` for fast, modern Python development.

### One-time Setup

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create environment
uv venv
source .venv/bin/activate

# Install dev tools
uv pip install ruff
```

### Daily Commands

```bash
source .venv/bin/activate

# Lint
ruff check .

# Format
ruff format .

# Install a package
uv pip install <package>
```

### Legacy Files

The old `cvce/requirements*.txt` files are deprecated. All dependencies are now managed in `pyproject.toml`.

## Project Structure

- `cvce/` — FastAPI calculation engine (deployed on Fly.io)
- `portal/` — Next.js frontend (deployed on Vercel)
- `knowledge-graph/` — Knowledge Graph data and tools
- `scripts/` — Ingestion, sync, and analysis scripts

## KnowledgeEngine

The central owner of the Vedic Knowledge Graph. All engines must go through it for knowledge access.

See `docs/knowledge-engine-architecture.md` and `docs/knowledge-engine-mapping-audit.md`.