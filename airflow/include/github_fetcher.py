"""
GitHub API helpers for the github_ingest DAG.

fetch_repo_data() is the only public entry point. It takes a GitHub token
and a list of "owner/repo" strings, and returns a list of dicts containing
the content needed to build each repo's markdown document.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def fetch_repo_data(token: str, repo_full_names: list[str]) -> list[dict]:
    """
    Fetch README, language stats, recent commits, and top-level file
    structure for each repo in repo_full_names.

    Returns a list of dicts with keys:
        full_name     str   "owner/repo"
        description   str   repo description (may be empty)
        readme        str   README content, truncated to 2000 chars
        languages     dict  {language: percentage_float}
        commits       list  [{sha, message, date}, ...]  (up to 10)
        file_structure list  top-level file/dir names (dirs end with "/")
    """
    from github import Github
    from github.GithubException import UnknownObjectException

    g = Github(token)
    results = []

    for full_name in repo_full_names:
        log.info("Fetching %s", full_name)
        try:
            repo = g.get_repo(full_name)
        except UnknownObjectException:
            log.warning("Repo not found or token has no access: %s", full_name)
            continue
        except Exception as exc:
            log.error("Failed to get repo %s: %s", full_name, exc)
            continue

        # README -------------------------------------------------------
        readme = ""
        try:
            readme_file = repo.get_readme()
            readme = readme_file.decoded_content.decode("utf-8", errors="replace")
            readme = readme[:2000]
        except UnknownObjectException:
            log.info("%s has no README", full_name)
        except Exception as exc:
            log.warning("Could not fetch README for %s: %s", full_name, exc)

        # Language stats -----------------------------------------------
        languages: dict[str, float] = {}
        try:
            lang_bytes = repo.get_languages()
            total = sum(lang_bytes.values()) or 1
            languages = {
                lang: round(count / total * 100, 1)
                for lang, count in lang_bytes.items()
            }
        except Exception as exc:
            log.warning("Could not fetch languages for %s: %s", full_name, exc)

        # Recent commits -----------------------------------------------
        commits: list[dict] = []
        try:
            for commit in list(repo.get_commits())[:10]:
                commits.append({
                    "sha": commit.sha[:7],
                    "message": commit.commit.message.split("\n")[0][:100],
                    "date": commit.commit.author.date.strftime("%Y-%m-%d"),
                })
        except Exception as exc:
            log.warning("Could not fetch commits for %s: %s", full_name, exc)

        # Top-level file structure -------------------------------------
        file_structure: list[str] = []
        try:
            for item in repo.get_contents(""):
                suffix = "/" if item.type == "dir" else ""
                file_structure.append(f"{item.name}{suffix}")
            file_structure = sorted(file_structure)
        except Exception as exc:
            log.warning("Could not fetch file structure for %s: %s", full_name, exc)

        results.append({
            "full_name": full_name,
            "description": repo.description or "",
            "readme": readme,
            "languages": languages,
            "commits": commits,
            "file_structure": file_structure,
        })

        log.info(
            "Fetched %s: %d commits, %d languages, README=%d chars",
            full_name, len(commits), len(languages), len(readme),
        )

    return results
