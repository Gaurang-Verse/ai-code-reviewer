"""Unit tests for GitHubPRClient. Mocks PyGithub entirely."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ai_code_reviewer.github_client import GitHubPRClient


def make_file(filename: str, patch: str | None):
    f = MagicMock()
    f.filename = filename
    f.patch = patch
    return f


@patch("ai_code_reviewer.github_client.Github")
def test_get_python_file_changes_filters_non_python_and_empty_patches(mock_github_cls):
    mock_pr = MagicMock()
    mock_pr.get_files.return_value = [
        make_file("app.py", "+ x = 1"),
        make_file("README.md", "+ docs change"),
        make_file("binary.png", None),
    ]

    mock_repo = MagicMock()
    mock_repo.get_pull.return_value = mock_pr

    mock_gh = MagicMock()
    mock_gh.get_repo.return_value = mock_repo
    mock_github_cls.return_value = mock_gh

    client = GitHubPRClient(token="fake-token")
    changes, pr = client.get_python_file_changes("owner/repo", 1)

    assert len(changes) == 1
    assert changes[0].filename == "app.py"
    assert pr is mock_pr


@patch("ai_code_reviewer.github_client.Github")
def test_post_comment_calls_create_issue_comment(mock_github_cls):
    client = GitHubPRClient(token="fake-token")
    mock_pr = MagicMock()

    client.post_comment(mock_pr, "review body")

    mock_pr.create_issue_comment.assert_called_once_with("review body")
