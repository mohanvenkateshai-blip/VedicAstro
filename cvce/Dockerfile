# VedicAstro CVCE — container image.
# Build context is the cvce/ directory so both app/ and vedic_engine/ are
# included. PyJHora ships the Swiss Ephemeris data files inside the wheel, so
# no separate ephemeris download is required; patch_pyjhora.py applies the
# runtime compatibility patches into site-packages at build time.
#
# NOTE (2026-08-22): this Dockerfile is the Fly.io fallback path — CVCE's
# live deploys are Vercel Functions (V-7, 2026-08-04/08-11), which build via
# `vercel --prod` in .github/workflows/build-and-deploy-cvce.yml, not this
# file. Kept current so the fallback still works if Fly is ever revived.

# ---- stage 1: bake graph_rag/graph.json -> knowledge_engine/graph.db ----
# (B-56 durable fix, docs/graph-sqlite-migration-playbook_1.md). Only this
# tiny stage rebuilds on a graph-only change; the app stage's layer cache is
# untouched, same benefit the playbook calls out for Docker layer caching.
FROM python:3.12-slim AS graphbuild
WORKDIR /build
COPY scripts/requirements-build.txt .
RUN pip install --no-cache-dir -r requirements-build.txt
COPY scripts/build_graph_db.py .
COPY graph_rag/graph.json .
RUN python build_graph_db.py graph.json graph.db && test -f graph.db

# ---- stage 2: app ----
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FASTEMBED_CACHE_PATH=/srv/.fastembed_cache

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libc6-dev make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

COPY requirements-prod.txt .
RUN pip install -r requirements-prod.txt

COPY . .
# graph_rag/graph.json stays in the image too (not stripped): engine.py's
# _attach_graph_compat() always builds the legacy GraphRAG accessor from the
# raw file directly, independent of which KnowledgeStore backend is active —
# removing it would silently break that existing fallback path. graph.db is
# the new addition, not a replacement.
COPY --from=graphbuild /build/graph.db knowledge_engine/graph.db

# Apply PyJHora compatibility patches (idempotent; runs a smoke test).
RUN python patch_pyjhora.py

# Pre-bake the bge-small ONNX embedding model into the image so Fly's
# ephemeral filesystem never re-downloads it on cold start (the model is
# ~130MB; baking it makes semantic-search cold starts instant + offline).
RUN python -c "from knowledge_engine.local_embedder import embed_documents; embed_documents(['warm the model cache'])"

# CORS origins, port and ayanamsa are injected at runtime via env (see .env.example).
EXPOSE 8400
CMD ["sh", "-c", "uvicorn app.server:app --host ${CVCE_HOST:-0.0.0.0} --port ${CVCE_PORT:-8400}"]
