"""
Converts a repo data dict (produced by github_fetcher.fetch_repo_data) into
a markdown string with YAML frontmatter compatible with Pipeline/ingest.py.

The frontmatter schema matches the existing data_v2/ files so that retrieval
filtering, company tags, and chunk metadata all work without changes to the
backend.
"""

from __future__ import annotations


def filename_for_repo(full_name: str) -> str:
    """
    Return the markdown filename for a given repo.

    "VDEugenio/RAG_Vaughn" -> "github_VDEugenio_RAG_Vaughn.md"

    The "github_" prefix lets write_files() identify and clean up stale
    files when a repo is removed from the fetch list.
    """
    safe = full_name.replace("/", "_").replace("-", "_")
    return f"github_{safe}.md"


def repo_to_markdown(repo: dict) -> str:
    """
    Convert a repo data dict into a markdown string with YAML frontmatter.

    Frontmatter fields:
        name         Human-readable title shown in retrieval traces
        company      "personal" — GitHub repos ARE personal projects, so they must
                     match the company tag used by hand-written project files
                     (a "personal projects" query pre-filters on company=personal)
        source       "github_dag" — provenance marker distinguishing DAG-generated
                     files from hand-written ones (this used to be conflated into
                     company: github)
        repo_url     Direct link to the GitHub repository
        topics       Static tags plus any detected topic keywords
        skills       Top programming languages from the repo's language stats
        story_types  Always "project" for GitHub repos

    Content sections (only included when data is present):
        Overview     Description + truncated README
        Tech Stack   Language percentages
        Recent Activity  Last 10 commit messages with dates
        File Structure   Top-level files and directories
    """
    full_name = repo["full_name"]
    _, repo_name = full_name.split("/", 1)

    # Build skills list from top languages (lowercase, underscores for spaces)
    languages: dict[str, float] = repo.get("languages", {})
    top_langs = sorted(languages, key=lambda l: -languages[l])[:5]
    skills_str = ", ".join(lang.lower().replace(" ", "_") for lang in top_langs)

    repo_url = f"https://github.com/{full_name}"
    frontmatter = (
        "---\n"
        f"name: {repo_name} (GitHub Repository)\n"
        "company: personal\n"
        "source: github_dag\n"
        f"repo_url: {repo_url}\n"
        "topics: [github, portfolio, open_source, personal_projects]\n"
        f"skills: [{skills_str}]\n"
        "story_types: [project]\n"
        "---"
    )

    sections: list[str] = []

    # Repo link line — kept in the body (not just frontmatter) so the URL is
    # part of the chunk text and the chatbot can cite it in answers.
    sections.append(
        f"This is one of Vaughn's personal projects. **GitHub repository:** {repo_url}"
    )

    # Overview: description + README
    overview_parts: list[str] = []
    if repo.get("description"):
        overview_parts.append(repo["description"])
    if repo.get("readme"):
        overview_parts.append(repo["readme"])
    if overview_parts:
        sections.append("## Overview\n\n" + "\n\n".join(overview_parts))

    # Tech Stack
    if languages:
        by_pct = sorted(languages.items(), key=lambda x: -x[1])
        lang_lines = "\n".join(f"- {lang}: {pct}%" for lang, pct in by_pct)
        sections.append(f"## Tech Stack\n\n{lang_lines}")

    # Recent Activity
    commits: list[dict] = repo.get("commits", [])
    if commits:
        commit_lines = "\n".join(
            f"- [{c['date']}] {c['message']}" for c in commits
        )
        sections.append(f"## Recent Activity\n\n{commit_lines}")

    # File Structure
    file_structure: list[str] = repo.get("file_structure", [])
    if file_structure:
        structure_lines = "\n".join(f"- {f}" for f in file_structure)
        sections.append(f"## File Structure\n\n{structure_lines}")

    body = "\n\n".join(sections)
    return f"{frontmatter}\n\n{body}\n"
