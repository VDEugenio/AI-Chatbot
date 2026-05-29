"""
GitHub RAG Ingestion DAG
========================

Runs daily. Fetches content from a hardcoded list of portfolio GitHub repos,
formats each repo as a markdown file with YAML frontmatter, then commits the
files directly to the repository via the GitHub API. No local filesystem
access — fully compatible with Astro Cloud.

Downstream CI/CD (GitHub Actions) handles: ingest -> build -> deploy.

Task graph:
    fetch_repos
        -> format_markdown
            -> commit_to_github  (pushes github_*.md to repo via GitHub API)
                        |
            GitHub Actions handles: ingest -> build -> deploy

Airflow concepts demonstrated:
    - TaskFlow API (@dag, @task decorators)
    - XCom (data passed as function return values / arguments)
    - Path-based XCom for larger payloads (format_markdown -> commit_to_github)
    - Retries on tasks that call external APIs
    - Airflow Variables for secrets (GITHUB_TOKEN)
    - catchup=False to prevent backfill on first enable
    - Stale file cleanup for idempotent runs
    - GitHub API commits via PyGithub (no local filesystem — Astro Cloud compatible)

Prerequisites (set before first run):
    Airflow UI -> Admin -> Variables:
        GITHUB_TOKEN    GitHub Fine-Grained PAT with Contents (read + write) permission
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.models import Variable

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

# ---------------------------------------------------------------------------
# Portfolio repos to index.
# Format: "owner/repo"
# Add or remove repos here. Files for repos not in this list will be
# automatically deleted from Pipeline/data_v2/ in the GitHub repo on the
# next run (stale file cleanup).
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
    schedule=None,                  # triggered externally via GHA debounce workflow
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
    """Daily GitHub -> repo commit ingestion pipeline."""

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
    # Task 3: Commit formatted github_*.md files to the repo via the
    # GitHub API.
    #
    # Reads the temp JSON written by format_markdown, then uses PyGithub
    # to create or update each file in Pipeline/data_v2/. Also deletes any
    # stale github_*.md files in the repo that are no longer in the current
    # fetch list.
    #
    # No local filesystem access — fully compatible with Astro Cloud.
    # Returns the data directory path prefix as a log-friendly confirmation.
    # ------------------------------------------------------------------
    @task(retries=2, retry_delay=timedelta(minutes=5))
    def commit_to_github(tmp_path: str) -> str:
        import json
        from github import Github
        from github.GithubException import UnknownObjectException

        token = Variable.get("GITHUB_TOKEN")
        g = Github(token)
        repo = g.get_repo("VDEugenio/AI-Chatbot")

        with open(tmp_path, "r", encoding="utf-8") as fh:
            files: list[dict] = json.load(fh)

        incoming_names = {item["filename"] for item in files}
        data_prefix = "Pipeline/data_v2"

        # Remove stale github_*.md files no longer in the current fetch list.
        try:
            contents = repo.get_contents(data_prefix)
            for entry in contents:
                if entry.name.startswith("github_") and entry.name.endswith(".md"):
                    if entry.name not in incoming_names:
                        repo.delete_file(
                            entry.path,
                            f"[bot] Remove stale {entry.name}",
                            entry.sha,
                        )
                        print(f"[commit_to_github] Deleted stale: {entry.name}")
        except Exception as exc:
            print(f"[commit_to_github] Warning: could not check for stale files: {exc}")

        # Create or update each github_*.md file.
        for file_item in files:
            path = f"{data_prefix}/{file_item['filename']}"
            content = file_item["content"]
            try:
                existing = repo.get_contents(path)
                repo.update_file(
                    path,
                    f"[bot] Update {file_item['filename']}",
                    content,
                    existing.sha,
                )
                print(f"[commit_to_github] Updated {path}")
            except UnknownObjectException:
                repo.create_file(
                    path,
                    f"[bot] Add {file_item['filename']}",
                    content,
                )
                print(f"[commit_to_github] Created {path}")

        # Clean up the temp file now that we're done with it.
        Path(tmp_path).unlink(missing_ok=True)

        print(f"[commit_to_github] Done — {len(files)} file(s) committed to {data_prefix}/")
        return data_prefix

    # ------------------------------------------------------------------
    # Wire up task dependencies.
    #
    # With the TaskFlow API, passing a task's return value as an argument
    # to the next task automatically creates a dependency.
    # ------------------------------------------------------------------
    repos_data = fetch_repos()
    tmp_path = format_markdown(repos_data)
    commit_to_github(tmp_path)


github_ingest()
