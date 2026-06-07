"""RAG Review enrichment — synthesizes Q&A answers into enriched markdown via Claude."""
from __future__ import annotations

import json

from anthropic import AsyncAnthropic
from fastapi import HTTPException

from app.db import get_run, save_enriched_files


def filename_for_repo(repo_full_name: str) -> str:
    """Convert 'VDEugenio/VaughnKey' -> 'github_VDEugenio_VaughnKey.md'."""
    slug = repo_full_name.replace("/", "_").replace("-", "_")
    return f"github_{slug}.md"


async def synthesize_and_store(run_id: str, answers: list[dict], settings) -> None:
    """
    Enrich baseline markdown files with developer Q&A answers via Claude,
    then store the enriched files against the run_id for DAG 2 to commit.

    Parameters
    ----------
    run_id:
        The Airflow run ID identifying the review run.
    answers:
        List of dicts with keys: repo_name, question, answer.
        Empty answers are treated as skips.
    settings:
        App settings instance (provides anthropic_api_key, claude_model).
    """
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    baseline_files: list[dict] = json.loads(run["files_json"])

    # Group non-empty answers by repo_name.
    answers_by_repo: dict[str, list[dict]] = {}
    for a in answers:
        if a["answer"].strip():
            answers_by_repo.setdefault(a["repo_name"], []).append(a)

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    enriched_files: list[dict] = []

    for file in baseline_files:
        # Find the repo whose filename matches this file.
        matching_repo = next(
            (repo for repo in answers_by_repo if filename_for_repo(repo) == file["filename"]),
            None,
        )
        if matching_repo:
            qa_pairs = answers_by_repo[matching_repo]
            formatted_qa = "\n\n".join(
                f"Q: {a['question']}\nA: {a['answer']}" for a in qa_pairs
            )
            message = await client.messages.create(
                model=settings.claude_model,
                max_tokens=4096,
                system=(
                    "You are enriching a RAG knowledge-base markdown file for a recruiter-facing "
                    "AI chatbot. Given the existing markdown and Q&A pairs from the developer, "
                    "append a `## Developer Notes` section at the end synthesizing the answers "
                    "into clear prose. Preserve all existing YAML frontmatter and content exactly. "
                    "Ignore any questions with empty answers. Only output the complete updated "
                    "file — no commentary."
                ),
                messages=[{
                    "role": "user",
                    "content": f"EXISTING FILE:\n{file['content']}\n\nQ&A PAIRS:\n{formatted_qa}",
                }],
            )
            enriched_files.append({
                "filename": file["filename"],
                "content": message.content[0].text,
            })
        else:
            # No answers for this repo — keep baseline unchanged.
            enriched_files.append(file)

    save_enriched_files(run_id, enriched_files)
