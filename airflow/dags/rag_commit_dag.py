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

import json
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
    def fetch_enriched_files(**context) -> str:
        """
        Fetch enriched markdown files from the backend for this run_id.

        Returns the path to a temp JSON file containing a list of
        {"filename": str, "content": str} dicts.
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

        run_id_safe = run_id.replace(":", "_").replace("+", "_")
        tmp_path = f"/tmp/rag_commit_{run_id_safe}.json"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(files, fh, ensure_ascii=False)

        return tmp_path

    @task(retries=2, retry_delay=timedelta(minutes=5))
    def commit_to_github(tmp_path: str) -> str:
        """
        Commit enriched markdown files to Pipeline/data_v2/ via the GitHub API.

        Only creates/updates files — never deletes (stale cleanup is handled
        by the github_ingest DAG, not this one).
        """
        from github import Github
        from github.GithubException import UnknownObjectException

        token = Variable.get("GITHUB_TOKEN")
        g = Github(token)
        repo = g.get_repo("VDEugenio/AI-Chatbot")
        data_prefix = "Pipeline/data_v2"

        with open(tmp_path, "r", encoding="utf-8") as fh:
            files: list[dict] = json.load(fh)

        for file_item in files:
            path = f"{data_prefix}/{file_item['filename']}"
            content = file_item["content"]
            try:
                existing = repo.get_contents(path)
                repo.update_file(
                    path,
                    f"[bot] Enrich {file_item['filename']} with developer notes",
                    content,
                    existing.sha,
                )
                print(f"[commit_to_github] Updated {path}")
            except UnknownObjectException:
                repo.create_file(
                    path,
                    f"[bot] Add {file_item['filename']} with developer notes",
                    content,
                )
                print(f"[commit_to_github] Created {path}")

        Path(tmp_path).unlink(missing_ok=True)
        print(f"[commit_to_github] Done — {len(files)} file(s) committed to {data_prefix}/")
        return data_prefix

    tmp_path = fetch_enriched_files()
    commit_to_github(tmp_path)


rag_commit()
