"""
GitHub RAG Ingestion DAG
========================

Triggered externally (GHA debounce workflow). Fetches content from a
hardcoded list of portfolio GitHub repos, formats each as a markdown file
with YAML frontmatter, then (in parallel):
  - commits the github_*.md files to the repo via the GitHub API, and
  - calls Claude to identify RAG context gaps and sends targeted questions
    to the developer via Telegram.

No local filesystem access — fully compatible with Astro Cloud (each task
runs in its own container; data is passed through XCom only).

Downstream CI/CD (GitHub Actions) handles: ingest -> build -> deploy.

Task graph:
    fetch_repos
        -> format_markdown
            -> commit_to_github  (pushes github_*.md to repo via GitHub API)
            -> ask_for_context   (Claude review + Telegram notification; runs
                                  in parallel with commit_to_github)

Airflow concepts demonstrated:
    - TaskFlow API (@dag, @task decorators)
    - XCom (data passed as function return values / arguments)
    - Retries on tasks that call external APIs
    - Airflow Variables for secrets
    - catchup=False to prevent backfill on first enable
    - Stale file cleanup for idempotent runs
    - GitHub API commits via PyGithub (no local filesystem — Astro Cloud compatible)
    - Parallel fan-out from a single upstream task result

Prerequisites — set these Airflow Variables before first run:
    GITHUB_TOKEN        GitHub Fine-Grained PAT with Contents (read + write)
    ANTHROPIC_API_KEY   Anthropic API key
    TELEGRAM_BOT_TOKEN  Telegram bot token (from BotFather)
    TELEGRAM_CHAT_ID    Telegram chat ID (see context_asker.py for how to obtain)
    BACKEND_URL         RAG backend base URL (e.g. https://chat.vaughneugenio.com)
"""

from __future__ import annotations

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
    "VDEugenio/outreach-extension",
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
    # Returns the formatted files list directly via XCom so downstream
    # tasks can access it without relying on a shared /tmp/ filesystem
    # (which is not guaranteed across task containers on Astro Cloud).
    # ------------------------------------------------------------------
    @task(retries=2, retry_delay=timedelta(minutes=5))
    def format_markdown(repos: list[dict]) -> list[dict]:
        from markdown_formatter import filename_for_repo, repo_to_markdown

        files = []
        for repo in repos:
            filename = filename_for_repo(repo["full_name"])
            content = repo_to_markdown(repo)
            files.append({"filename": filename, "content": content})
            print(f"[format_markdown] Formatted {filename} ({len(content)} chars)")

        print(f"[format_markdown] Formatted {len(files)} file(s)")
        return files

    # ------------------------------------------------------------------
    # Task 3: Commit formatted github_*.md files to the repo via the
    # GitHub API.
    #
    # Receives the formatted files list directly from XCom (no /tmp/
    # involved — each Astro Cloud task runs in its own container so
    # /tmp/ is not shared across tasks).
    #
    # Uses PyGithub to create or update each file in Pipeline/data_v2/.
    # Also deletes stale github_*.md files in the repo that are no
    # longer in the current fetch list.
    #
    # No local filesystem access — fully compatible with Astro Cloud.
    # Returns the data directory path prefix as a log-friendly confirmation.
    # ------------------------------------------------------------------
    @task(retries=2, retry_delay=timedelta(minutes=5))
    def commit_to_github(files: list[dict]) -> str:
        from github import Github
        from github.GithubException import UnknownObjectException

        token = Variable.get("GITHUB_TOKEN")
        g = Github(token)
        repo = g.get_repo("VDEugenio/AI-Chatbot")

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
                old_content = existing.decoded_content.decode("utf-8")
                if "## Developer Notes" in old_content:
                    notes_section = old_content[old_content.index("## Developer Notes"):]
                    content = content.rstrip() + "\n\n" + notes_section.strip()
                    print(f"[commit_to_github] Preserved Developer Notes in {file_item['filename']}")
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

        print(f"[commit_to_github] Done — {len(files)} file(s) committed to {data_prefix}/")
        return data_prefix

    # ------------------------------------------------------------------
    # Task 4: Ask for context gaps via Claude + Telegram.
    #
    # Runs in parallel with commit_to_github — both receive formatted_data
    # directly from format_markdown's XCom return value.
    #
    # Uses Claude to review the fetched repo metadata and identify gaps
    # that would hurt RAG retrieval quality, then POSTs the questions +
    # formatted files to the backend (BACKEND_URL/api/rag-questions) and
    # sends a Telegram notification linking to vaughneugenio.com/rag-review.
    # ------------------------------------------------------------------
    @task()
    def ask_for_context(repos: list[dict], formatted_files: list[dict], **context) -> None:
        """
        Uses the Claude API to identify RAG context gaps in each fetched repo,
        then sends targeted questions to the developer via Telegram.

        Runs in parallel with commit_to_github; both fan out from format_markdown.
        Data arrives via XCom injection (standard TaskFlow API — no trigger_rule
        workarounds needed).
        """
        from context_asker import generate_questions, parse_questions_to_list, post_run_to_backend, send_telegram, fetch_existing_files

        api_key      = Variable.get("ANTHROPIC_API_KEY")
        bot_token    = Variable.get("TELEGRAM_BOT_TOKEN")
        chat_id      = Variable.get("TELEGRAM_CHAT_ID")
        backend_url  = Variable.get("BACKEND_URL")
        github_token = Variable.get("GITHUB_TOKEN")
        run_id       = context["run_id"]

        existing_files = fetch_existing_files(github_token, "VDEugenio/AI-Chatbot")
        print(f"[ask_for_context] Fetched {len(existing_files)} existing enriched file(s) for context.")

        print(f"[ask_for_context] Got {len(repos)} repo(s) and {len(formatted_files)} file(s).")

        message = generate_questions(repos, api_key, existing_files=existing_files)

        if message.strip():
            repos_questions = parse_questions_to_list(message)
            try:
                post_run_to_backend(run_id, repos_questions, formatted_files, backend_url)
                print(f"[ask_for_context] Posted {len(repos_questions)} repo(s) to backend.")
            except Exception as exc:
                print(f"[ask_for_context] Warning: failed to post to backend: {exc}")
            send_telegram(message, bot_token, chat_id)
            print("[ask_for_context] Telegram notification sent.")
        else:
            print("[ask_for_context] Claude found no context gaps — no message sent.")

    # ------------------------------------------------------------------
    # Wire up task dependencies.
    #
    # With the TaskFlow API, passing a task's return value as an argument
    # automatically creates a data dependency (and therefore an execution
    # dependency). commit_to_github and ask_for_context both depend on
    # format_markdown and run in parallel once it completes.
    # ------------------------------------------------------------------
    repos_data     = fetch_repos()
    formatted_data = format_markdown(repos_data)
    commit_to_github(formatted_data)
    ask_for_context(repos_data, formatted_data)


github_ingest()
