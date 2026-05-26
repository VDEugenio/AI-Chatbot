"""
GitHub RAG Ingestion DAG
========================

Runs daily. Fetches content from a hardcoded list of portfolio GitHub repos,
formats each repo as a markdown file with YAML frontmatter, writes them into
Pipeline/data_v2/, then triggers a full rebuild of the ChromaDB vector store
by calling ingest.py --rebuild.

Task graph:
    fetch_repos
        -> format_markdown
            -> write_files
                -> run_ingest   (BashOperator)
                    -> validate_index

Airflow concepts demonstrated:
    - TaskFlow API (@dag, @task decorators)
    - XCom (data passed as function return values / arguments)
    - Path-based XCom for larger payloads (format_markdown -> write_files)
    - BashOperator for shelling out to an existing script
    - Retries on tasks that call external APIs
    - Airflow Variables for secrets (GITHUB_TOKEN, OPENAI_API_KEY)
    - catchup=False to prevent backfill on first enable
    - Stale file cleanup for idempotent runs

Prerequisites (set before first run):
    Airflow UI -> Admin -> Variables:
        GITHUB_TOKEN    GitHub Fine-Grained PAT with Contents (read) permission
        OPENAI_API_KEY  OpenAI API key (used by ingest.py for embeddings)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.providers.standard.operators.bash import BashOperator

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Add include/ to sys.path so github_fetcher and markdown_formatter are
# importable. Astro Runtime typically adds this automatically, but we add it
# explicitly here as a safety measure so the import works regardless of how
# the DAG is executed.
_INCLUDE_DIR = Path("/usr/local/airflow/include")
if str(_INCLUDE_DIR) not in sys.path:
    sys.path.insert(0, str(_INCLUDE_DIR))

# Path to the Pipeline directory inside the container (via volume mount).
# Defined here as a constant so it's easy to update if the mount path changes.
PIPELINE_DIR = Path("/pipeline")
DATA_DIR = PIPELINE_DIR / "data_v2"

# ---------------------------------------------------------------------------
# Portfolio repos to index.
# Format: "owner/repo"
# Add or remove repos here. Files for repos not in this list will be
# automatically deleted from data_v2/ on the next run (stale file cleanup).
# ---------------------------------------------------------------------------
PORTFOLIO_REPOS: list[str] = [
    "VDEugenio/AI-Chatbot",
    "VDEugenio/Job-Application-Tracker",
    "VDEugenio/VaughnKey",
    "VDEugenio/adf-marketplace",
]


# ---------------------------------------------------------------------------
# DAG definition
# ---------------------------------------------------------------------------

@dag(
    dag_id="github_ingest",
    schedule="0 6 * * *",          # daily at 6 AM
    start_date=datetime(2026, 5, 22),
    catchup=False,                  # don't backfill missed runs
    tags=["rag", "ingestion"],
    default_args={
        "owner": "airflow",
        "depends_on_past": False,
    },
    doc_md=__doc__,
)
def github_ingest() -> None:
    """Daily GitHub -> ChromaDB ingestion pipeline."""

    # ------------------------------------------------------------------
    # Task 1: Fetch repo data from the GitHub API.
    #
    # Returns a list of dicts (one per repo) containing README content,
    # language stats, recent commits, and top-level file structure.
    # This list is serialised into XCom automatically by the TaskFlow API.
    #
    # retries=2 handles transient GitHub API failures (rate limits,
    # network hiccups). retry_delay gives the API time to recover.
    # ------------------------------------------------------------------
    @task(retries=2, retry_delay=timedelta(minutes=5))
    def fetch_repos() -> list[dict]:
        from github_fetcher import fetch_repo_data

        token = Variable.get("GITHUB_TOKEN")
        repos = fetch_repo_data(token, PORTFOLIO_REPOS)
        print(f"[fetch_repos] Fetched data for {len(repos)} repo(s): "
              f"{[r['full_name'] for r in repos]}")
        return repos

    # ------------------------------------------------------------------
    # Task 2: Format repo dicts as markdown strings.
    #
    # Writes all markdown content to a temporary JSON file (one object per
    # repo: {filename, content}) and returns the file path via XCom.
    #
    # We use a file-path XCom pattern here instead of passing the markdown
    # strings directly. This is the correct Airflow pattern for payloads
    # that could grow large as the repo list scales up.
    # ------------------------------------------------------------------
    @task(retries=2, retry_delay=timedelta(minutes=5))
    def format_markdown(repos: list[dict], **context) -> str:
        from markdown_formatter import filename_for_repo, repo_to_markdown

        # Sanitise run_id for use as a filename (colons are valid on Linux
        # but can cause confusion; replace for clarity).
        run_id = context["run_id"].replace(":", "_").replace("+", "_")
        tmp_path = f"/tmp/github_repos_{run_id}.json"

        files = []
        for repo in repos:
            filename = filename_for_repo(repo["full_name"])
            content = repo_to_markdown(repo)
            files.append({"filename": filename, "content": content})
            print(f"[format_markdown] Formatted {filename} ({len(content)} chars)")

        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(files, fh, ensure_ascii=False)

        print(f"[format_markdown] Wrote {len(files)} formatted file(s) to {tmp_path}")
        return tmp_path

    # ------------------------------------------------------------------
    # Task 3: Write markdown files into Pipeline/data_v2/.
    #
    # Also removes any stale github_*.md files from previous runs whose
    # repos are no longer in PORTFOLIO_REPOS. This keeps data_v2/ clean
    # when you remove a repo from the fetch list.
    # ------------------------------------------------------------------
    @task
    def write_files(tmp_path: str) -> list[str]:
        with open(tmp_path, "r", encoding="utf-8") as fh:
            files: list[dict] = json.load(fh)

        incoming_names = {item["filename"] for item in files}

        # Delete stale github_*.md files not in this run's fetch list.
        for stale in DATA_DIR.glob("github_*.md"):
            if stale.name not in incoming_names:
                stale.unlink()
                print(f"[write_files] Removed stale file: {stale.name}")

        # Write (overwrite) the current set of github_*.md files.
        written: list[str] = []
        for item in files:
            dest = DATA_DIR / item["filename"]
            dest.write_text(item["content"], encoding="utf-8")
            written.append(item["filename"])
            print(f"[write_files] Wrote {dest}")

        # Clean up the temp file now that we're done with it.
        Path(tmp_path).unlink(missing_ok=True)

        print(f"[write_files] Done. {len(written)} file(s) in {DATA_DIR}")
        return written

    # ------------------------------------------------------------------
    # Task 4: Run ingest.py --rebuild inside the Pipeline directory.
    #
    # This is a BashOperator (not a @task) because it shells out to an
    # existing script rather than running Python inline. The script:
    #   1. Loads all .md/.txt/.pdf files from data_v2/ (incl. the new
    #      github_*.md files written by the previous task)
    #   2. Chunks them with RecursiveCharacterTextSplitter
    #   3. Embeds with OpenAI text-embedding-3-small
    #   4. Deletes and recreates the ChromaDB collection
    #
    # OPENAI_API_KEY is injected from Airflow Variables via Jinja templating.
    # append_env=True merges it with the container's existing environment
    # (so PATH, PYTHONPATH, etc. are preserved).
    # ------------------------------------------------------------------
    run_ingest = BashOperator(
        task_id="run_ingest",
        bash_command="cd /pipeline && python ingest.py --rebuild",
        env={"OPENAI_API_KEY": "{{ var.value.OPENAI_API_KEY }}"},
        append_env=True,
    )

    # ------------------------------------------------------------------
    # Task 5: Validate the rebuilt index.
    #
    # Uses the low-level chromadb client directly (no LangChain wrapper,
    # no OpenAI key required) just to verify the collection exists and
    # has a sensible number of chunks.
    # ------------------------------------------------------------------
    @task
    def validate_index() -> None:
        import chromadb

        client = chromadb.PersistentClient(path=str(PIPELINE_DIR / "chroma_db"))
        collection = client.get_collection("vaughn_personal_docs")
        count = collection.count()

        if count == 0:
            raise ValueError(
                "ChromaDB collection is empty after rebuild. "
                "Check the run_ingest task logs for errors."
            )

        print(f"[validate_index] Collection 'vaughn_personal_docs' has {count} chunk(s). "
              f"Rebuild successful.")

    # ------------------------------------------------------------------
    # Wire up task dependencies.
    #
    # With the TaskFlow API, passing a task's return value as an argument
    # to the next task automatically creates a dependency. For BashOperator
    # (which isn't a @task), we use set_upstream() explicitly.
    # ------------------------------------------------------------------
    repos_data = fetch_repos()
    tmp_path = format_markdown(repos_data)
    written = write_files(tmp_path)
    run_ingest.set_upstream(written)
    validate_index().set_upstream(run_ingest)


github_ingest()
