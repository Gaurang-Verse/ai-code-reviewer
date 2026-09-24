"""Unit tests for the review/retry/fallback logic in reviewer.py.

These tests mock the google-genai Client entirely - no real API key or
network access is needed to run them.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from google.genai import errors as genai_errors

from ai_code_reviewer.github_client import FileChange
from ai_code_reviewer.reviewer import CodeReviewer, ReviewError


def make_reviewer(**overrides) -> CodeReviewer:
    defaults = dict(
        api_key="fake-key",
        model_name="gemini-2.0-flash",
        max_retries=2,
        base_wait_seconds=0,  # keep tests fast
    )
    defaults.update(overrides)
    with patch("ai_code_reviewer.reviewer.genai.Client"):
        return CodeReviewer(**defaults)


def api_error(code: int, message: str = "error") -> genai_errors.APIError:
    return genai_errors.APIError(
        code=code, response_json={"message": message, "status": message}
    )


@patch("ai_code_reviewer.reviewer.genai.Client")
def test_review_files_returns_report_for_each_file(mock_client_cls):
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MagicMock(text="Looks fine.")
    mock_client_cls.return_value = mock_client

    reviewer = make_reviewer()
    reviewer._client = mock_client  # ensure our instance uses this mock
    changes = [FileChange(filename="app.py", patch="+ print('hi')")]

    report = reviewer.review_files(changes)

    assert "app.py" in report
    assert "Looks fine." in report


def test_review_files_with_no_changes_short_circuits():
    reviewer = make_reviewer()
    report = reviewer.review_files([])
    assert "No Python file changes" in report


@patch("ai_code_reviewer.reviewer.time.sleep", return_value=None)
def test_rate_limit_triggers_retry_then_succeeds(mock_sleep):
    reviewer = make_reviewer(max_retries=3)
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [
        api_error(429, "RESOURCE_EXHAUSTED"),
        MagicMock(text="All good after retry."),
    ]
    reviewer._client = mock_client

    result = reviewer._review_one_patch("f.py", "diff")

    assert result == "All good after retry."
    assert mock_sleep.called


def test_model_not_found_falls_back():
    reviewer = make_reviewer()
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [
        api_error(404, "model not found"),
        MagicMock(text="Fallback review."),
    ]
    reviewer._client = mock_client

    result = reviewer._review_one_patch("f.py", "diff")

    assert result == "Fallback review."


def test_unrecoverable_error_raises_review_error():
    reviewer = make_reviewer()
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = api_error(500, "server error")
    reviewer._client = mock_client

    with pytest.raises(ReviewError):
        reviewer._review_one_patch("f.py", "diff")