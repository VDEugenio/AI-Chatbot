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
- **Output**: `Pipeline/chroma_db/` (vector store) + `Pipeline/chunks_metadata.json` (inspection export)

### Backend — RAG Query Engine

A FastAPI service that handles each chat turn:

1. **Query expansion** — maps natural language to technical vocabulary (e.g., "efficient" expands to "optimized performance streamlined reduced latency") to bridge vocabulary mismatches between a user's words and document language
2. **History merging** — folds recent user turns into the query so follow-ups like "tell me more" stay on-topic
3. **Metadata pre-filtering** — detects company names in the query and restricts ChromaDB search to that company's chunks
4. **Retrieval** — three modes available:
   - **Vector-only** (default): semantic similarity search via OpenAI embeddings + ChromaDB
   - **BM25-only**: exact keyword matching via `rank_bm25` — great for proper nouns
   - **Hybrid RRF** (recommended): runs both, fuses results with Reciprocal Rank Fusion — no extra LLM call needed
5. **Prompt construction** — retrieved chunks are inlined with `[source: filename#chunk_id]` tags
6. **Answer generation** — Claude reads the evidence and generates a grounded, cited response
7. **Source return** — the API response includes the source chunks with scores and previews so clients can show citations

---

## Project Structure

```
AI-Chatbot/
├── Pipeline/                  # Document ingestion (run once)
│   ├── ingest.py              # Main ingestion script
│   ├── data_v2/               # Your source documents (.md, .txt, .pdf)
│   ├── chroma_db/             # Generated vector store (gitignored)
│   ├── requirements.txt
│   └── .env.example
│
├── Backend/                   # FastAPI service
│   ├── app/
│   │   ├── main.py            # FastAPI app + startup
│   │   ├── rag.py             # Retrieval pipeline
│   │   ├── llm.py             # Claude client
│   │   ├── bm25.py            # BM25 index
│   │   └── config.py          # Pydantic settings
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── .env.example
│
├── apprunner-service.example.json   # AWS App Runner deployment template
└── .gitignore
```

---

## Setup

### Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com)
- An [OpenAI API key](https://platform.openai.com) (for embeddings)

---

### 1. Pipeline — Ingest Documents

```bash
cd Pipeline

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

Add your documents to `Pipeline/data_v2/`. Markdown files support YAML frontmatter:

```markdown
---
name: My Experience at Acme Corp
company: acme
topics: [backend, distributed-systems]
skills: [Python, Kafka, Kubernetes]
---

Full document content here...
```

Run ingestion:

```bash
python ingest.py              # append to existing collection
python ingest.py --rebuild    # wipe and rebuild from scratch
```

This creates `Pipeline/chroma_db/` — the vector store the backend reads from.

---

### 2. Backend — Run the API

```bash
cd Backend

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env and add ANTHROPIC_API_KEY and OPENAI_API_KEY
```

Key settings in `.env` (full list in `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Required |
| `OPENAI_API_KEY` | — | Required (embeddings) |
| `CHROMA_DIR` | `../Pipeline/chroma_db` | Path to vector store |
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` | Model for answer generation |
| `TOP_K` | `8` | Chunks retrieved per query |
| `ENABLE_BM25` | `false` | Enable hybrid RRF retrieval |
| `CORS_ORIGINS` | `["http://localhost:3000","http://localhost:5173"]` | Allowed frontend origins |

Start the server:

```bash
uvicorn app.main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`.

#### API Reference

```
POST /api/chat
```

Request body:
```json
{
  "question": "What experience do you have with Kubernetes?",
  "conversation_history": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}
```

Response:
```json
{
  "answer": "...",
  "sources": [
    { "filename": "experience.md", "chunk_id": 3, "preview": "...", "score": 0.87 }
  ]
}
```

#### Debug Endpoints

```
GET  /health                   # Liveness probe + vector store status
POST /api/debug/retrieve       # Run retrieval without calling Claude (inspect chunks + scores)
POST /api/debug/compare        # Compare vector-only vs BM25 vs hybrid side-by-side
```

---

## Deployment

### Docker (local or any server)

Build from the repo root — the Dockerfile copies `Pipeline/chroma_db/` into the image:

```bash
docker build -f Backend/Dockerfile -t rag-backend .

docker run --rm -p 8000:8000 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e OPENAI_API_KEY=sk-... \
  rag-backend
```

Or with Docker Compose (reads from `Backend/.env`):

```bash
cd Backend
docker compose up --build
```

### AWS App Runner

Copy the example config and fill in your values:

```bash
cp apprunner-service.example.json apprunner-service.json
# Edit with your AWS account ID, ECR repo, and Secrets Manager ARNs
```

Push image to ECR and deploy:

```bash
# Authenticate
aws ecr get-login-password --region YOUR_REGION | \
  docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.YOUR_REGION.amazonaws.com

# Build, tag, push
docker build -f Backend/Dockerfile -t rag-backend .
docker tag rag-backend:latest YOUR_ACCOUNT_ID.dkr.ecr.YOUR_REGION.amazonaws.com/YOUR_REPO:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.YOUR_REGION.amazonaws.com/YOUR_REPO:latest

# Deploy
aws apprunner create-service --cli-input-json file://apprunner-service.json
```

The `/health` endpoint is used as the App Runner health check.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Embeddings | OpenAI `text-embedding-3-small` |
| Vector store | ChromaDB |
| Keyword search | BM25 (`rank_bm25`) |
| Retrieval fusion | Reciprocal Rank Fusion (RRF) |
| LLM | Anthropic Claude (`claude-sonnet-4-20250514`) |
| Backend | FastAPI + Python 3.11 |
| Containerization | Docker (multi-stage build) |
| Cloud | AWS App Runner + ECR + Secrets Manager |
