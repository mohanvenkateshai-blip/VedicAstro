# VedicAstro CVCE — container image.
# Build context is the cvce/ directory so both app/ and vedic_engine/ are
# included. PyJHora ships the Swiss Ephemeris data files inside the wheel, so
# no separate ephemeris download is required; patch_pyjhora.py applies the
# runtime compatibility patches into site-packages at build time.
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

# Apply PyJHora compatibility patches (idempotent; runs a smoke test).
RUN python patch_pyjhora.py

# Pre-bake the bge-small ONNX embedding model into the image so Fly's
# ephemeral filesystem never re-downloads it on cold start (the model is
# ~130MB; baking it makes semantic-search cold starts instant + offline).
RUN python -c "from knowledge_engine.local_embedder import embed_documents; embed_documents(['warm the model cache'])"

# CORS origins, port and ayanamsa are injected at runtime via env (see .env.example).
EXPOSE 8400
CMD ["sh", "-c", "uvicorn app.server:app --host ${CVCE_HOST:-0.0.0.0} --port ${CVCE_PORT:-8400}"]
