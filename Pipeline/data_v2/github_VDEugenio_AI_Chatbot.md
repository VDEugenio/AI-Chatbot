---
name: AI-Chatbot (GitHub Repository)
company: personal
source: github_dag
repo_url: https://github.com/VDEugenio/AI-Chatbot
topics: [github, portfolio, open_source, personal_projects]
skills: []
story_types: [project]
---

This is one of Vaughn's personal projects. **GitHub repository:** https://github.com/VDEugenio/AI-Chatbot

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

- [2026-07-14] Merge pull request #3 from VDEugenio/corpus-restructure
- [2026-07-14] fix retrieval: narrow query expansion, ingest metadata upgrades, aggregation tuning
- [2026-07-14] airflow: personal/source taxonomy in formatter, repo_url + link line, add outreach-extension to PORT
- [2026-07-14] corpus: restructure data_v2 - aggregation layer, dedupe, taxonomy + stale-fact fixes
- [2026-07-14] eval: add Q24/Q25 known-failure questions, save baseline, fix Windows UTF-8 output
- [2026-07-14] chore: sync context_asker docstrings; move frontend maintainer doc to .claude/agents
- [2026-07-14] data: expand target roles in profile overview (Sales Eng, FDE, TAM, CRE)
- [2026-07-14] feat: add local Kubernetes deployment with ChromaDB HTTP mode support
- [2026-06-30] feat: delegate tracking link lookup to outreach backend
- [2026-06-28] feat: add tracking link redirect endpoint with Telegram notifications

## File Structure

- .dockerignore
- .github/
- .gitignore
- AIRFLOW_BUILD_NOTES.md
- Backend/
- Pipeline/
- RAG_REVIEW_SYSTEM.md
- README.md
- airflow/
- apprunner-ecr-trust.json
- apprunner-service.example.json
- apprunner-tasks-trust.json
- k8s/
- test_results.txt
- tests/
