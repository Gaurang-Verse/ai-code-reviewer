"""Command-line entry point.

Usage:
    python -m ai_code_reviewer.cli --repo owner/name --pr 12
    python -m ai_code_reviewer.cli --repo owner/name --pr 12 --dry-run

With no --repo/--pr, it tries to detect them from the GitHub Actions
environment (GITHUB_REPOSITORY + the pull_request event payload), so the
same command works unchanged in the GitHub Action workflow.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from .config import ConfigError, load_settings
from .github_client import GitHubPRClient
from .reviewer import CodeReviewer

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def detect_github_actions_context() -> tuple[str | None, int | None]:
    """Best-effort detection of repo/PR number from the GitHub Actions
    environment, so the workflow doesn't need to hardcode them."""
    repo = os.getenv("GITHUB_REPOSITORY")
    pr_number: int | None = None

    event_path = os.getenv("GITHUB_EVENT_PATH")
    if event_path and os.path.exists(event_path):
        try:
            with open(event_path, encoding="utf-8") as f:
                event = json.load(f)
            pr_number = (event.get("pull_request") or {}).get("number") or event.get(
                "number"
            )
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not parse GITHUB_EVENT_PATH: %s", exc)

    return repo, pr_number


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", help="owner/name of the repository (default: auto-detect in CI)"
    )
    parser.add_argument(
        "--pr", type=int, help="pull request number (default: auto-detect in CI)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the review to stdout instead of posting it to GitHub",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    detected_repo, detected_pr = detect_github_actions_context()
    repo_name = args.repo or detected_repo
    pr_number = args.pr or detected_pr

    if not repo_name or not pr_number:
        logger.error(
            "Could not determine repository/PR number. Pass --repo and --pr, "
            "or run this inside a GitHub Actions pull_request workflow."
        )
        return 2

    try:
        settings = load_settings()
    except ConfigError as exc:
        logger.error(str(exc))
        return 2

    gh_client = GitHubPRClient(settings.github_token)
    reviewer = CodeReviewer(
        api_key=settings.google_api_key,
        model_name=settings.gemini_model,
        max_retries=settings.max_retries,
        base_wait_seconds=settings.base_retry_wait_seconds,
    )

    logger.info("Fetching PR #%s from %s", pr_number, repo_name)
    changes, pr = gh_client.get_python_file_changes(repo_name, pr_number)
    logger.info("Found %d changed Python file(s)", len(changes))

    report = reviewer.review_files(changes)

    if args.dry_run:
        print(report)
        return 0

    gh_client.post_comment(pr, report)
    logger.info("Review posted to PR #%s", pr_number)
    return 0


if __name__ == "__main__":
    sys.exit(main())
