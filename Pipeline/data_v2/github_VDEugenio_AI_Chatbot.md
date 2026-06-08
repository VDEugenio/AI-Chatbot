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

- [2026-06-08] fix: pass repos and files as direct XCom args to ask_for_context
- [2026-06-08] [bot] Remove stale github_VDEugenio_adf_marketplace.md
- [2026-06-08] [bot] Remove stale github_VDEugenio_VaughnKey.md
- [2026-06-08] [bot] Remove stale github_VDEugenio_Job_Application_Tracker.md
- [2026-06-08] [bot] Remove stale github_VDEugenio_AI_Chatbot.md
- [2026-06-08] fix: remove /tmp/ file pattern, use XCom for cross-task data on Astro Cloud
- [2026-06-08] fix: data dir permissions, Bearer auth for Airflow trigger, anthropic dep
- [2026-06-08] [bot] Update github_VDEugenio_adf_marketplace.md
- [2026-06-08] [bot] Update github_VDEugenio_VaughnKey.md
- [2026-06-08] [bot] Update github_VDEugenio_Job_Application_Tracker.md

## File Structure

- .dockerignore
- .github/
- .gitignore
- AIRFLOW_BUILD_NOTES.md
- Backend/
- FRONTEND_MAINTAINER.md
- Pipeline/
- RAG_REVIEW_SYSTEM.md
- README.md
- airflow/
- apprunner-ecr-trust.json
- apprunner-service.example.json
- apprunner-tasks-trust.json
- test_results.txt
- tests/
