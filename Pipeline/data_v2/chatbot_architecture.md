---
name: AI Resume Chatbot — System Architecture
description: Full technical architecture of the chatbot and portfolio site — FastAPI backend, React frontend, ChromaDB vector store, OpenAI embeddings, Claude LLM, Docker, and AWS App Runner deployment.
company: personal
topics: [system_architecture, backend, frontend, deployment, cloud_infrastructure, api_design]
skills: [FastAPI, React, TypeScript, Docker, AWS, ChromaDB, OpenAI, Anthropic, python, pydantic]
story_types: [architecture_design, systems_thinking]
related_files: [chatbot_overview.md, chatbot_rag_pipeline.md, chatbot_frontend.md]
---

# AI Resume Chatbot — System Architecture

## System Overview

```
Browser (React + TypeScript + Tailwind)
    ↓ HTTP POST /api/chat
FastAPI Backend (Python)
    ├── OpenAI Embeddings (text-embedding-3-small)
    │       ↓
    ├── ChromaDB Vector Store  ←── Pipeline/ingest.py builds this
    ├── BM25 In-Memory Index   ←── Built from ChromaDB at startup
    └── Anthropic Claude API   ←── claude-sonnet-4 for generation
```

Every chat request triggers this sequence:
1. The question is expanded with synonym/entity groups and embedded by OpenAI
2. RRF hybrid retrieval fuses vector + BM25 results
3. Company-level metadata pre-filtering narrows the search space for role-specific questions
4. Retrieved chunks are formatted into a context block and sent to Claude
5. Claude generates a grounded response; sources are returned to the frontend

## Backend — FastAPI

**Framework:** FastAPI (Python 3.10+) with Pydantic settings  
**Server:** Uvicorn

### Endpoints
| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness probe — reports vectorstore loaded status and chunk count |
| `POST /api/chat` | Main chat endpoint — RAG retrieval + Claude generation |
| `POST /api/debug/retrieve` | Returns full retrieval trace (chunks, scores, expansions) without LLM call |
| `POST /api/debug/compare` | Side-by-side comparison of vector, BM25, and hybrid retrieval for a query |

### Configuration (Pydantic Settings via .env)
All runtime behavior is controlled through environment variables — no hardcoded values:
- `CLAUDE_MODEL` — Anthropic model ID
- `EMBEDDING_MODEL` — OpenAI embedding model
- `TOP_K` — number of chunks retrieved per query
- `ENABLE_BM25` — enables RRF hybrid retrieval (on by default)
- `TEMPERATURE` — LLM temperature (0.0 for factual grounding)
- `ENABLE_QUERY_EXPANSION` — synonym-based query enrichment
- `CORS_ORIGINS` — allowed frontend origins

### Key Components
- **`app/rag.py`** — retrieval logic: vector search, BM25, RRF fusion, query expansion, company filtering, prompt assembly
- **`app/bm25.py`** — BM25 index built in-memory from ChromaDB at startup
- **`app/llm.py`** — Claude client wrapper with reranking support
- **`app/config.py`** — typed settings loaded from `.env`

## Frontend — React Portfolio + Chat Widget

**Stack:** React 18, TypeScript, Vite, Tailwind CSS

The frontend has two main components that live side-by-side:

### Portfolio Drawer (`PortfolioDrawer.tsx`)
A sidebar (or expandable drawer on mobile) displaying:
- Work experience timeline with company, role, and dates
- Personal projects (see projects_index.md for the full list)
- Skills and tech stack inventory
- Contact information and social links (LinkedIn, GitHub, email)

### Chat Widget (`ChatWidget.tsx`)
- Multi-turn conversation with automatic scroll
- Loading indicator while waiting for Claude
- Source attribution chips showing which files were retrieved
- Greeting message on load
- Message history sent to backend for conversational context

The frontend is packaged as a reusable chat widget component in `/Chat Widget/` so it can be embedded in external React apps.

## Data Pipeline — `Pipeline/ingest.py`

The ingestion pipeline builds the ChromaDB vector store from the knowledge base:

1. **Load** — reads all `.md` / `.pdf` / `.txt` files from `data_v2/`
2. **Parse frontmatter** — extracts YAML metadata (`company`, `topics`, `skills`, `story_types`) and stores on every chunk
3. **Chunk** — header-aware splitting that keeps narrative sections intact (the chunking strategy and its parameters are covered in the RAG pipeline design — see `chatbot_rag_pipeline.md`)
4. **Embed** — sends chunks to OpenAI `text-embedding-3-small`
5. **Store** — persists to ChromaDB; deletes the existing collection first to prevent accumulation

Re-ingestion is a single command: `python ingest.py`

## Deployment

**Containerization:** Docker multi-stage build  
**Registry:** AWS ECR  
**Runtime:** AWS App Runner (auto-scaling, managed TLS, no server management)

The backend container includes the ChromaDB vector store baked in at build time. The frontend is built as a static bundle and served separately. App Runner handles scaling, health checks, and HTTPS automatically.

Environment secrets (API keys) are injected via App Runner environment variable configuration, not baked into the image.
