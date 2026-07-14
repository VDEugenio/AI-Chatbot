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

- [2026-06-15] chore: update Claude model to claude-sonnet-4-6 (retire claude-sonnet-4-20250514)
- [2026-06-09] [bot] Enrich 4 RAG file(s) with developer notes
- [2026-06-09] [bot] Update github_VDEugenio_adf_marketplace.md
- [2026-06-09] [bot] Update github_VDEugenio_VaughnKey.md
- [2026-06-09] [bot] Update github_VDEugenio_Job_Application_Tracker.md
- [2026-06-09] [bot] Update github_VDEugenio_AI_Chatbot.md
- [2026-06-09] [bot] Enrich 4 RAG file(s) with developer notes
- [2026-06-09] [bot] Update github_VDEugenio_adf_marketplace.md
- [2026-06-09] [bot] Update github_VDEugenio_VaughnKey.md
- [2026-06-09] [bot] Update github_VDEugenio_Job_Application_Tracker.md

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

## Developer Notes

The AI Chatbot represents a fully production-ready RAG system with careful attention to both technical implementation and operational deployment. The developer chose a 1800-character chunk size as a key design decision for balancing context coherence with retrieval precision.

The infrastructure architecture demonstrates a stateless, container-first approach. The entire system runs on AWS App Runner in us-east-1, with ChromaDB embedded directly into the Docker image rather than running as a separate service. This design choice trades some operational flexibility for deployment simplicity and reproducibility—the vector store is baked into the container at build time and stored in AWS ECR with auto-incrementing version tags.

The corpus update workflow showcases sophisticated automation with human oversight. An Airflow DAG scrapes GitHub repositories and commits updates, triggering a GitHub Actions pipeline that rebuilds ChromaDB from scratch, validates the results, and packages everything into a new Docker image. Crucially, the deployment includes a manual approval gate via GitHub Environments, allowing inspection of ingest results before production deployment. The system provides comprehensive monitoring through Telegram notifications and health checks that verify chunk counts after deployment.

This architecture prioritizes reproducibility and safety over real-time updates, making it well-suited for a personal knowledge base where accuracy and reliability matter more than instant corpus synchronization.