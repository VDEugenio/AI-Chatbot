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

- [2026-05-15] Merge pull request #2 from VDEugenio/claude/nervous-mclaren-e6fddf
- [2026-05-15] Add visitor intake flow, SQLite analytics, and PostHog event tracking
- [2026-05-14] Update Pipeline data files and add frontend maintainer doc
- [2026-05-14] Add Telegram notifier, GeoIP lookup, visit endpoint, and rerank support
- [2026-05-06] Fix CI: add pull-requests write permission and add delay between API calls
- [2026-05-06] Merge pull request #1 from VDEugenio/eval-layer
- [2026-05-06] Add RAG evaluation layer with 22 test questions and CI workflow
- [2026-04-20] updated Readme
- [2026-04-20] first commit

## File Structure

- .dockerignore
- .github/
- .gitignore
- Backend/
- FRONTEND_MAINTAINER.md
- Pipeline/
- README.md
- apprunner-ecr-trust.json
- apprunner-service.example.json
- apprunner-tasks-trust.json
- test_results.txt
- tests/
