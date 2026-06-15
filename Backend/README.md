# Vaughn RAG Backend

A FastAPI service that answers questions about Vaughn by retrieving relevant
chunks from a local ChromaDB vector store and passing them to Anthropic's
Claude API.

## Architecture

```
client ──HTTP──▶ FastAPI (/api/chat)
                    │
                    ├─▶ OpenAI embeddings (embed question)
                    ├─▶ ChromaDB (similarity search, top-k)
                    └─▶ Claude (claude-sonnet-4-6)
```

The vector store is the one produced by `../Pipeline/ingest.py`. The
collection name and embedding model are kept in sync via environment
variables — do not change them on one side without updating the other.

## Prerequisites

1. Python 3.10+
2. The Chroma store has been built: from the repo root run
   ```
   cd Pipeline
   python ingest.py
   ```
   This must produce `Pipeline/chroma_db/`.
3. API keys for **Anthropic** and **OpenAI**.

## Setup

```bash
cd Backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env       # then edit .env and fill in your keys
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

On startup you should see something like:

```
[INFO] vaughn-rag: Vectorstore loaded: 137 chunks
[INFO] vaughn-rag: Anthropic client initialized (model=claude-sonnet-4-6)
```

Interactive API docs (Swagger UI): http://localhost:8000/docs

## Endpoints

### `GET /health`
Returns service status and the number of chunks loaded.

```json
{ "status": "ok", "vectorstore_loaded": true, "chunk_count": 137 }
```

### `POST /api/chat`

Supports multi-turn conversations. The backend is **stateless** — the
frontend owns the history list and sends it on every request.

Request:
```json
{
  "question": "What experience does Vaughn have with Kubernetes?",
  "conversation_history": [
    { "role": "user",      "content": "What technologies does Vaughn know?" },
    { "role": "assistant", "content": "Vaughn has experience with Python, C#, Java..." }
  ]
}
```

`conversation_history` is optional (omit or pass `[]` for the first turn).
Each entry must have `role` of `"user"` or `"assistant"` and a non-empty
`content`. Only the last **20** messages are forwarded to Claude; older
turns are dropped to keep the request bounded.

How history is used:
- **Retrieval**: the most recent few turns are concatenated with the current
  question before being embedded, so short follow-ups like *"tell me more"*
  or *"what else?"* still retrieve thread-relevant chunks.
- **Generation**: the full (truncated) history is forwarded to Claude as a
  multi-turn `messages` array, with the current user turn carrying the
  freshly-retrieved RAG context.

Response:
```json
{
  "answer": "Vaughn has ...",
  "sources": [
    { "filename": "resume.pdf", "chunk_id": 3, "preview": "..." }
  ]
}
```

## Test with curl

```bash
# Health check
curl http://localhost:8000/health

# Ask a question (first turn — no history)
curl -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"question":"What technologies does Vaughn know?"}'

# Follow-up turn — frontend echoes prior turns back to the server
curl -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{
       "question": "Tell me more about his Kubernetes experience.",
       "conversation_history": [
         {"role": "user", "content": "What technologies does Vaughn know?"},
         {"role": "assistant", "content": "Vaughn has experience with Python, C#, Java, and Kubernetes..."}
       ]
     }'

# Validation error (empty question)
curl -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"question":""}'
```

On Windows `cmd.exe`, escape the inner quotes:
```bat
curl -X POST http://localhost:8000/api/chat ^
     -H "Content-Type: application/json" ^
     -d "{\"question\":\"What experience does Vaughn have?\"}"
```

## Configuration reference

| Env var            | Default                       | Notes                                         |
| ------------------ | ----------------------------- | --------------------------------------------- |
| `ANTHROPIC_API_KEY`| —                             | Required.                                     |
| `OPENAI_API_KEY`   | —                             | Required (used to embed incoming questions). |
| `CHROMA_DIR`       | `../Pipeline/chroma_db`       | Path to the persisted Chroma directory.       |
| `COLLECTION_NAME`  | `vaughn_personal_docs`        | Must match `ingest.py`.                       |
| `EMBEDDING_MODEL`  | `text-embedding-3-small`      | Must match `ingest.py`.                       |
| `CLAUDE_MODEL`     | `claude-sonnet-4-6`    | Anthropic model id.                           |
| `MAX_TOKENS`       | `1024`                        | Cap on Claude response length.                |
| `TEMPERATURE`      | `0.2`                         | Lower = more deterministic.                   |
| `TOP_K`            | `10`                          | Number of chunks retrieved per question.      |
| `MIN_SIMILARITY_SCORE` | *(unset)*                 | Optional [0,1] floor; drops weak matches.     |
| `ENABLE_QUERY_EXPANSION` | `true`                  | Append synonym lists to queries (see below).  |
| `ENABLE_BM25`      | `false`                       | Default retriever for `/api/chat`. `true` = BM25 + rerank. |
| `BM25_CANDIDATES`  | `25`                          | First-stage candidate pool size for BM25.     |
| `RERANK_TOP_K`     | `8`                           | Chunks kept after Claude rerank.              |
| `RERANK_MODEL`     | *(unset → CLAUDE_MODEL)*      | Override the model used for reranking.        |
| `CORS_ORIGINS`     | `["*"]`                       | JSON array of allowed frontend origins.       |
| `TELEGRAM_BOT_TOKEN` | *(unset)*                   | From @BotFather. Notifications no-op without it. |
| `TELEGRAM_CHAT_ID` | *(unset)*                     | Your chat id from @userinfobot.               |
| `ENABLE_TELEGRAM_NOTIFICATIONS` | `true`           | Master switch for Telegram notifications.     |
| `VISIT_THROTTLE_SECONDS` | `3600`                  | Per-IP+path throttle window for `/api/visit`. |

## Retrieval & debugging

The backend ships with three retrieval-quality levers and a debug endpoint
that lets you inspect exactly what the vector store is returning before the
results reach Claude.

### Query expansion

Many natural-language questions use casual verbs ("efficient", "problem",
"time when") that don't overlap well with the vocabulary in the source docs
("optimized", "reduced latency", "edge case"). Before embedding, the backend
checks the question for known trigger words and appends a synonym list to
the query. Multiple groups can fire on one question.

Default trigger groups (see `app/rag.py:EXPANSION_GROUPS`):

| Trigger words                         | Appended to query |
| ------------------------------------- | ----------------- |
| `efficient`, `efficiency`             | optimized performance faster improved streamlined reduced enhanced |
| `project`, `projects`                 | work built developed created implemented system |
| `problem(s)`, `solve(d)`, `solving`   | challenge issue edge case bug fixed resolved |
| `time`, `when`, `example`, `instance` | specific story case experience |
| `system`, `systems`                   | architecture infrastructure platform service |

Example:
- **Original**: `"time where Vaughn made a system more efficient"`
- **Expanded**: `"time where Vaughn made a system more efficient specific story case experience architecture infrastructure platform service optimized performance faster improved streamlined reduced enhanced"`

Disable with `ENABLE_QUERY_EXPANSION=false` if you want to A/B test. Add new
groups by editing `EXPANSION_GROUPS` directly.

### Tuning `top_k` and `MIN_SIMILARITY_SCORE`

- `TOP_K` (default `10`) controls how many chunks are fetched from Chroma.
  Raise it if the right chunk is ranking 11th–15th; lower it if the prompt is
  getting too long. Hard max is 50.
- `MIN_SIMILARITY_SCORE` (unset by default) is a floor in `[0,1]` using
  Chroma's relevance score (higher = more similar). Set it to `0.65` or so
  to drop clearly-irrelevant chunks. Leave it unset while you're still
  investigating — filtering too aggressively can hide problems.

### Reading the retrieval logs

Every `/api/chat` and `/api/debug/retrieve` call emits a structured trace at
`INFO`:

```
[INFO] app.rag: ---- retrieval trace ----
[INFO] app.rag: original_query : 'Can you tell me about a time where Vaughn made a system more efficient?'
[INFO] app.rag: expanded_query : 'Can you tell me about a time where Vaughn made a system more efficient specific story ... optimized performance ...'
[INFO] app.rag: expansions     : ['optimized performance faster ...', 'specific story case experience', 'architecture infrastructure ...']
[INFO] app.rag: k=10 min_score=None returned=10 dropped=0
[INFO] app.rag:   # 1  score=0.8123  src_employment_detailed_context.md#7  At DraftKings, Vaughn optimized the live odds...
[INFO] app.rag:   # 2  score=0.7891  src_employment_detailed_context.md#8  ...reduced p99 latency from 240ms to 90ms...
[INFO] app.rag:   # 3  score=0.7604  vaughn_eugenio_context.md#3         Senior engineer with a focus on ...
...
[INFO] app.rag: -------------------------
```

Each row is `#rank  score=X.XXXX  filename#chunk_id  first 100 chars`.
If the expected chunks aren't in the top results, either raise `TOP_K`,
add a new expansion group for the vocabulary mismatch, or re-chunk the
source (smaller chunks often score higher on specific questions).

### `POST /api/debug/retrieve`

Runs the full retrieval pipeline — expansion, history merging, scored
search, filtering — and returns the trace as JSON **without calling Claude**.
Use this to iterate on retrieval quality cheaply.

Request:
```json
{
  "question": "Can you tell me about a time where Vaughn made a system more efficient?",
  "k": 10,
  "min_score": null,
  "enable_expansion": true
}
```
`k`, `min_score`, and `enable_expansion` are all optional per-request
overrides; omit them to use the values from `.env`. `conversation_history`
is also supported, same shape as `/api/chat`.

Response:
```json
{
  "original_query": "...",
  "expanded_query": "...",
  "retrieval_query": "...",
  "expansions_applied": ["optimized performance ...", "..."],
  "k": 10,
  "min_score": null,
  "returned": 10,
  "dropped_below_threshold": 0,
  "chunks": [
    { "filename": "src_employment_detailed_context.md", "chunk_id": 7, "preview": "At DraftKings, Vaughn optimized ...", "score": 0.8123 }
  ]
}
```

Curl — A/B test your problematic query with expansion on vs off:
```bash
# With expansion on (default)
curl -X POST http://localhost:8000/api/debug/retrieve \
     -H "Content-Type: application/json" \
     -d '{"question":"Can you tell me about a time where Vaughn made a system more efficient?"}'

# Same query, expansion OFF, to compare
curl -X POST http://localhost:8000/api/debug/retrieve \
     -H "Content-Type: application/json" \
     -d '{"question":"Can you tell me about a time where Vaughn made a system more efficient?","enable_expansion":false}'
```

Diff the two responses to see whether expansion is actually pulling
`src_employment_detailed_context.md` into the top-k.

## Hybrid retrieval (BM25 + LLM rerank)

Vector search alone dilutes exact keyword matches — asking *"what did Vaughn
do with Kubernetes"* can miss the chunk that literally contains the word
"Kubernetes" because vector similarity spreads probability across paraphrases.
Following [Karpathy's RAG gist][karpathy-gist], the backend ships an
alternative two-stage pipeline:

1. **BM25 first stage** — classic keyword search over every chunk in the
   ChromaDB collection. Returns a candidate pool of ~25 (`BM25_CANDIDATES`).
2. **Claude rerank** — candidates are numbered and sent to Claude with the
   question. Claude returns a JSON array of `{id, score}` objects. Top-K
   (`RERANK_TOP_K`, default 8) become the final context.

[karpathy-gist]: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

### When to use which retriever

| Retriever          | Wins on                                              | Costs                         |
| ------------------ | ---------------------------------------------------- | ----------------------------- |
| Vector only        | Paraphrased / conceptual questions                   | 1 embedding + 1 answer call   |
| BM25 + rerank      | Questions with specific keywords, proper nouns, jargon | 1 rerank + 1 answer call (2 LLM calls total) |

Default is vector-only. Opt in to hybrid either globally (`ENABLE_BM25=true`
in `.env`) or per-request via the `use_bm25` query param.

### Using BM25 for a single request

```bash
curl -X POST 'http://localhost:8000/api/chat?use_bm25=true' \
     -H "Content-Type: application/json" \
     -d '{"question":"Can you tell me about a time where Vaughn made a system more efficient?"}'
```

The response shape is identical to the vector path; only the `sources`
scores differ (they'll be rerank scores in `[0, 1]` instead of Chroma
relevance scores).

### `POST /api/debug/compare`

Runs **all three** retrievers on the same question and returns a
side-by-side JSON trace so you can see exactly which chunks each approach
surfaces. Makes one LLM call (the rerank pass); does **not** call the
answer model.

```bash
curl -X POST http://localhost:8000/api/debug/compare \
     -H "Content-Type: application/json" \
     -d '{"question":"Can you tell me about a time where Vaughn made a system more efficient?"}'
```

Response shape:
```json
{
  "question": "...",
  "vector":          { "chunks": [ { "filename": "...", "chunk_id": 1, "score": 0.78, "preview": "..." }, ... ], ... },
  "bm25":            { "chunks": [ ... ], ... },
  "hybrid_reranked": { "chunks": [ ... ], ... }
}
```

Each block is a full `DebugRetrieveResponse` with per-chunk scores. Diff
the three `chunks` arrays to confirm whether BM25 is pulling the right
files (e.g. `src_employment_detailed_context.md`) and whether the reranker
is sharpening the top of the list vs the raw BM25 order.

Optional per-request overrides:
```json
{
  "question": "...",
  "candidates_k": 40,         // larger BM25 pool
  "final_k": 5,               // tighter final context
  "enable_expansion": false   // compare without synonym expansion
}
```

### Reading hybrid logs

Server logs emit **two** trace blocks per hybrid request — the BM25 first
stage and the reranked top-K — using the same format as the vector trace
but with `---- bm25 trace ----` and `---- reranked trace ----` headers.
The reranked block's `score` column is Claude's relevance judgment in
`[0, 1]` (from a 0–10 internal scale), not BM25 or Chroma.

### Tuning

- `BM25_CANDIDATES` (default 25): raise to 40–50 if the right chunk is
  missing from the first stage. Costs extra rerank tokens linearly.
- `RERANK_TOP_K` (default 8): raise for broader context, lower for tighter
  prompts.
- `RERANK_MODEL`: point at a cheaper/faster Anthropic model (e.g. Haiku)
  once you're happy with quality — the rerank prompt is short and doesn't
  need the flagship model.

## Telegram notifications

Optional: get a phone push every time someone visits the site or uses the
chatbot, including coarse geolocation of the visitor.

### One-time Telegram setup

1. In Telegram, talk to **@BotFather** → `/newbot` → pick a name → copy the
   **bot token** it returns.
2. Talk to **@userinfobot** to get your numeric **chat id**.
3. Send your new bot a `/start` message (Telegram won't let it message you
   first until you do).

### Backend config

In `.env` (or App Runner env vars):
```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF-your-token-here
TELEGRAM_CHAT_ID=123456789
ENABLE_TELEGRAM_NOTIFICATIONS=true
VISIT_THROTTLE_SECONDS=3600
```

If either token or chat_id is missing, the notifier silently no-ops — so
local dev without Telegram credentials is fine.

### What gets sent

**Per chatbot use** (no throttle, every chat is signal):
```
🗨️ New chat on vaughneugenio.com

Q: Can you tell me about Vaughn's experience at DraftKings?
A: At DraftKings, Vaughn worked on the Abacus and Titan…

📍 Brooklyn, New York, US
🌐 IP: 73.x.x.x
⚙️ vector · 8 sources · 2.4s
🧭 Mozilla/5.0 (Macintosh; Intel Mac OS X…
```

**Per page visit** (throttled — one ping per IP+path per
`VISIT_THROTTLE_SECONDS`):
```
👀 New visit to vaughneugenio.com

Path: /
📍 Brooklyn, New York, US
🌐 IP: 73.x.x.x
↩️ Referrer: https://www.linkedin.com/
🧭 Mozilla/5.0 (Macintosh; Intel Mac OS X…
```

### How geolocation works

Free server-side IP lookup via [ip-api.com](http://ip-api.com) (45 req/min,
no key, HTTP — fine for backend-to-backend). Results are cached in-process
via `lru_cache(1024)`, so repeat visitors don't burn quota. Local/private
IPs are short-circuited to "local / private network" without an upstream
call. Lookup failures degrade gracefully — the notification still goes
out, just labeled "Unknown location."

### `POST /api/visit`

The frontend hits this on page load. Body:
```json
{ "path": "/", "referrer": "https://www.linkedin.com/" }
```
Both fields are optional. Returns `{"ok": true}` immediately; the actual
notification is sent in a FastAPI `BackgroundTask`, so the visitor never
waits on Telegram. See `FRONTEND_INTEGRATION.md` for the snippet to drop
into the React frontend.

### Privacy notes

- Question text is logged to CloudWatch (already was) and now also sent to
  your private Telegram chat. Don't share this Telegram chat.
- IPs and User-Agents are sent to Telegram. Coarse city-level geolocation
  only; no street-level data.
- The notifier never sends Anthropic responses to anywhere except the
  visitor's browser — only the visible answer preview is included.

## Docker

The backend ships as a self-contained container image with the prebuilt
ChromaDB store baked in, so it can be deployed to AWS App Runner with no
volume mounts.

> **Build context is the repo root**, not `Backend/`. The Dockerfile needs to
> `COPY` from both `Backend/` and `Pipeline/chroma_db`, so all `docker build`
> commands below must be run from the repo root. The `.dockerignore` lives at
> the repo root for the same reason — Docker only reads `.dockerignore` from
> the build-context root.

### Prerequisite

`Pipeline/chroma_db/` must exist on disk before you build. If it doesn't:
```bash
cd Pipeline && python ingest.py && cd ..
```

### Build locally

From the repo root:
```bash
docker build -f Backend/Dockerfile -t vaughn-rag-backend .
```

The build is multi-stage (`python:3.11-slim`) so the final runtime image
contains only Python, the installed packages, the app, and the vector DB.

### Run locally

```bash
docker run --rm -p 8000:8000 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e OPENAI_API_KEY=sk-... \
  vaughn-rag-backend
```

Then `curl http://localhost:8000/health` should return
`{"status":"ok","vectorstore_loaded":true,...}`.

The container honors the `PORT` env var (App Runner injects this), defaulting
to `8000`. To simulate App Runner locally on a different port:
```bash
docker run --rm -p 9090:9090 -e PORT=9090 \
  -e ANTHROPIC_API_KEY=... -e OPENAI_API_KEY=... \
  vaughn-rag-backend
```

### Docker Compose

For repeated local runs, fill in `Backend/.env` (from `.env.example`) and:
```bash
cd Backend
docker compose up --build
```

### Push to AWS ECR

```bash
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012
REPO=vaughn-rag-backend

# 1. Create the ECR repo (one time)
aws ecr create-repository --repository-name $REPO --region $AWS_REGION

# 2. Authenticate Docker to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# 3. Build, tag, and push (from the repo root)
docker build -f Backend/Dockerfile -t $REPO:latest .
docker tag $REPO:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO:latest
docker push \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO:latest
```

### Configure AWS App Runner

When creating the App Runner service:
- **Source**: ECR, image URI from the push step above.
- **Port**: `8000` (or any port — the container honors `$PORT`).
- **Health check path**: `/health`.
- **Environment variables**: set `ANTHROPIC_API_KEY` and `OPENAI_API_KEY`.
  All other settings have safe defaults baked into the image.
- **CPU/Memory**: 1 vCPU / 2 GB is a reasonable starting point; the OpenAI
  embedding call dominates per-request cost, not local CPU.

## Troubleshooting

- **`/health` reports `vectorstore_loaded: false`** — the server failed to
  open `CHROMA_DIR`. Check that `Pipeline/chroma_db/` exists and that
  `CHROMA_DIR` in `.env` resolves correctly relative to where you launched
  uvicorn.
- **`502 Upstream LLM error`** — Anthropic returned an error. Check the
  server logs for the underlying message (auth, rate limit, etc.).
- **Retrieval returns irrelevant chunks** — verify `COLLECTION_NAME` and
  `EMBEDDING_MODEL` match the values used by `Pipeline/ingest.py`.
