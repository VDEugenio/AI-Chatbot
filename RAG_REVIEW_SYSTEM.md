# RAG Review System — Build Documentation

## Overview

This document covers the design, implementation, and deployment of the **RAG Review System** — a two-phase feedback loop that automatically identifies context gaps in the RAG knowledge base and provides a mobile-friendly interface for the developer to fill those gaps.

The system was built in two phases:

- **Phase 1:** Claude-powered Telegram notifications (already shipped before this document)
- **Phase 2:** Full end-to-end review loop with a hosted frontend, backend storage, and automated GitHub commits (documented here)

---

## Problem Statement

The RAG chatbot at `vaughneugenio.com` answers recruiter questions about Vaughn's background using a vector knowledge base built from markdown files in `Pipeline/data_v2/`. The GitHub-sourced files (`github_*.md`) are auto-generated from README content, language stats, and commit history — but READMEs are often thin or missing entirely.

Without a feedback mechanism, there was no way to:
- Know when a repo's context was too weak for quality retrieval
- Ask targeted questions to fill specific gaps
- Update the knowledge base without manually editing markdown files

---

## Architecture

### Before This Build

```
GitHub push
  → Airflow DAG (github_ingest)
      → fetch_repos
      → format_markdown
      → commit_to_github
          → CI rebuilds RAG index
```

### After This Build

```
GitHub push
  → DAG 1 (github_ingest)
      → fetch_repos
      → format_markdown
      → commit_to_github          ← baseline markdown committed (raw auto-generated)
      → ask_for_context           ← NEW (non-blocking, trigger_rule=all_done)
          → Claude generates targeted questions per repo
          → POST questions + formatted files to backend
          → Telegram ping with link to /rag-review

Developer opens vaughneugenio.com/rag-review on phone
  → Sees questions grouped by repo
  → Fills in answers (empty = skip)
  → Hits Submit

Backend (POST /api/rag-answers)
  → Claude synthesizes answers into enriched markdown
    (appends ## Developer Notes section to each repo's file)
  → Triggers DAG 2 via Airflow REST API

DAG 2 (rag_commit)
  → fetch_enriched_files          ← pulls enriched files from backend
  → commit_to_github              ← commits enriched markdown to Pipeline/data_v2/
      → CI rebuilds RAG index with developer context included
```

---

## Phase 1: Telegram Notifications (Previously Shipped)

### What was built

A new task `ask_for_context` was added to the existing `github_ingest` DAG as a 4th step. It runs with `trigger_rule="all_done"` so it never blocks ingestion.

**`airflow/include/context_asker.py`** (new file at Phase 1):
- `generate_questions(repos, api_key)` — calls `claude-opus-4-5` with full repo metadata and a system prompt positioning Claude as a RAG quality reviewer. Returns markdown-formatted questions or empty string if no gaps found.
- `send_telegram(message, bot_token, chat_id)` — sends the questions via Telegram Bot API. Auto-splits messages over 4096 chars at newline boundaries.
- `_split_message(message)` — internal helper for chunking long messages.

**New Airflow Variables added:**
| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API access |
| `TELEGRAM_BOT_TOKEN` | BotFather token for the notification bot |
| `TELEGRAM_CHAT_ID` | Chat ID of the dedicated RAG review group |

### Claude prompt strategy (Phase 1)

Claude is given the raw repo metadata (full_name, description, README, languages, commits, file_structure) and instructed to:
- Identify gaps that would hurt retrieval quality in a recruiter-facing AI chatbot
- Ask as many questions as genuinely needed per repo — no artificial cap
- Skip repos that already look complete and well-documented
- Format output as `### repo_name\n- question\n- question...`

---

## Phase 2: Full Review Loop (This Build)

### Design Decisions

**Why two DAGs instead of one?**
The original `github_ingest` DAG was not designed to wait for human input. Leaving a DAG suspended for hours while waiting for answers is an anti-pattern in Airflow. Separating concerns gives us:
- DAG 1 finishes immediately after asking questions
- DAG 2 triggers only when answers are ready (via the backend)
- No polling, no sensors, no open-ended waits

**Why does the backend store the formatted files?**
DAG 2 needs the baseline markdown to enrich with developer notes. Two options were considered:
- **Option A (chosen):** DAG 1 ships the formatted files to the backend alongside the questions. When answers come in, the backend enriches them and stores the result. DAG 2 fetches the enriched files and commits.
- **Option B (rejected):** DAG 2 re-fetches repos from GitHub and re-formats. Simpler storage, but loses the exact snapshot DAG 1 captured.

Option A was chosen to guarantee DAG 2 commits exactly the same baseline that DAG 1 prepared, enriched with developer notes.

**Why is the review page unauthenticated?**
The data being read (Claude's questions about Vaughn's repos) is not sensitive. Authentication can be added later in a single line (`_=Depends(verify_admin_key)` on the endpoint). Starting without auth removes friction for mobile access and simplifies the initial build. The `GET /api/rag-run/{run_id}/files` endpoint used by DAG 2 remains authenticated.

**Empty answers = skip**
Rather than a dedicated Skip button, any empty textarea is treated as a skip by the backend. Claude ignores Q&A pairs where the answer is empty.

---

## Files Changed / Created

### Airflow (`airflow/`)

#### `airflow/include/context_asker.py` (updated)

**New functions added in Phase 2:**

`parse_questions_to_list(raw_text: str) -> list[dict]`
- Parses Claude's `### repo_name\n- question` markdown into a structured list
- Returns: `[{"repo_name": "VDEugenio/VaughnKey", "questions": ["q1", "q2"]}]`
- Repos with no questions are omitted
- Preserves the repo name exactly as Claude wrote it (e.g. `VDEugenio/VaughnKey`)

`post_run_to_backend(run_id, repos_questions, formatted_files, backend_url) -> None`
- POSTs `{run_id, repos, files}` to `{backend_url}/api/rag-questions`
- Unauthenticated — endpoint is intentionally open
- `requests.post()` with 30-second timeout, raises on non-2xx

**Updated in Phase 2:**

`send_telegram()` — appends `🔗 Answer at: https://vaughneugenio.com/rag-review` to every message so the developer can tap directly to the review page.

#### `airflow/dags/github_ingest_dag.py` (updated)

**`ask_for_context` task changes:**
- Signature updated to accept `tmp_path: str` in addition to `repos`
- Reads formatted files from `tmp_path` (the JSON written by `format_markdown`)
- Calls `parse_questions_to_list()` and `post_run_to_backend()` in a try/except (backend failure is non-fatal)
- Telegram send kept in a separate try/except so backend failure never silences the notification
- Tmp file cleanup (`Path(tmp_path).unlink()`) moved from `commit_to_github` to end of `ask_for_context` so the file survives long enough to be read

**Wiring update:**
```python
# Before
commit_to_github(tmp_path) >> ask_for_context(repos_data)

# After
commit_to_github(tmp_path) >> ask_for_context(repos_data, tmp_path)
```

**New Airflow Variable required:**
| Variable | Value |
|---|---|
| `BACKEND_URL` | `https://chat.vaughneugenio.com` |

#### `airflow/dags/rag_commit_dag.py` (new file)

DAG 2 — triggered by the backend after answer submission.

```
fetch_enriched_files → commit_to_github
```

**`fetch_enriched_files` task:**
- Reads `run_id` from `dag_run.conf`
- Calls `GET {BACKEND_URL}/api/rag-run/{run_id}/files` with `X-Admin-Key` header
- Writes the enriched files list to a temp JSON file
- Returns the temp file path via XCom (path-based XCom pattern, same as `format_markdown` in DAG 1)

**`commit_to_github` task:**
- Same PyGithub create/update pattern as in DAG 1
- Commits enriched `github_*.md` files to `Pipeline/data_v2/` in `VDEugenio/AI-Chatbot`
- Never deletes files — stale cleanup remains DAG 1's responsibility
- Cleans up tmp file after committing

**New Airflow Variables required:**
| Variable | Value |
|---|---|
| `ADMIN_KEY` | Must match backend `ADMIN_KEY` env var |

> `BACKEND_URL` and `GITHUB_TOKEN` are shared with DAG 1 — no new entries needed.

---

### Backend (`Backend/app/`)

#### `app/db.py` (updated)

**New table: `rag_review_runs`**
```sql
CREATE TABLE IF NOT EXISTS rag_review_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        TEXT UNIQUE NOT NULL,
    created_at    REAL NOT NULL,
    repos_json    TEXT NOT NULL,     -- [{"repo_name": str, "questions": [str]}]
    files_json    TEXT NOT NULL,     -- [{"filename": str, "content": str}] baseline
    enriched_json TEXT,              -- [{"filename": str, "content": str}] after synthesis
    status        TEXT NOT NULL DEFAULT 'pending'  -- 'pending' | 'committed'
)
```

**New functions:**
- `save_rag_run(run_id, repos, files)` — INSERT OR REPLACE, status='pending'
- `get_latest_pending_run()` — returns most recent pending run as dict (repos parsed from JSON), or None
- `get_run(run_id)` — returns full raw row as dict, or None
- `save_enriched_files(run_id, enriched_files)` — stores Claude's enriched output
- `mark_run_committed(run_id)` — sets status='committed' after DAG 2 finishes

All functions follow the existing `_lock` + fresh `_conn()` per operation pattern for thread safety.

**Also added:** `import json` at the top of the file (was missing, needed by new functions).

#### `app/schemas.py` (updated)

7 new Pydantic models added:

| Model | Purpose |
|---|---|
| `RepoQuestions` | `{repo_name, questions[]}` — one repo's questions |
| `FormattedFile` | `{filename, content}` — one markdown file |
| `RagQuestionsRequest` | Body for `POST /api/rag-questions` (DAG 1 → backend) |
| `RepoAnswer` | `{repo_name, question, answer}` — one Q&A pair |
| `RagAnswersRequest` | Body for `POST /api/rag-answers` (frontend → backend) |
| `RagQuestionsResponse` | Response for `GET /api/rag-questions` (backend → frontend) |
| `RagFilesResponse` | Response for `GET /api/rag-run/{run_id}/files` (backend → DAG 2) |

#### `app/rag_review.py` (new file)

**`filename_for_repo(repo_full_name: str) -> str`**
- Converts `"VDEugenio/VaughnKey"` → `"github_VDEugenio_VaughnKey.md"`
- Replicates the same slug logic used by `airflow/include/markdown_formatter.py`

**`async synthesize_and_store(run_id, answers, settings) -> None`**
1. Fetches the run's baseline files from DB
2. Groups non-empty answers by `repo_name` (empty = skip)
3. For each file with matching answers: calls Claude (`claude-sonnet-4-20250514`) to append a `## Developer Notes` section synthesizing the answers
4. Files with no answers pass through unchanged (baseline content kept)
5. Saves enriched files back to DB via `save_enriched_files()`

**Claude synthesis prompt:**
> "You are enriching a RAG knowledge-base markdown file for a recruiter-facing AI chatbot. Given the existing markdown and Q&A pairs from the developer, append a `## Developer Notes` section at the end synthesizing the answers into clear prose. Preserve all existing YAML frontmatter and content exactly. Ignore any questions with empty answers. Only output the complete updated file — no commentary."

#### `app/config.py` (updated)

3 new settings added to `Settings`:

| Setting | Env Var | Purpose |
|---|---|---|
| `airflow_url` | `AIRFLOW_URL` | Astro Cloud base URL for triggering DAG 2 |
| `airflow_username` | `AIRFLOW_USERNAME` | Airflow REST API credentials |
| `airflow_password` | `AIRFLOW_PASSWORD` | Airflow REST API credentials |

#### `app/main.py` (updated)

**New imports:**
- `Depends`, `Header` added to fastapi import
- `import httpx` added at module level
- New schemas (`RagQuestionsRequest`, `RagQuestionsResponse`, `RagAnswersRequest`, `RagFilesResponse`) imported
- `synthesize_and_store` imported from `app.rag_review`
- New DB functions imported from `app.db`

**`verify_admin_key` dependency (new):**
```python
def verify_admin_key(x_admin_key: str = Header(default="")) -> None:
    if not settings.admin_key or x_admin_key != settings.admin_key:
        raise HTTPException(status_code=403, detail="Forbidden")
```
The existing `admin_visitors` endpoint was refactored from an inline key check to use `Depends(verify_admin_key)`.

**4 new endpoints:**

| Method | Path | Auth | Caller | Purpose |
|---|---|---|---|---|
| `POST` | `/api/rag-questions` | None | DAG 1 | Store questions + baseline files from a DAG run |
| `GET` | `/api/rag-questions` | None | Frontend | Fetch the latest pending review run |
| `POST` | `/api/rag-answers` | None | Frontend | Submit answers → synthesize → trigger DAG 2 |
| `GET` | `/api/rag-run/{run_id}/files` | `X-Admin-Key` | DAG 2 | Fetch enriched files for committing |

> Note: The two user-facing endpoints (`GET` and `POST /api/rag-questions`, `POST /api/rag-answers`) are intentionally unauthenticated. Authentication can be added later by adding `_=Depends(verify_admin_key)` to the function signatures. The `GET /api/rag-run/{run_id}/files` endpoint remains protected since it is machine-to-machine (DAG 2 only).

**`POST /api/rag-answers` flow:**
1. Calls `synthesize_and_store()` — Claude enriches each repo's markdown with non-empty answers
2. If `settings.airflow_url` is set: POSTs to `{airflow_url}/api/v2/dags/rag_commit/dagRuns` with `conf: {run_id}` to trigger DAG 2
3. Calls `mark_run_committed(run_id)` — sets status='committed'

---

### Frontend (`FrontendV2/src/`)

#### `src/api/ragReview.ts` (new file)

Two API functions:

`fetchPendingRun() -> Promise<RagRun>`
- `GET /api/rag-questions`
- Throws `{status, detail}` on non-2xx

`submitAnswers(run_id, answers) -> Promise<void>`
- `POST /api/rag-answers`
- Body: `{run_id, answers: [{repo_name, question, answer}]}`
- Throws `{status, detail}` on non-2xx

#### `src/pages/RagReviewPage.tsx` (new file)

A mobile-first page following the existing design system (dark theme, purple accents, Syne/Inter fonts, SpinningBorderButton).

**Page states:**

| State | What the user sees |
|---|---|
| `loading` | Pulsing "Loading questions…" text |
| `questions` (no run) | "All caught up ✓" — no pending questions |
| `questions` (with run) | Repo cards with question labels and textareas |
| `submitting` | Submit button visually disabled (opacity-50) |
| `success` | "Done ✓ — your answers are being processed" |
| `error` | Error message with Try again button |

**Questions view:**
- Sticky header with run date and "RAG Review" title
- Per-repo cards with `purple-hot` left border accent and `dark-700` background
- Each question rendered as a label above a 3-row textarea
- `placeholder="Leave blank to skip"` — empty = skip, no dedicated Skip button
- Sticky bottom bar with `SpinningBorderButton` — disabled state handled via `opacity-50 pointer-events-none` wrapper (SpinningBorderButton has no native disabled prop)

**On submit:**
- Collects all textarea values (including empty strings)
- POSTs full answer list to `/api/rag-answers`
- Empty answers are passed as-is; the backend filters them out

#### `src/App.tsx` (updated)

```tsx
import RagReviewPage from './pages/RagReviewPage';
// ...
<Route path="/rag-review" element={<RagReviewPage />} />
```

---

## New Environment Variables — Full Reference

### Airflow Variables (set in Astro Cloud UI: Admin → Variables)

| Variable | Value | Used by |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key | DAG 1 — `ask_for_context` task |
| `TELEGRAM_BOT_TOKEN` | BotFather token | DAG 1 — `ask_for_context` task |
| `TELEGRAM_CHAT_ID` | Telegram group chat ID | DAG 1 — `ask_for_context` task |
| `BACKEND_URL` | `https://chat.vaughneugenio.com` | DAG 1 + DAG 2 |
| `ADMIN_KEY` | Must match backend `ADMIN_KEY` env var | DAG 2 — `fetch_enriched_files` task |
| `GITHUB_TOKEN` | Fine-grained PAT, Contents r/w on `VDEugenio/AI-Chatbot` | DAG 1 + DAG 2 (shared) |

### Backend (AWS App Runner environment variables)

| Variable | Value | Purpose |
|---|---|---|
| `AIRFLOW_URL` | Astro Cloud deployment base URL | Trigger DAG 2 after answer submission |
| `AIRFLOW_USERNAME` | Astro Cloud API username | Airflow REST API auth |
| `AIRFLOW_PASSWORD` | Astro Cloud API password/token | Airflow REST API auth |

> All other existing env vars (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `ADMIN_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) remain unchanged.

### Frontend (Vercel — no new variables)

The frontend uses `VITE_API_BASE` (already set) for all API calls. No new Vercel env vars required.

---

## Deployment Order

1. **Backend** — deploy to App Runner first so the new endpoints are live before DAG 1 tries to POST to them
2. **Airflow DAGs** — push changes to trigger `astro-deploy.yml`; set `BACKEND_URL` and `ADMIN_KEY` Variables in the Astro Cloud UI
3. **Frontend** — deploy to Vercel (`vercel --prod` from `FrontendV2/`)

---

## End-to-End Verification Checklist

- [ ] Trigger `github_ingest` DAG manually from Airflow UI
- [ ] Confirm `ask_for_context` logs: questions generated → backend POST succeeded → Telegram sent
- [ ] Check Telegram — message received with `/rag-review` link
- [ ] `curl https://chat.vaughneugenio.com/api/rag-questions` → questions JSON returned
- [ ] Open `vaughneugenio.com/rag-review` on phone → questions appear
- [ ] Fill in some answers, leave one blank, hit Submit
- [ ] Confirm backend logs: Claude synthesis ran → enriched files stored → DAG 2 triggered
- [ ] Check Airflow UI — `rag_commit` DAG run appeared and completed
- [ ] Check `Pipeline/data_v2/` on GitHub — enriched files have `## Developer Notes` section
- [ ] Confirm CI `ingest-and-deploy.yml` triggered and rebuilt successfully
- [ ] Ask the RAG chatbot a question about the enriched repo — verify it uses the new context

---

## Adding Authentication Later

When ready to lock down the review page:

**Backend** — add `_=Depends(verify_admin_key)` to the three unauthenticated endpoints:
```python
# GET /api/rag-questions
async def get_rag_questions(_=Depends(verify_admin_key)):

# POST /api/rag-answers
async def submit_rag_answers(body: RagAnswersRequest, _=Depends(verify_admin_key)):
```

**Frontend** — re-add the password gate to `RagReviewPage.tsx`. The locked state, `handleLogin`, and sessionStorage logic were all written and tested before being removed for the unauthenticated version — they can be restored from git history or re-implemented in the same pattern.

The `ADMIN_KEY` env var on App Runner is already set (used by `/api/admin/visitors`), so no new infrastructure is needed.
