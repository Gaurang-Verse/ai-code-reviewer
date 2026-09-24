"""Thin wrapper around PyGithub for the two operations this tool needs:
reading a pull request's changed Python files, and posting a comment back.

Consolidates what used to be duplicated across app.py, github_client.py,
and debug_github.py in the old prototype.
"""

from __future__ import annotations

from dataclasses import dataclass

from github import Auth, Github
from github.PullRequest import PullRequest


@dataclass(frozen=True)
class FileChange:
    filename: str
    patch: str


class GitHubPRClient:
    """Reads pull request diffs and posts review comments."""

    def __init__(self, token: str):
        self._gh = Github(auth=Auth.Token(token))

    def whoami(self) -> str:
        """Return the authenticated user's login. Useful for a quick
        connectivity/token sanity check (replaces debug_github.py)."""
        return self._gh.get_user().login

    def get_pull_request(self, repo_name: str, pr_number: int) -> PullRequest:
        repo = self._gh.get_repo(repo_name)
        return repo.get_pull(pr_number)

    def get_python_file_changes(
        self, repo_name: str, pr_number: int
    ) -> tuple[list[FileChange], PullRequest]:
        """Return the .py file diffs for a PR, plus the PR object itself
        (so the caller can post a comment on it without a second lookup).
        """
        pr = self.get_pull_request(repo_name, pr_number)
        changes = [
            FileChange(filename=f.filename, patch=f.patch)
            for f in pr.get_files()
            if f.filename.endswith(".py") and f.patch
        ]
        return changes, pr

    def post_comment(self, pr: PullRequest, body: str) -> None:
        pr.create_issue_comment(body)
