# Airflow Build Notes — GitHub RAG Ingestion Pipeline

This document is the comprehensive reference for the Airflow piece of the RAG Vaughn project. It covers every file, every design decision, every concept used, and every bug encountered across both Tier 1 (local pipeline) and Tier 2 (automated cloud pipeline with debounce trigger).

---

## What This Pipeline Does

The chatbot at `chat.vaughneugenio.com` answers questions about Vaughn using a RAG (Retrieval-Augmented Generation) backend. The knowledge base is a ChromaDB vector index built from markdown files in `Pipeline/data_v2/`. Most of those files are handwritten (career narrative, resume, etc.), but the ones prefixed `github_` are auto-generated — one per portfolio GitHub repository.

The Airflow pipeline keeps those `github_*.md` files up to date. It fetches fresh data from the GitHub API for each portfolio repo, formats it as markdown, and commits the files directly to the repository via the GitHub API. Downstream GitHub Actions handle rebuilding ChromaDB and redeploying the live site.

---

## Repository Structure (Airflow-Relevant Files)

```
RAG_Vaughn/
├── airflow/
│   ├── dags/
│   │   └── github_ingest_dag.py        # The DAG definition
│   ├── include/
│   │   ├── github_fetcher.py           # GitHub API helper
│   │   └── markdown_formatter.py       # Markdown + frontmatter generator
│   ├── Dockerfile                       # Astro Runtime base image
│   ├── requirements.txt                 # Python dependencies for the DAG
│   ├── packages.txt                     # OS-level packages (empty)
│   └── docker-compose.override.yml      # Local dev volume mounts (ignored by Astro Cloud)
└── .github/
    └── workflows/
        ├── debounce-trigger.yml         # Fires on push → 5h sleep → triggers github_ingest
        ├── astro-deploy.yml             # Deploys Airflow project to Astro Cloud on push
        ├── ingest-and-deploy.yml        # Rebuilds ChromaDB and redeploys Backend on push
        └── eval.yml                     # RAG evaluation (paths-ignore: github_*.md)
```

---

## Full Architecture

```
You push code to main
        ↓
debounce-trigger.yml fires (paths-ignore: Pipeline/data_v2/**)
        ↓
GHA concurrency cancel-in-progress: true
  → cancels any currently sleeping run (timer reset)
  → starts a fresh run
        ↓
sleep 18000 (5 hours)  ← cancelled + restarted on each new push
        ↓  [5 hours of silence]
Wake deployment if hibernating (astro deployment wake-up --force --for 2h)
        ↓
POST /api/v2/dags/github_ingest/dagRuns  (Airflow REST API)
        ↓
[Astro Cloud — github_ingest DAG]
  fetch_repos → format_markdown → commit_to_github
                                        ↓
                          Commits github_*.md to main
                                        ↓
                    GitHub detects push to Pipeline/data_v2/
                                        ↓
                    ingest-and-deploy.yml fires

    ┌────────────────────────────────────────────────────────┐
    │  Job 1: ingest                                          │
    │  pip install → python ingest.py --rebuild               │
    │  validate chunk_count > 0                               │
    │  upload Pipeline/chroma_db/ as artifact                 │
    │  → Telegram: "N chunks. Approve: [link]"                │
    └────────────────────────┬───────────────────────────────┘
                             │
                 [You approve in GitHub UI]
                             ↓
    ┌────────────────────────────────────────────────────────┐
    │  Job 2: deploy  (environment: production gate)          │
    │  download chroma_db artifact                            │
    │  AWS + ECR login                                        │
    │  verify App Runner RUNNING                              │
    │  determine next tag :v(N+1)                             │
    │  docker build (chroma_db baked in) + push to ECR        │
    │  update App Runner service                              │
    │  poll until RUNNING → smoke test /health                │
    │  → Telegram: "vN deployed — N chunks live"              │
    └────────────────────────────────────────────────────────┘
```

---

## Tier 1 — Local Pipeline

### Goal

Get the DAG running locally to verify the full fetch → format → ingest flow before moving anything to the cloud. The Tier 1 DAG wrote markdown files to the local `Pipeline/data_v2/` directory and ran `ingest.py` as a bash subprocess.

### Local Development Setup

**Astro CLI** manages Docker containers for all Airflow components (webserver, scheduler, triggerer, dag-processor, postgres, redis).

```
winget install -e --id Astronomer.Astro
```

**Docker runtime** — Astro CLI requires Docker. Docker Desktop had persistent issues, so **Rancher Desktop 1.22.3** with the **moby (dockerd)** engine is used instead.

**Podman conflict** — Podman also claims the `docker_engine` named pipe. Before every `astro dev start`, stop any Podman machines:
```
podman machine stop podman-machine-default
podman machine stop astro-machine
```

**Starting the local environment:**
```
cd airflow
astro dev start
```
Builds the Astro Runtime image and starts all containers. Airflow UI: `http://localhost:8080`.

**Stopping:**
```
astro dev stop
```

### `airflow/Dockerfile`

```dockerfile
FROM astrocrpublic.azurecr.io/runtime:3.2-4
```

A single line. Astro Runtime 3.2-4 is a pre-built image that includes Airflow 3.2.1 and all its dependencies. Additional Python packages are declared in `requirements.txt`.

### `airflow/requirements.txt`

```
chromadb==1.5.7
langchain-community==0.4.1
langchain-core==1.2.27
langchain-openai==1.1.12
langchain-text-splitters==1.1.1
openai==2.30.0
pypdf==6.9.2
python-dotenv==1.2.2
python-frontmatter==1.1.0
PyGithub>=2.1.0
```

**Why pinned?** The ChromaDB version must match `Pipeline/.venv` exactly. ChromaDB's on-disk format changes between versions — a mismatch causes the Backend to fail to read the collection. Versions were sourced from `pip freeze` in `Pipeline/.venv`.

**What was removed:** `unstructured>=0.15.0` and `markdown>=3.6` were originally listed but were never imported by any DAG code. `unstructured` pulls in ~15 minutes of ML sub-dependencies (torch, transformers, etc.) which was causing CI to time out. Both were removed.

### `airflow/docker-compose.override.yml`

```yaml
services:
  scheduler:
    volumes:
      - ../Pipeline:/pipeline:rw
  dag-processor:
    volumes:
      - ../Pipeline:/pipeline:rw
  triggerer:
    volumes:
      - ../Pipeline:/pipeline:rw
```

Mounts the local `Pipeline/` directory into Airflow containers at `/pipeline`. Used in Tier 1 so the DAG could write `github_*.md` files to `Pipeline/data_v2/` and shell out to `ingest.py`.

**This file is for local development only.** Astro Cloud silently ignores `docker-compose.override.yml` — it doesn't use Docker Compose. This is why the Tier 1 DAG tasks that used this mount had to be replaced in Tier 2.

---

## The DAG — `airflow/dags/github_ingest_dag.py`

### DAG Configuration

```python
@dag(
    dag_id="github_ingest",
    schedule=None,              # triggered externally via GHA debounce workflow
    start_date=datetime(2026, 5, 22),
    catchup=False,
    tags=["rag", "ingestion"],
    default_args={
        "owner": "airflow",
        "depends_on_past": False,
    },
    doc_md=__doc__,
)
```

**`schedule=None`** — the DAG does not run on a cron schedule. It only runs when triggered externally — either by the GHA debounce workflow (via the Airflow REST API) or by clicking "Trigger DAG" manually in the Airflow UI. This was changed from `"0 6 */2 * *"` (every other day at 6 AM UTC) in Tier 2 once the debounce trigger was built.

**`catchup=False`** — prevents backfill runs when the DAG is first enabled. Without this, Airflow would try to schedule every missed interval since `start_date`.

**`depends_on_past=False`** — each run is independent. A failed run doesn't block the next one.

**`doc_md=__doc__`** — uses the module docstring as the DAG's documentation in the Airflow UI.

### `sys.path` Manipulation

```python
_INCLUDE_DIR = Path("/usr/local/airflow/include")
if str(_INCLUDE_DIR) not in sys.path:
    sys.path.insert(0, str(_INCLUDE_DIR))
```

The `include/` directory is automatically added to the Python path by Astro Runtime, but this is done explicitly as a safety measure. `/usr/local/airflow/include` is where Astro Runtime mounts the `include/` directory inside containers.

### `PORTFOLIO_REPOS`

```python
PORTFOLIO_REPOS: list[str] = [
    "VDEugenio/AI-Chatbot",
    "VDEugenio/Job-Application-Tracker",
    "VDEugenio/VaughnKey",
    "VDEugenio/adf-marketplace",
]
```

The only configuration you need to touch when adding or removing repos. Format: `"owner/repo"`. Stale cleanup is automatic — if a repo is removed from this list, its `github_*.md` file is deleted from `Pipeline/data_v2/` on the next run.

---

### Task 1: `fetch_repos`

```python
@task(retries=2, retry_delay=timedelta(minutes=5))
def fetch_repos() -> list[dict]:
    from github_fetcher import fetch_repo_data
    token = Variable.get("GITHUB_TOKEN")
    repos = fetch_repo_data(token, PORTFOLIO_REPOS)
    return repos
```

Reads `PORTFOLIO_REPOS`, fetches data for each repo from the GitHub API via the `github_fetcher` helper, and returns a list of dicts. The return value is automatically serialised to JSON and stored in Airflow's XCom database, making it available to the next task.

**`Variable.get("GITHUB_TOKEN")`** — reads the `GITHUB_TOKEN` Airflow Variable, which is stored encrypted in Airflow's metadata database. The correct way to pass secrets to tasks.

**Why the import is inside the function:** Airflow parses the DAG file frequently to detect changes. Module-level imports slow down that parse cycle. Imports inside task functions only run when the task actually executes.

---

### Task 2: `format_markdown`

```python
@task(retries=2, retry_delay=timedelta(minutes=5))
def format_markdown(repos: list[dict], **context) -> str:
    from markdown_formatter import filename_for_repo, repo_to_markdown

    run_id = context["run_id"].replace(":", "_").replace("+", "_")
    tmp_path = f"/tmp/github_repos_{run_id}.json"

    files = []
    for repo in repos:
        filename = filename_for_repo(repo["full_name"])
        content = repo_to_markdown(repo)
        files.append({"filename": filename, "content": content})

    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(files, fh, ensure_ascii=False)

    return tmp_path
```

Converts each repo dict to a markdown string and writes all results to a temp JSON file at `/tmp/`, returning the file path via XCom.

**Why write to a temp file?** This is the **path-based XCom pattern**. XCom is designed for small values. With 4 repos × 2000-character READMEs, the total payload could exceed XCom's safe limits. Writing to `/tmp/` and passing the path keeps XCom tiny while the actual content lives on disk.

**`**context`** — Airflow injects the task's execution context. `context["run_id"]` is a unique string per run, used to prevent two concurrent runs from colliding on the same temp file.

---

### Task 3: `commit_to_github`

```python
@task(retries=2, retry_delay=timedelta(minutes=5))
def commit_to_github(tmp_path: str) -> str:
    from github import Github
    from github.GithubException import UnknownObjectException

    token = Variable.get("GITHUB_TOKEN")
    g = Github(token)
    repo = g.get_repo("VDEugenio/AI-Chatbot")

    with open(tmp_path, "r", encoding="utf-8") as fh:
        files = json.load(fh)

    incoming_names = {item["filename"] for item in files}
    data_prefix = "Pipeline/data_v2"

    # Delete stale files
    try:
        contents = repo.get_contents(data_prefix)
        for entry in contents:
            if entry.name.startswith("github_") and entry.name.endswith(".md"):
                if entry.name not in incoming_names:
                    repo.delete_file(entry.path, f"[bot] Remove stale {entry.name}", entry.sha)
    except Exception as exc:
        print(f"Warning: could not check for stale files: {exc}")

    # Create or update each file
    for file_item in files:
        path = f"{data_prefix}/{file_item['filename']}"
        content = file_item["content"]
        try:
            existing = repo.get_contents(path)
            repo.update_file(path, f"[bot] Update {file_item['filename']}", content, existing.sha)
        except UnknownObjectException:
            repo.create_file(path, f"[bot] Add {file_item['filename']}", content)

    Path(tmp_path).unlink(missing_ok=True)
    return data_prefix
```

Uses the GitHub Contents API (via PyGithub) to create or update each `github_*.md` file directly in the repository, with no local filesystem access. Also deletes any stale `github_*.md` files no longer in `PORTFOLIO_REPOS`.

**Why `update_file` needs the SHA:** The GitHub Contents API uses optimistic concurrency. To update a file, you must provide the SHA of the version you're replacing. If someone else updated the file between your `get_contents()` and `update_file()` calls, the SHAs won't match and GitHub rejects the update. Pattern: `get_contents() → extract SHA → update_file(sha=...)`.

**Why `except UnknownObjectException → create_file()`:** If a `github_*.md` file doesn't exist yet (new repo added to `PORTFOLIO_REPOS`), `get_contents()` raises `UnknownObjectException` (HTTP 404). Catch it and call `create_file()` instead, which doesn't require a SHA.

**Why filter stale cleanup by `github_` prefix:** `repo.get_contents("Pipeline/data_v2")` returns ALL files in that directory — including handwritten docs like `profile_overview.md`. The `startswith("github_") and endswith(".md")` filter ensures we only delete machine-generated files.

**Downstream effect:** Each `update_file()` or `create_file()` call creates a commit on `main`. These commits touch `Pipeline/data_v2/github_*.md`, which triggers `ingest-and-deploy.yml` in GitHub Actions.

---

### Task Wiring

```python
repos_data = fetch_repos()
tmp_path = format_markdown(repos_data)
commit_to_github(tmp_path)
```

With the **TaskFlow API**, passing a task's return value as an argument to the next task automatically creates both a data dependency (XCom) and an execution dependency. No explicit `>>` operators needed.

---

### Tier 1 Task Graph (for reference)

In Tier 1, the DAG had five tasks:

```
fetch_repos
    → format_markdown
        → write_files         # wrote github_*.md to local /pipeline/data_v2/
            → run_ingest      # BashOperator: cd /pipeline && python ingest.py --rebuild
                → validate_index  # confirmed ChromaDB chunk count > 0
```

`write_files`, `run_ingest`, and `validate_index` were removed in Tier 2 because they depended on the `docker-compose.override.yml` volume mount, which is incompatible with Astro Cloud. All three responsibilities moved to GitHub Actions.

---

## The Include Helpers

### `airflow/include/github_fetcher.py`

All GitHub API logic, separate from the DAG file for readability and testability.

**Public interface:**
```python
def fetch_repo_data(token: str, repo_full_names: list[str]) -> list[dict]
```

**What it fetches per repo:**

| Field | Source | Detail |
|---|---|---|
| `full_name` | `repo.full_name` | e.g., `"VDEugenio/AI-Chatbot"` |
| `description` | `repo.description` | One-line repo description |
| `readme` | `repo.get_readme()` | Decoded README content, **truncated to 2000 chars** |
| `languages` | `repo.get_languages()` | `{language: percentage}`, converted from raw byte counts |
| `commits` | `repo.get_commits()[:10]` | Last 10 commits: sha (7 chars), message (100 chars max), date |
| `file_structure` | `repo.get_contents("")` | Top-level files and directories (dirs suffixed with `/`) |

**Why truncate README to 2000 chars?** Long READMEs add noise without proportional retrieval value. 2000 characters covers the key project details.

**Why convert language bytes to percentages?** The GitHub API returns raw byte counts (e.g., `{"Python": 45231}`). Percentages are more meaningful in the markdown output and avoid leaking file-size information.

**Error handling:** Every API call is individually wrapped in try/except. A missing README or unavailable language data returns an empty default without aborting the rest of the fetch.

---

### `airflow/include/markdown_formatter.py`

Converts a repo data dict into a markdown string matching the schema expected by `Pipeline/ingest.py`.

**Public interface:**
```python
def filename_for_repo(full_name: str) -> str
def repo_to_markdown(repo: dict) -> str
```

**`filename_for_repo`:**
```
"VDEugenio/AI-Chatbot"  →  "github_VDEugenio_AI_Chatbot.md"
```
Replaces `/` and `-` with `_`, adds the `github_` prefix. The prefix is what allows stale cleanup to safely identify and delete only machine-generated files.

**YAML frontmatter generated:**
```yaml
---
name: AI-Chatbot (GitHub Repository)
company: github
topics: [github, portfolio, open_source]
skills: [python, javascript, typescript]
story_types: [project]
---
```

The `company: github` tag lets the Backend's retrieval layer filter results by source.

**Body sections (only included when data is present):**

| Section | Included when |
|---|---|
| `## Overview` | Description or README is non-empty |
| `## Tech Stack` | Language data was successfully fetched |
| `## Recent Activity` | At least one commit was fetched |
| `## File Structure` | At least one top-level file/dir was found |

---

## Airflow Variables

Encrypted key-value store built into Airflow's metadata database. Set via: **Airflow UI → Admin → Variables**

| Variable | Value | Used by |
|---|---|---|
| `GITHUB_TOKEN` | Fine-grained PAT, Contents: read+write on `VDEugenio/AI-Chatbot` | `fetch_repos` (read repo data), `commit_to_github` (write files) |

**Fine-grained PAT requirements:**
- Repository access: `VDEugenio/AI-Chatbot` only
- Permissions: Contents → **Read and write**

**Why not environment variables?** Airflow Variables are encrypted at rest and masked in logs. Container environment variables are visible in `docker inspect` output and can leak into logs.

---

## Tier 2 — Automated Cloud Pipeline

### Goal

Two problems remained after Tier 1:
1. The live site still served stale data after each DAG run. Rebuilding ChromaDB and redeploying the Backend required manual steps.
2. The DAG only ran while the laptop was on.

Tier 2 solved both by restructuring the DAG for Astro Cloud (no local filesystem access), automating the full ingest → approve → deploy chain with GitHub Actions, and adding a debounce trigger so the DAG runs automatically after pushes.

---

## Debounce Trigger — `.github/workflows/debounce-trigger.yml`

### The Problem It Solves

Airflow is a scheduler — it waits for a time or a condition. It has no native way to listen for GitHub push events. We needed the DAG to run after code changes, not on a fixed clock. The solution: GitHub Actions handles the event detection and the debounce timer; Airflow just executes the DAG when called.

### How Debounce Works

```
Push at 2:00 PM  → GHA workflow starts sleeping (5h)
Push at 4:00 PM  → cancel-in-progress kills the sleeping job → new job starts sleeping
No more pushes   → sleep completes at 9:00 PM → DAG triggered
```

The `concurrency: cancel-in-progress: true` is the entire debounce mechanism. Each new push cancels the currently sleeping run and starts a fresh 5-hour window. The GHA history will show many grey "Cancelled" runs — that's expected and cosmetic.

### The Workflow

```yaml
name: Debounce Ingest Trigger

on:
  push:
    branches: [main]
    paths-ignore:
      - 'Pipeline/data_v2/**'   # ignore bot commits from github_ingest itself

concurrency:
  group: ingest-debounce
  cancel-in-progress: true      # ← the debounce reset

jobs:
  wait-and-trigger:
    runs-on: ubuntu-latest
    steps:
      - name: Wait 5 hours (debounce window)
        run: sleep 18000

      - name: Install Astro CLI
        run: curl -sSL https://install.astronomer.io | sudo bash -s

      - name: Wake deployment if hibernating
        env:
          ASTRO_API_TOKEN: ${{ secrets.ASTRONOMER_API_KEY }}
        run: |
          STATE=$(astro deployment inspect cmpncv8rk8dfc01j7s24vh17h \
            --key metadata.status 2>/dev/null || echo "UNKNOWN")
          if [[ "$STATE" == *"HIBERNAT"* ]]; then
            astro deployment wake-up cmpncv8rk8dfc01j7s24vh17h --force --for 2h
            for i in $(seq 1 20); do
              sleep 30
              STATE=$(astro deployment inspect cmpncv8rk8dfc01j7s24vh17h \
                --key metadata.status 2>/dev/null || echo "UNKNOWN")
              if [[ "$STATE" == *"HEALTHY"* || "$STATE" == *"ACTIVE"* ]]; then break; fi
            done
          fi

      - name: Trigger github_ingest DAG
        run: |
          HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
            "${{ secrets.AIRFLOW_API_URL }}/dags/github_ingest/dagRuns" \
            -H "Authorization: Bearer ${{ secrets.ASTRONOMER_API_KEY }}" \
            -H "Content-Type: application/json" \
            -d "{\"dag_run_id\": \"debounce_${{ github.run_id }}\", \
                 \"logical_date\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}")
          [ "$HTTP_STATUS" -ge 200 ] && [ "$HTTP_STATUS" -lt 300 ] || exit 1
```

### `paths-ignore: Pipeline/data_v2/**`

Without this, the debounce workflow would fire on the DAG's own commits (each `commit_to_github` call creates a commit on `main`), causing an infinite loop:

```
github_ingest commits github_*.md
  → debounce-trigger fires
    → 5h later, github_ingest runs again
      → commits github_*.md
        → debounce-trigger fires
          → ...
```

The `paths-ignore` breaks the loop: bot commits that only touch `Pipeline/data_v2/` are invisible to this workflow.

### Wake Step

The Astro Cloud deployment has a hibernation schedule (sleeps during off-hours to save credits). If the 5-hour sleep ends while the deployment is hibernating, the API call would return `503 no healthy upstream`. The wake step handles this:

1. Checks deployment state via `astro deployment inspect --key metadata.status`
2. If `HIBERNATING`: calls `astro deployment wake-up --force --for 2h`
   - `--force` skips the interactive confirmation prompt (required for CI)
   - `--for 2h` keeps it awake long enough for the DAG to complete
3. Polls every 30 seconds (up to 10 min) until state is `HEALTHY`
4. Then proceeds to trigger the DAG

### Airflow REST API Call

```bash
POST https://cmpncv8rk8dfc01j7s24vh17h.7h.astronomer.run/d24vh17h/api/v2/dags/github_ingest/dagRuns
```

**Key points:**
- **`/api/v2`** — Airflow 3.x changed the REST API path from `/api/v1` to `/api/v2`
- **`logical_date` is required** — Airflow 3.x requires this field in the request body. In Airflow 2.x it was optional. Without it, the API returns HTTP 422.
- **Auth** — Bearer token using `ASTRONOMER_API_KEY` (the same workspace token used for Astro CLI operations)

**How to find the correct API URL** if you ever need it:
```
astro deployment inspect cmpncv8rk8dfc01j7s24vh17h
```
Look for `airflow_api_url` in the `metadata` section of the output.

### GHA Secrets Required

| Secret | Purpose |
|---|---|
| `ASTRONOMER_API_KEY` | Astro Cloud workspace API token — authenticates both CLI commands and Airflow REST API calls |
| `AIRFLOW_API_URL` | `https://cmpncv8rk8dfc01j7s24vh17h.7h.astronomer.run/d24vh17h/api/v2` |

---

## `.github/workflows/astro-deploy.yml`

Deploys changes to the Airflow project (DAG code, helpers, requirements, Dockerfile) to Astro Cloud automatically when those files change. Created because the `astro deploy` CLI had persistent WSL relay errors on Windows.

```yaml
name: Deploy to Astro Cloud

on:
  push:
    branches: [main]
    paths:
      - 'airflow/dags/**'
      - 'airflow/include/**'
      - 'airflow/requirements.txt'
      - 'airflow/Dockerfile'
      - 'airflow/packages.txt'
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Install Astro CLI
        run: curl -sSL https://install.astronomer.io | sudo bash -s

      - name: Wake deployment if hibernating
        env:
          ASTRO_API_TOKEN: ${{ secrets.ASTRONOMER_API_KEY }}
        run: |
          STATE=$(astro deployment inspect cmpncv8rk8dfc01j7s24vh17h \
            --key configuration.deployment_state 2>/dev/null || echo "UNKNOWN")
          if [[ "$STATE" == *"HIBERNAT"* ]]; then
            astro deployment wake-up cmpncv8rk8dfc01j7s24vh17h --force
            for i in $(seq 1 20); do
              sleep 30
              STATE=$(astro deployment inspect cmpncv8rk8dfc01j7s24vh17h \
                --key configuration.deployment_state 2>/dev/null || echo "UNKNOWN")
              [[ "$STATE" == *"ACTIVE"* || "$STATE" == *"HEALTHY"* ]] && break
            done
          fi

      - name: Deploy to Astro Cloud
        uses: astronomer/deploy-action@v0.13.0
        with:
          deployment-id: cmpncv8rk8dfc01j7s24vh17h
          root-folder: airflow
          force: true
        env:
          ASTRO_API_TOKEN: ${{ secrets.ASTRONOMER_API_KEY }}
```

**`root-folder: airflow`** — tells the action where the Astro project lives. Without this, it looks for `dags/`, `requirements.txt`, etc. at the repo root.

**`force: true`** — skips pytest and parse error checks. Does not skip file-change detection.

**`ASTRO_API_TOKEN: ${{ secrets.ASTRONOMER_API_KEY }}`** — the env var name changed between action versions: `ASTRONOMER_API_KEY` (v0.7) → `ASTRO_API_TOKEN` (v0.13.0). The GitHub secret is still named `ASTRONOMER_API_KEY`; we map it here.

**Three bugs fixed iteratively:**

| # | Error | Root Cause | Fix |
|---|---|---|---|
| 1 | `invalid input 'workspace-id'` | `workspace-id` is not a valid param for this action | Removed it |
| 2 | `fatal: not a git repository` | Action looked for Astro project at repo root | Added `root-folder: airflow` |
| 3 | `conditional binary operator expected` (exit 2) on `workflow_dispatch` | v0.7 does `git diff` to detect deploy type. No base SHA on `workflow_dispatch` — bash comparison breaks | Upgraded to `v0.13.0` + renamed env var |

---

## Astro Cloud Deployment

- **Deployment name**: `vaughn-rag-ingest`
- **Deployment ID**: `cmpncv8rk8dfc01j7s24vh17h`
- **Airflow version**: 3.2.1 (Astro Runtime 3.2-4)
- **Webserver URL**: `https://cmpncv8rk8dfc01j7s24vh17h.7h.astronomer.run/d24vh17h`
- **REST API base URL**: `https://cmpncv8rk8dfc01j7s24vh17h.7h.astronomer.run/d24vh17h/api/v2`
- **Cloud**: Azure, eastus2

**Hibernation schedule** (saves credits during off-hours):
- Hibernate: `30 8 * * 0,1,3,5` (8:30 AM UTC on Sun, Mon, Wed, Fri)
- Wake: `30 6 * * 0,1,3,5` (6:30 AM UTC on Sun, Mon, Wed, Fri)

**Variables set in Astro Cloud UI (Admin → Variables):**

| Variable | Value |
|---|---|
| `GITHUB_TOKEN` | Fine-grained PAT, Contents: read+write on `VDEugenio/AI-Chatbot` |

---

## `.github/workflows/ingest-and-deploy.yml`

### Trigger

```yaml
on:
  push:
    branches: [main]
    paths:
      - 'Pipeline/data_v2/github_*.md'
  workflow_dispatch:
```

Fires only when the DAG's output files change. `workflow_dispatch` allows manual triggering from the GitHub Actions UI.

### Concurrency

```yaml
concurrency:
  group: ingest-and-deploy
  cancel-in-progress: false
```

Queues concurrent runs rather than cancelling them. `false` is important — cancelling a partially complete deploy could leave App Runner in an inconsistent state.

### Job 1: `ingest`

Installs `Pipeline/requirements.txt`, runs `python ingest.py --rebuild` (with `OPENAI_API_KEY`), validates `chunk_count > 0`, uploads `Pipeline/chroma_db/` as a 1-day artifact, and sends a Telegram message with chunk count and an approval link.

### Job 2: `deploy`

```yaml
deploy:
  needs: ingest
  environment: production
```

`environment: production` triggers the GitHub Environment gate — the job pauses until you approve in the GitHub UI.

Steps: download chroma_db artifact → AWS/ECR login → verify App Runner `RUNNING` → determine next `:vN` tag → `docker build` (chroma_db baked in) → push to ECR → `update-service` (derives `SourceConfiguration` from live service to preserve env vars) → poll until `RUNNING` → smoke test `/health` → Telegram success/failure message.

### IAM Policy (user: `vaughn-rag-gha-deployer`)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Sid": "ECRLogin", "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken", "Resource": "*" },
    { "Sid": "ECRPush", "Effect": "Allow",
      "Action": ["ecr:BatchCheckLayerAvailability", "ecr:InitiateLayerUpload",
                 "ecr:UploadLayerPart", "ecr:CompleteLayerUpload", "ecr:PutImage",
                 "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
      "Resource": "arn:aws:ecr:us-east-1:841979603625:repository/vaughn-rag-backend" },
    { "Sid": "AppRunnerDeploy", "Effect": "Allow",
      "Action": ["apprunner:DescribeService", "apprunner:UpdateService"],
      "Resource": "arn:aws:apprunner:us-east-1:841979603625:service/vaughn-rag-backend/4dddfb340c624fcb9f2b4b62598a831f" },
    { "Sid": "PassRoleToAppRunner", "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::841979603625:role/AppRunnerECRAccessRole" }
  ]
}
```

**The `PassRoleToAppRunner` statement trips people up.** When `update-service` changes the image, App Runner internally re-authenticates with ECR using `AppRunnerECRAccessRole`. AWS requires `iam:PassRole` on that role to permit this. Without it, `update-service` returns `AccessDeniedException` even when `apprunner:UpdateService` is granted.

### GitHub Environment: `production`

Located at: `github.com/VDEugenio/AI-Chatbot → Settings → Environments → production`

- **Required reviewers**: VDEugenio
- **Branch policy**: `main` only
- **No wait timer** — the wait timer is a mandatory minimum delay, NOT a timeout. It was removed after discovering it blocked deploys for 19+ hours.

### GitHub Actions Secrets Required

| Secret | Purpose |
|---|---|
| `OPENAI_API_KEY` | Used by `ingest.py --rebuild` to call OpenAI embeddings API |
| `AWS_ACCESS_KEY_ID` | IAM user `vaughn-rag-gha-deployer` credentials |
| `AWS_SECRET_ACCESS_KEY` | Same IAM user |
| `TELEGRAM_BOT_TOKEN` | Bot API token for notifications |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID |
| `ASTRONOMER_API_KEY` | Astro Cloud workspace token (also used by debounce and astro-deploy workflows) |
| `AIRFLOW_API_URL` | `https://cmpncv8rk8dfc01j7s24vh17h.7h.astronomer.run/d24vh17h/api/v2` |

---

## Key Airflow Concepts Used

### TaskFlow API (`@dag`, `@task`)

The modern way to define Airflow DAGs (Airflow 2.x+). Instead of instantiating operator objects and chaining with `>>`, you write plain Python functions decorated with `@task`. Return values are automatically serialised to XCom, and passing a task's return value as an argument to another task creates both a data and an execution dependency automatically.

### XCom (Cross-Communication)

Airflow's built-in key-value store for passing data between tasks. Values are stored in Airflow's metadata database (PostgreSQL). For larger payloads (like multiple markdown files), use the **path-based XCom pattern**: write data to `/tmp/`, pass the file path via XCom, read the file in the next task.

### Airflow Variables

Encrypted key-value store for secrets and configuration. Accessed at runtime with `Variable.get("KEY_NAME")`. Values are masked in logs. Set via Airflow UI → Admin → Variables, or via `astro deployment airflow-variable create`.

### `catchup=False`

Prevents backfill runs when a DAG is first enabled. Without it, Airflow tries to run all missed scheduled intervals since `start_date`.

### `schedule=None`

The DAG is manually triggered only — it won't run on any automatic schedule. In this project, triggering is handled externally by the GHA debounce workflow via the Airflow REST API.

### Retries

`@task(retries=2, retry_delay=timedelta(minutes=5))` — if a task raises an exception, Airflow waits `retry_delay` and retries up to `retries` times. Critical for tasks calling the GitHub API (rate limits, transient errors).

### Airflow REST API (Airflow 3.x)

Airflow ships with a built-in REST API. On Astro Cloud it's publicly accessible. Key differences from Airflow 2.x:
- **Path changed**: `/api/v1/` → `/api/v2/`
- **`logical_date` is required** in `POST /dags/{dag_id}/dagRuns` request body
- **Auth**: Bearer token (the Astro workspace API token)

---

## All Bugs Encountered and Fixed

| # | Component | Issue | Fix |
|---|---|---|---|
| 1 | Local dev | Docker Desktop wouldn't open | Installed Rancher Desktop 1.22.3 with moby engine |
| 2 | Local dev | Podman machines claimed the Docker socket → `crun: Permission denied` | `podman machine stop` before each `astro dev start` |
| 3 | `fetch_repos` | Wrong repo slug used | Corrected to `VDEugenio/AI-Chatbot` |
| 4 | `commit_to_github` | `update_file()` requires SHA; new files raise 404 | `try get_contents → update_file; except UnknownObjectException: create_file` |
| 5 | `commit_to_github` | Stale cleanup would list ALL files in `data_v2/`, risking deletion of handwritten docs | Filter by `startswith("github_") and endswith(".md")` before deleting |
| 6 | `Pipeline/requirements.txt` | `unstructured` took 15 min in CI, was never imported | Removed `unstructured` and `markdown` |
| 7 | `ingest-and-deploy.yml` | `update-service` → `AccessDeniedException` | Added `iam:PassRole` to IAM inline policy |
| 8 | `ingest-and-deploy.yml` | GitHub Environment wait timer blocked deploys for 19+ hours | Removed wait timer — it's a minimum delay, not a timeout |
| 9 | `astro-deploy.yml` | `invalid input 'workspace-id'` | Removed — not a valid param for this action |
| 10 | `astro-deploy.yml` | `fatal: not a git repository` | Added `root-folder: airflow` |
| 11 | `astro-deploy.yml` | `conditional binary operator expected` (exit 2) on `workflow_dispatch` | Upgraded from `v0.7` to `v0.13.0`; renamed env var to `ASTRO_API_TOKEN` |
| 12 | `astro deploy` CLI | `execvpe(/bin/bash) failed: No such file or directory` (WSL relay error) | Replaced CLI-based deploy with `astronomer/deploy-action` in GHA |
| 13 | `debounce-trigger.yml` | Wrong `AIRFLOW_API_URL` — was `cmpncv8rk8dfc01j7s24vh17h.astronomer.run/api/v1`, missing `.7h.` subdomain segment and `/d24vh17h` path, wrong API version | Used `astro deployment inspect` to find correct URL; changed to `/api/v2` |
| 14 | `debounce-trigger.yml` | `astro deployment wake --force` → `unknown flag: --force` | Wrong subcommand. Correct command is `astro deployment wake-up` |
| 15 | `debounce-trigger.yml` | `wake-up` without `--force` prompts `(y/n)` → cancelled in CI (non-interactive) | Added `--force` flag to skip confirmation |
| 16 | `debounce-trigger.yml` | HTTP 422 from Airflow API — `logical_date: Field required` | Added `"logical_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"` to request body (Airflow 3.x requirement) |
| 17 | `astro-deploy.yml` | `Deploy is blocked because Deployment is in HIBERNATING state` | Added wake step before deploy action; uses same `wake-up --force` pattern |

---

## Common Operations

### Add a New Portfolio Repo

1. Add `"owner/repo"` to `PORTFOLIO_REPOS` in `github_ingest_dag.py`
2. Commit and push — `astro-deploy.yml` fires and deploys the updated DAG to Astro Cloud
3. On the next trigger, the DAG fetches the new repo and commits a new `github_*.md` file
4. `ingest-and-deploy.yml` fires, rebuilds ChromaDB, and (after approval) redeploys the Backend

### Remove a Portfolio Repo

1. Remove the entry from `PORTFOLIO_REPOS`
2. Commit and push — `astro-deploy.yml` deploys the updated DAG
3. On the next trigger, `commit_to_github` detects the stale file and deletes it
4. `ingest-and-deploy.yml` fires, rebuilds ChromaDB without the removed repo

### Manually Trigger the DAG

- **Airflow UI**: Go to the deployment URL → `github_ingest` → click ▶ Trigger DAG
- **REST API**:
  ```bash
  curl -X POST \
    "https://cmpncv8rk8dfc01j7s24vh17h.7h.astronomer.run/d24vh17h/api/v2/dags/github_ingest/dagRuns" \
    -H "Authorization: Bearer <ASTRONOMER_API_KEY>" \
    -H "Content-Type: application/json" \
    -d "{\"dag_run_id\": \"manual_$(date +%s)\", \"logical_date\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"
  ```

### Check Deployment State

```bash
astro deployment inspect cmpncv8rk8dfc01j7s24vh17h
```

Look for `metadata.status`. Possible values: `HEALTHY`, `HIBERNATING`, `DEPLOYING`, `UNHEALTHY`.

### Wake the Deployment Manually

```bash
astro deployment wake-up cmpncv8rk8dfc01j7s24vh17h --force --for 2h
```
