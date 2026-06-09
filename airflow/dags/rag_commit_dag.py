"""
RAG Commit DAG
==============

Triggered externally by the RAG backend after the user submits answers on
/rag-review. Fetches enriched markdown files (baseline + developer notes
synthesized by Claude) from the backend, then commits them to Pipeline/data_v2/
in the GitHub repo via the PyGithub API.

Downstream CI/CD (GitHub Actions ingest-and-deploy.yml) handles:
    commit -> ingest -> build -> deploy

Task graph:
    fetch_enriched_files
        -> commit_to_github

Trigger: REST API call from backend (POST /api/v2/dags/rag_commit/dagRuns)
         with conf: {"run_id": "<run_id>"}

Airflow Variables required:
    GITHUB_TOKEN    Fine-grained PAT (same one used by github_ingest DAG)
    BACKEND_URL     RAG backend base URL (e.g. https://chat.vaughneugenio.com)
    ADMIN_KEY       Backend admin key for GET /api/rag-run/{run_id}/files
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.models import Variable

_INCLUDE_DIR = Path("/usr/local/airflow/include")
if str(_INCLUDE_DIR) not in sys.path:
    sys.path.insert(0, str(_INCLUDE_DIR))


@dag(
    dag_id="rag_commit",
    schedule=None,
    start_date=datetime(2026, 5, 22),
    catchup=False,
    tags=["rag", "ingestion"],
    default_args={
        "owner": "airflow",
        "depends_on_past": False,
    },
    doc_md=__doc__,
)
def rag_commit() -> None:
    """RAG enriched-content commit pipeline."""

    @task(retries=2, retry_delay=timedelta(minutes=2))
    def fetch_enriched_files(**context) -> list[dict]:
        """
        Fetch enriched markdown files from the backend for this run_id.

        Returns the list of {"filename": str, "content": str} dicts directly
        via XCom. No /tmp/ involved — each Astro Cloud task runs in its own
        container, so /tmp/ is not shared between tasks.
        """
        import requests

        run_id      = context["dag_run"].conf.get("run_id")
        backend_url = Variable.get("BACKEND_URL")
        admin_key   = Variable.get("ADMIN_KEY")

        if not run_id:
            raise ValueError("dag_run.conf must contain 'run_id'")

        response = requests.get(
            f"{backend_url}/api/rag-run/{run_id}/files",
            headers={"X-Admin-Key": admin_key},
            timeout=30,
        )
        response.raise_for_status()

        files: list[dict] = response.json()["files"]
        print(f"[fetch_enriched_files] Fetched {len(files)} enriched file(s) for run_id={run_id}")
        return files

    @task(retries=2, retry_delay=timedelta(minutes=5))
    def commit_to_github(files: list[dict]) -> str:
        """
        Commit enriched markdown files to Pipeline/data_v2/ in a single batched
        commit using the GitHub low-level Git API.

        All files are uploaded as blobs, assembled into one tree, and pushed as
        one commit — regardless of how many files are being enriched. This avoids
        the per-file commit race where each individual commit fires a separate
        GitHub Actions trigger and the triggers cancel each other.

        Only creates/updates files — never deletes (stale cleanup is handled
        by the github_ingest DAG, not this one).
        """
        from github import Github, InputGitTreeElement

        token = Variable.get("GITHUB_TOKEN")
        g = Github(token)
        repo = g.get_repo("VDEugenio/AI-Chatbot")
        data_prefix = "Pipeline/data_v2"

        # 1. Create a blob for every file.
        blobs = []
        for file_item in files:
            blob = repo.create_git_blob(file_item["content"], "utf-8")
            blobs.append(blob)
            print(f"[commit_to_github] Blob created for {file_item['filename']} ({blob.sha[:7]})")

        # 2. Build the tree using InputGitTreeElement objects (required by PyGithub 2.x).
        tree_list = [
            InputGitTreeElement(
                path=f"{data_prefix}/{file_item['filename']}",
                mode="100644",
                type="blob",
                sha=blob.sha,
            )
            for file_item, blob in zip(files, blobs)
        ]

        # 3. Resolve the current HEAD commit and its tree.
        head_ref = repo.get_git_ref("heads/main")
        head_sha = head_ref.object.sha
        base_tree_sha = repo.get_git_commit(head_sha).tree.sha

        # 4. Create a new tree on top of the existing one.
        new_tree = repo.create_git_tree(
            tree_list,
            base_tree=repo.get_git_tree(base_tree_sha),
        )

        # 5. Create the commit.
        n = len(files)
        commit_message = f"[bot] Enrich {n} RAG file(s) with developer notes"
        new_commit = repo.create_git_commit(
            commit_message,
            new_tree,
            [repo.get_git_commit(head_sha)],
        )

        # 6. Advance the ref.
        head_ref.edit(new_commit.sha)

        print(
            f"[commit_to_github] Single commit {new_commit.sha[:7]} — "
            f"{n} file(s) pushed to {data_prefix}/"
        )
        return data_prefix

    files = fetch_enriched_files()
    commit_to_github(files)


rag_commit()
