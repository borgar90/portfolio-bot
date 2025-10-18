"""Generate a portfolio summary based on public GitHub data.

Usage examples:

    python scripts/github_summary.py --username borgar90
    python scripts/github_summary.py --username borgar90 --tokenEnv GITHUB_TOKEN --output me/summary.txt

The script calls the public GitHub REST API, so unauthenticated requests are limited
(60 requests/hour). Provide a personal access token via --token or --tokenEnv for
higher limits. The script intentionally keeps output deterministic and ASCII-only so it
can be consumed directly by the portfolio bot.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections import Counter
from datetime import datetime
from typing import Dict, Iterable, List, Optional

import requests

GITHUB_API_BASE = "https://api.github.com"
DEFAULT_MAX_REPOS = 8
REQUEST_TIMEOUT = 15  # seconds
MAX_RETRIES = 3
RETRY_SLEEP_SECONDS = 2

QUALITY_CHECK_PATHS = {
    "has_ci": [".github/workflows"],
    "has_tests": ["tests", "test", "spec", "__tests__"],
    "has_docs": ["docs", "documentation", "wiki"],
    "has_linting": [
        ".pre-commit-config.yaml",
        ".flake8",
        "pyproject.toml",
        "setup.cfg",
        "tox.ini",
        "package.json",
        ".eslintrc.json",
        ".eslint.js",
    ],
    "has_docker": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yaml"],
}


class GithubApiError(RuntimeError):
    """Raised when the GitHub API returns an unexpected response."""


def _build_headers(token: Optional[str]) -> Dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "portfolio-bot-summary-script",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def github_request(url: str, token: Optional[str] = None, params: Optional[dict] = None) -> dict:
    """Perform a GET request against the GitHub API with basic retry handling."""

    headers = _build_headers(token)

    for attempt in range(1, MAX_RETRIES + 1):
        response = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()

        # Surface helpful error messages for common failure cases.
        if response.status_code == 404:
            raise GithubApiError(f"Resource not found at {url}. Check the username and try again.")
        if response.status_code == 401:
            raise GithubApiError("Authentication failed. Verify that your GitHub token is valid.")
        if response.status_code in {403, 429}:
            reset = response.headers.get("X-RateLimit-Reset")
            if reset:
                reset_time = datetime.fromtimestamp(int(reset)).isoformat()
                raise GithubApiError(
                    "GitHub API rate limit exceeded. Provide a token or wait until "
                    f"after {reset_time}."
                )

        if attempt == MAX_RETRIES:
            raise GithubApiError(
                f"GitHub API request failed (status={response.status_code}). Body: {response.text}"
            )

        time.sleep(RETRY_SLEEP_SECONDS)

    # This line is unreachable but satisfies type checkers.
    raise GithubApiError("Unexpected failure contacting the GitHub API.")


def repo_path_exists(owner: str, repo: str, path: str, token: Optional[str]) -> bool:
    """Return True if the repository contains the given path, False for 404."""

    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
    headers = _build_headers(token)
    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    if response.status_code == 200:
        return True
    if response.status_code == 404:
        return False

    raise GithubApiError(
        f"Unable to inspect path '{path}' in {owner}/{repo}. "
        f"Status: {response.status_code}. Body: {response.text}"
    )


def inspect_repo_quality(repo: dict, token: Optional[str]) -> Dict[str, Optional[str]]:
    owner = repo.get("owner", {}).get("login", "")
    name = repo.get("name", "")
    if not owner or not name:
        return {}

    def _path_any(paths: List[str]) -> bool:
        for path in paths:
            try:
                if repo_path_exists(owner, name, path, token):
                    return True
            except GithubApiError as exc:
                # Surface non-404 errors immediately so users understand what failed.
                if "Status: 404" not in str(exc):
                    raise
        return False

    quality = {}
    for key, paths in QUALITY_CHECK_PATHS.items():
        quality[key] = _path_any(paths)

    # README is almost always present; fallback to content flag.
    try:
        quality["has_readme"] = repo_path_exists(owner, name, "README.md", token) or repo_path_exists(
            owner, name, "README", token
        )
    except GithubApiError:
        quality["has_readme"] = False

    license_info = repo.get("license") or {}
    quality["license"] = license_info.get("spdx_id") or license_info.get("name")
    quality["open_issues"] = int(repo.get("open_issues_count") or 0)
    quality["has_issues_enabled"] = bool(repo.get("has_issues", False))
    quality["default_branch"] = repo.get("default_branch")
    quality["has_discussions"] = bool(repo.get("has_discussions", False))

    return quality


def fetch_user(username: str, token: Optional[str]) -> dict:
    return github_request(f"{GITHUB_API_BASE}/users/{username}", token)


def fetch_repositories(username: str, token: Optional[str]) -> List[dict]:
    """Fetch all public repositories owned by the user (non-fork by default)."""

    repos: List[dict] = []
    page = 1
    while True:
        page_data = github_request(
            f"{GITHUB_API_BASE}/users/{username}/repos",
            token,
            params={
                "per_page": 100,
                "page": page,
                "type": "owner",
                "sort": "updated",
                "direction": "desc",
            },
        )
        if not page_data:
            break
        repos.extend(page_data)
        if len(page_data) < 100:
            break
        page += 1
    return repos


def human_join(items: Iterable[str]) -> str:
    items = [item for item in items if item]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f" and {items[-1]}"


def format_repo_line(repo: dict) -> str:
    topics = repo.get("topics") or []
    topic_str = f" | Topics: {', '.join(topics[:5])}" if topics else ""
    stats = []
    if repo.get("stargazers_count"):
        stats.append(f"★ {repo['stargazers_count']}")
    if repo.get("forks_count"):
        stats.append(f"Forks {repo['forks_count']}")
    stats_str = f" ({', '.join(stats)})" if stats else ""
    language = repo.get("language") or "Unknown"
    description = repo.get("description") or "No description provided"
    pushed_at = repo.get("pushed_at")
    last_update = ""
    if pushed_at:
        last_update = datetime.fromisoformat(pushed_at.replace("Z", "+00:00")).date().isoformat()
    last_update_str = f" | Last update: {last_update}" if last_update else ""
    return (
        f"- {repo['name']} [{language}]{stats_str}{last_update_str}\n"
        f"  {description}{topic_str}\n"
        f"  Repository: {repo['html_url']}"
    )


def generate_summary(user: dict, repos: List[dict], max_repos: int, include_forks: bool, token: Optional[str]) -> str:
    if not include_forks:
        repos = [repo for repo in repos if not repo.get("fork")]

    if not repos:
        raise GithubApiError("No public repositories found to summarise. Add repos or use --include-forks.")

    # Language statistics based on the primary language field.
    language_counter = Counter(repo.get("language") or "Other" for repo in repos)
    total_repos = len(repos)
    top_languages = language_counter.most_common(5)

    # Determine highlight repositories by stars, then recency as a tiebreaker.
    repos_sorted = sorted(
        repos,
        key=lambda r: (
            r.get("stargazers_count", 0),
            r.get("watchers_count", 0),
            r.get("pushed_at") or "",
        ),
        reverse=True,
    )
    highlight_repos = repos_sorted[:max_repos]
    quality_reports: List[Dict[str, Optional[str]]] = []
    for repo in highlight_repos:
        try:
            quality_reports.append(inspect_repo_quality(repo, token))
        except GithubApiError as exc:
            quality_reports.append({"error": str(exc)})

    lines: List[str] = []
    name = user.get("name") or user.get("login")
    headline_parts = [name]
    if user.get("company"):
        headline_parts.append(f"({user['company']})")
    headline = " ".join(headline_parts)

    location = user.get("location")
    followers = user.get("followers") or 0
    public_repos = user.get("public_repos") or total_repos
    bio = user.get("bio")

    lines.append(f"GitHub profile summary for {headline} ({user['html_url']}).")
    if bio:
        lines.append(bio.strip())

    context_bits = []
    if location:
        context_bits.append(f"Based in {location}")
    context_bits.append(f"{followers} followers")
    context_bits.append(f"{public_repos} public repositories")
    lines.append("; ".join(context_bits) + ".")

    lines.append("")
    lines.append("Primary languages:")
    for language, count in top_languages:
        percent = (count / total_repos) * 100
        lines.append(f"- {language}: {count} repos ({percent:.1f}% of portfolio)")

    lines.append("")
    lines.append(f"Highlighted repositories (top {len(highlight_repos)} by stars and recent activity):")
    for repo, quality in zip(highlight_repos, quality_reports):
        lines.append(format_repo_line(repo))
        quality_notes: List[str] = []
        if quality.get("error"):
            quality_notes.append(f"Quality analysis unavailable: {quality['error']}")
        else:
            if quality.get("has_ci"):
                quality_notes.append("CI/CD workflows configured")
            if quality.get("has_tests"):
                quality_notes.append("Automated tests present")
            if quality.get("has_docs"):
                quality_notes.append("Project documentation directory")
            if quality.get("has_linting"):
                quality_notes.append("Linting/config automation files")
            if quality.get("has_docker"):
                quality_notes.append("Containerization assets")
            if quality.get("has_readme") is False:
                quality_notes.append("Missing README")
            license_name = quality.get("license")
            if license_name:
                quality_notes.append(f"License: {license_name}")
            if quality.get("has_issues_enabled"):
                quality_notes.append("Issues enabled")
            if quality.get("has_discussions"):
                quality_notes.append("GitHub Discussions enabled")
            open_issues = quality.get("open_issues")
            if isinstance(open_issues, int) and open_issues > 0:
                quality_notes.append(f"Open issues: {open_issues}")

        if quality_notes:
            lines.append("  Quality signals: " + "; ".join(quality_notes))
        lines.append("")

    lines.append("Recent activity:")
    recent_repos = sorted(repos, key=lambda r: r.get("pushed_at") or "", reverse=True)[:5]
    for repo in recent_repos:
        pushed_at = repo.get("pushed_at")
        last_update = "unknown"
        if pushed_at:
            last_update = datetime.fromisoformat(pushed_at.replace("Z", "+00:00")).date().isoformat()
        lines.append(f"- {repo['name']} updated on {last_update}")

    lines.append("")
    lines.append("How to collaborate:")
    if user.get("blog"):
        lines.append(f"- Portfolio or blog: {user['blog']}")
    if user.get("email"):
        lines.append(f"- Email: {user['email']}")
    lines.append(f"- GitHub profile: {user['html_url']}")

    if quality_reports:
        lines.append("")
        lines.append("Aggregate quality indicators across highlighted repositories:")
        repo_count = len([q for q in quality_reports if not q.get("error")])
        if repo_count:
            def _count_true(flag: str) -> int:
                return sum(1 for q in quality_reports if not q.get("error") and q.get(flag))

            lines.append(f"- CI/CD workflows present in {_count_true('has_ci')} of {repo_count}")
            lines.append(f"- Automated tests in {_count_true('has_tests')} of {repo_count}")
            lines.append(f"- Dedicated docs folders in {_count_true('has_docs')} of {repo_count}")
            lines.append(f"- Lint/tooling configs in {_count_true('has_linting')} of {repo_count}")
            lines.append(f"- Containerization support in {_count_true('has_docker')} of {repo_count}")

    lines.append("")
    lines.append("Generated on " + datetime.utcnow().isoformat() + "Z")

    return "\n".join(lines).strip() + "\n"


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a GitHub-powered summary for the portfolio bot.")
    parser.add_argument("--username", required=True, help="GitHub username to summarise")
    parser.add_argument("--output", default="me/summary.txt", help="Path to write the summary (default: me/summary.txt)")
    parser.add_argument("--max-repos", type=int, default=DEFAULT_MAX_REPOS, help="Number of highlighted repositories to include")
    parser.add_argument("--include-forks", action="store_true", help="Include forked repositories in statistics")
    parser.add_argument(
        "--token",
        help="GitHub personal access token. Use when running many requests or when rate-limited.",
    )
    parser.add_argument(
        "--tokenEnv",
        default="",
        help="Environment variable name that stores the GitHub token (alternative to --token).",
    )
    return parser.parse_args(argv)


def resolve_token(args: argparse.Namespace) -> Optional[str]:
    if args.token:
        return args.token
    if args.tokenEnv:
        return os.getenv(args.tokenEnv)
    return None


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    token = resolve_token(args)

    try:
        user = fetch_user(args.username, token)
        repos = fetch_repositories(args.username, token)
        summary = generate_summary(
            user,
            repos,
            max_repos=max(args.max_repos, 1),
            include_forks=args.include_forks,
            token=token,
        )
    except GithubApiError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"Network error contacting GitHub: {exc}", file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(summary)

    print(f"Summary written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
