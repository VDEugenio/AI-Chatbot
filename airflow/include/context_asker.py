"""
context_asker.py
================

Helpers for the ask_for_context task in github_ingest_dag.

Public functions:
    generate_questions(repos, api_key)      -> str
    parse_questions_to_list(raw_text)       -> list[dict]
    post_run_to_backend(run_id, repos_questions, formatted_files, backend_url) -> None
    send_telegram(message, bot_token, chat_id) -> None
"""

from __future__ import annotations

import json

import anthropic
import requests
from github import Github

_SYSTEM_PROMPT = (
    "You are a RAG knowledge-base quality reviewer. Your job is to read GitHub repo metadata "
    "and identify specific context gaps that would hurt retrieval quality in a RAG system used "
    "by a recruiter-facing AI chatbot. For each gap, write a direct, specific question to the "
    "developer (addressed as \"you\"). Ask as many questions as genuinely needed per repo — but "
    "skip a repo entirely if it already looks complete and well-documented. Only ask questions "
    "whose answers would meaningfully improve the RAG knowledge base. Format your response "
    "exactly as: \"### <repo name>\\n- <question>\\n- <question>...\" with a blank line between "
    "repos. If there are no gaps across all repos, return an empty string."
    "Where existing enriched documentation is provided, treat it as the ground truth for what "
    "has already been answered. Only ask questions whose answers are absent or materially "
    "incomplete in that existing content."
)

def fetch_existing_files(token: str, repo_name: str) -> dict[str, str]:
    """
    Fetches all existing github_*.md files from Pipeline/data_v2/ in the
    given GitHub repo. Returns a dict mapping filename to decoded content.
    Returns an empty dict on any failure (first run, path missing, etc.)
    so it never blocks the DAG.
    """
    try:
        from github import Github
        g = Github(token)
        repo = g.get_repo(repo_name)
        contents = repo.get_contents("Pipeline/data_v2")
        result = {}
        for entry in contents:
            if entry.name.startswith("github_") and entry.name.endswith(".md"):
                try:
                    result[entry.name] = entry.decoded_content.decode("utf-8")
                except Exception as exc:
                    print(f"[fetch_existing_files] Warning: could not decode {entry.name}: {exc}")
        print(f"[fetch_existing_files] Fetched {len(result)} existing file(s).")
        return result
    except Exception as exc:
        print(f"[fetch_existing_files] Warning: could not fetch existing files: {exc}")
        return {}


_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
_TELEGRAM_MAX_CHARS = 4096


def generate_questions(repos: list[dict], api_key: str, existing_files: dict | None = None) -> str:
    """
    Call Claude to identify RAG context gaps in the fetched repo metadata.

    Parameters
    ----------
    repos:
        List of repo dicts as returned by github_fetcher.fetch_repo_data().
        Each dict has: full_name, description, readme, languages, commits,
        file_structure.
    api_key:
        Anthropic API key.

    Returns
    -------
    str
        Raw text from Claude (formatted questions), or empty string if Claude
        found no context gaps or returned an empty response.
    """
    client = anthropic.Anthropic(api_key=api_key)

    if existing_files:
        existing_block = "\n\n".join(
            f"--- {fname} ---\n{content}"
            for fname, content in existing_files.items()
        )
        user_content = (
            "=== RAW REPO METADATA (freshly fetched from GitHub API) ===\n"
            + json.dumps(repos, ensure_ascii=False, default=str)
            + "\n\n=== EXISTING ENRICHED DOCUMENTATION (previously committed to Pipeline/data_v2/) ===\n"
            "The following files were written by a previous run and may already answer some questions. "
            "Do NOT ask questions whose answers are clearly present in these files.\n\n"
            + existing_block
        )
    else:
        user_content = json.dumps(repos, ensure_ascii=False, default=str)

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2048,
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": user_content,
            }
        ],
    )

    # Extract the text content from the first content block.
    if not message.content:
        return ""

    text = message.content[0].text if hasattr(message.content[0], "text") else ""
    return text or ""


def parse_questions_to_list(raw_text: str) -> list[dict]:
    """
    Parse Claude's markdown response into a structured list of repo/question dicts.

    Expected input format::

        ### VDEugenio/VaughnKey
        - question one
        - question two

        ### VDEugenio/AI-Chatbot
        - question three

    Parameters
    ----------
    raw_text:
        Raw markdown string returned by generate_questions().

    Returns
    -------
    list[dict]
        Each dict has the shape::

            {"repo_name": "VDEugenio/VaughnKey", "questions": ["q1", "q2"]}

        Repos with no question lines are omitted.
    """
    result: list[dict] = []
    current_repo: str | None = None
    current_questions: list[str] = []

    for line in raw_text.splitlines():
        if line.startswith("### "):
            # Flush the previous repo if it had questions.
            if current_repo is not None and current_questions:
                result.append({"repo_name": current_repo, "questions": current_questions})
            current_repo = line[4:]  # preserve exactly what appears after "### "
            current_questions = []
        elif line.startswith("- ") and current_repo is not None:
            current_questions.append(line[2:])

    # Flush the last repo.
    if current_repo is not None and current_questions:
        result.append({"repo_name": current_repo, "questions": current_questions})

    return result


def post_run_to_backend(
    run_id: str,
    repos_questions: list[dict],
    formatted_files: list[dict],
    backend_url: str,
) -> None:
    """
    POST the run's questions and formatted files to the RAG backend.

    Parameters
    ----------
    run_id:
        The Airflow run ID for this DAG run.
    repos_questions:
        Output of parse_questions_to_list() — list of repo/question dicts.
    formatted_files:
        The list of {filename, content} dicts loaded from the format_markdown
        temp file.
    backend_url:
        Base URL of the RAG backend (e.g. https://chat.vaughneugenio.com).

    Raises
    ------
    requests.HTTPError
        If the backend returns a non-2xx HTTP status.
    """
    body = {
        "run_id": run_id,
        "repos": repos_questions,
        "files": formatted_files,
    }
    response = requests.post(
        f"{backend_url}/api/rag-questions",
        json=body,
        timeout=30,
    )
    response.raise_for_status()


def send_telegram(message: str, bot_token: str, chat_id: str) -> None:
    """
    Send a message to a Telegram chat via the Bot API.

    If the message exceeds 4096 characters, it is split into chunks at
    newline boundaries so each chunk fits within Telegram's limit.

    Parameters
    ----------
    message:
        The text to send. Supports Markdown formatting.
    bot_token:
        Telegram bot token from BotFather.
    chat_id:
        Target chat ID (obtain via getUpdates after the user messages the bot).

    Raises
    ------
    requests.HTTPError
        If any API request returns a non-2xx HTTP status.
    """
    message = message + "\n\n🔗 Answer at: https://vaughneugenio.com/rag-review"
    url = _TELEGRAM_API.format(token=bot_token)

    chunks = _split_message(message)
    for chunk in chunks:
        response = requests.post(
            url,
            params={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "Markdown",
            },
            timeout=30,
        )
        response.raise_for_status()


def _split_message(message: str) -> list[str]:
    """
    Split a message into chunks that each fit within Telegram's 4096-char
    limit, breaking only at newline boundaries.
    """
    if len(message) <= _TELEGRAM_MAX_CHARS:
        return [message]

    chunks: list[str] = []
    lines = message.splitlines(keepends=True)
    current_chunk = ""

    for line in lines:
        if len(current_chunk) + len(line) > _TELEGRAM_MAX_CHARS:
            if current_chunk:
                chunks.append(current_chunk)
            # If a single line itself exceeds the limit, hard-split it.
            while len(line) > _TELEGRAM_MAX_CHARS:
                chunks.append(line[:_TELEGRAM_MAX_CHARS])
                line = line[_TELEGRAM_MAX_CHARS:]
            current_chunk = line
        else:
            current_chunk += line

    if current_chunk:
        chunks.append(current_chunk)

    return chunks
