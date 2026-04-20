# syntax=docker/dockerfile:1.6
#
# Multi-stage build for the Vaughn RAG FastAPI backend.
#
# Build context MUST be the repo root (one level above Backend/) so the
# Dockerfile can pull both the Backend/ source and Pipeline/chroma_db into
# the image. From the repo root:
#
#   docker build -f Backend/Dockerfile -t vaughn-rag-backend .
#

# ---------- Stage 1: builder ----------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build deps for chromadb / hnswlib / pydantic-core wheels that may need to compile.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps into a relocatable prefix we can copy into the runtime stage.
WORKDIR /install
COPY Backend/requirements.txt .
RUN pip install --prefix=/install/deps -r requirements.txt


# ---------- Stage 2: runtime ----------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    CHROMA_DIR=/app/chroma_db

# curl is only here so HEALTHCHECK can hit /health. Tiny footprint.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser

# Pull installed Python packages from the builder stage.
COPY --from=builder /install/deps /usr/local

WORKDIR /app

# Application code.
COPY --chown=appuser:appuser Backend/app ./app

# Bake the prebuilt vector database into the image so the container is
# self-contained for AWS App Runner (no volume mount required).
COPY --chown=appuser:appuser Pipeline/chroma_db ./chroma_db

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:${PORT}/health || exit 1

# Honor $PORT so the same image works locally (8000) and on App Runner
# (which injects PORT). `sh -c` is needed for env-var expansion.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
