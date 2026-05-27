---
name: AI-Chatbot (GitHub Repository)
company: github
topics: [github, portfolio, open_source]
skills: []
story_types: [project]
---

## Overview

# AI Chatbot — Personal RAG Backend

A production-ready Retrieval-Augmented Generation (RAG) backend that powers a personal AI assistant. Send it a question and it searches a vector store of personal documents, retrieves the most relevant chunks, and generates a grounded, cited answer via Claude.

The frontend (personal website + chat UI) lives in a separate repo and connects to this service via `VITE_CHAT_API_URL`.

Built with FastAPI, ChromaDB, OpenAI embeddings, and Claude (Anthropic).

---

## How It Works

```
┌─────────────┐     ┌──────────────────────────────────────┐
│  PIPELINE   │     │               BACKEND                │
│  (one-time) │     │            (FastAPI API)             │
│             │     │                                      │
│ 1. Load     │     │  POST /api/chat                      │◀──── any HTTP client
│    .md/.pdf │     │                                      │
│ 2. Chunk    │────▶│  1. Embed question (OpenAI)          │
│    docs     │     │  2. Retrieve chunks (ChromaDB)       │
│ 3. Embed    │     │     + BM25 keyword search (optional) │
│    (OpenAI) │     │     + RRF fusion                     │
│ 4. Store in │     │  3. Build prompt with cited context  │
│    ChromaDB │     │  4. Answer with Claude               │
└─────────────┘     │  5. Return answer + source chunks    │
                    └──────────────────────────────────────┘
```

### Pipeline — Document Ingestion

Run once (or whenever documents change). Reads documents from `Pipeline/data_v2/`, chunks them, embeds each chunk with OpenAI's `text-embedding-3-small`, and persists everything to a local ChromaDB vector store.

- **Supported formats**: `.md`, `.txt`, `.pdf`
- **YAML frontmatter** on markdown files (`name`, `company`, `topics`, `skills`) cascades to every chunk as filterable metadata
- **Chunk size**: 1800 characters with 200-character overlap, split on markdown headers first to keep narrative sections intact
- **Output**: `Pipeline/chroma_db/` (vector stor

## Recent Activity

- [2026-05-27] Upgrade deploy-action to v0.13.0, fix env var name
- [2026-05-27] Fix astro-deploy: add force=true for workflow_dispatch
- [2026-05-27] Fix astro-deploy: remove duplicate checkout, add root-folder: airflow
- [2026-05-27] Fix astro-deploy: remove invalid workspace-id input
- [2026-05-27] Add workflow_dispatch to astro-deploy workflow
- [2026-05-27] Add GitHub Actions workflow to deploy to Astro Cloud
- [2026-05-27] chore: update airflow .dockerignore
- [2026-05-27] Change github_ingest DAG schedule from daily to every other day
- [2026-05-26] Trigger ingest-and-deploy workflow via trivial whitespace edit
- [2026-05-26] Add Tier 2 automated ingest-and-deploy pipeline

## File Structure

- .dockerignore
- .github/
- .gitignore
- Backend/
- FRONTEND_MAINTAINER.md
- Pipeline/
- README.md
- airflow/
- apprunner-ecr-trust.json
- apprunner-service.example.json
- apprunner-tasks-trust.json
- test_results.txt
- tests/
