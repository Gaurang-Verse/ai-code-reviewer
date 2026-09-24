"""Unit tests for the review/retry/fallback logic in reviewer.py.

These tests mock google.generativeai entirely - no real API key or network
access is needed to run them.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

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
    with patch("ai_code_reviewer.reviewer.genai.configure"):
        return CodeReviewer(**defaults)


@patch("ai_code_reviewer.reviewer.genai.GenerativeModel")
def test_review_files_returns_report_for_each_file(mock_model_cls):
    mock_model = MagicMock()
    mock_model.generate_content.return_value = MagicMock(text="Looks fine.")
    mock_model_cls.return_value = mock_model

    reviewer = make_reviewer()
    changes = [FileChange(filename="app.py", patch="+ print('hi')")]

    report = reviewer.review_files(changes)

    assert "app.py" in report
    assert "Looks fine." in report


def test_review_files_with_no_changes_short_circuits():
    reviewer = make_reviewer()
    report = reviewer.review_files([])
    assert "No Python file changes" in report


@patch("ai_code_reviewer.reviewer.time.sleep", return_value=None)
@patch("ai_code_reviewer.reviewer.genai.GenerativeModel")
def test_rate_limit_triggers_retry_then_succeeds(mock_model_cls, mock_sleep):
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = [
        Exception("429 RESOURCE_EXHAUSTED"),
        MagicMock(text="All good after retry."),
    ]
    mock_model_cls.return_value = mock_model

    reviewer = make_reviewer(max_retries=3)
    result = reviewer._review_one_patch("f.py", "diff")

    assert result == "All good after retry."
    assert mock_sleep.called


@patch("ai_code_reviewer.reviewer.genai.GenerativeModel")
def test_model_not_found_falls_back(mock_model_cls):
    primary_model = MagicMock()
    primary_model.generate_content.side_effect = Exception("404 model not found")

    fallback_model = MagicMock()
    fallback_model.generate_content.return_value = MagicMock(text="Fallback review.")

    mock_model_cls.side_effect = [primary_model, fallback_model]

    reviewer = make_reviewer()
    result = reviewer._review_one_patch("f.py", "diff")

    assert result == "Fallback review."


@patch("ai_code_reviewer.reviewer.genai.GenerativeModel")
def test_unrecoverable_error_raises_review_error(mock_model_cls):
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = Exception("boom, unrecoverable")
    mock_model_cls.return_value = mock_model

    reviewer = make_reviewer()
    with pytest.raises(ReviewError):
        reviewer._review_one_patch("f.py", "diff")
