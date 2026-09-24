"""Sends code diffs to Gemini and builds a Markdown review report.

Consolidates the two divergent LLM integrations from the old prototype
(raw google-generativeai in app.py vs. LangChain in ai_agent.py) into a
single, tested path.
"""

from __future__ import annotations

import logging
import time

from google import genai
from google.genai import errors as genai_errors

from .github_client import FileChange

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are a Senior Software Engineer reviewing a colleague's \
pull request. Review this change to '{filename}'.

Focus only on:
1. Security risks (e.g. SQL injection, hardcoded secrets/credentials)
2. Performance issues (e.g. inefficient loops, N+1 queries)
3. Code quality (e.g. naming, missing type hints, dead code)

Be concise and direct. If the code has no issues in these areas, say so \
plainly instead of inventing nitpicks. Format your response as Markdown.

CODE PATCH:
{patch}
"""

# Models are tried in order; if one isn't available for the caller's API
# key/region, we fall back to the next rather than failing outright.
FALLBACK_MODELS = ("gemini-flash-latest",)


class ReviewError(RuntimeError):
    """Raised when a file could not be reviewed after all retries/fallbacks."""


class CodeReviewer:
    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-flash-latest",
        max_retries: int = 3,
        base_wait_seconds: int = 30,
    ):
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name
        self._max_retries = max_retries
        self._base_wait_seconds = base_wait_seconds

    def _generate(self, model_name: str, prompt: str) -> str:
        response = self._client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        return response.text

    def _review_one_patch(self, filename: str, patch: str) -> str:
        prompt = PROMPT_TEMPLATE.format(filename=filename, patch=patch)

        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                logger.info("Reviewing %s (attempt %d)", filename, attempt)
                return self._generate(self._model_name, prompt)
            except genai_errors.APIError as exc:
                last_error = exc

                if exc.code == 429:
                    wait = self._base_wait_seconds * attempt
                    logger.warning(
                        "Rate limited reviewing %s, waiting %ds", filename, wait
                    )
                    time.sleep(wait)
                    continue

                if exc.code == 404:
                    for fallback in FALLBACK_MODELS:
                        try:
                            logger.warning(
                                "Model %s unavailable, trying fallback %s",
                                self._model_name,
                                fallback,
                            )
                            return self._generate(fallback, prompt)
                        except genai_errors.APIError as fallback_exc:
                            last_error = fallback_exc
                    break

                # Unrecognized error: don't burn retries on it.
                break

        raise ReviewError(
            f"Failed to review {filename} after {attempt} attempt(s): {last_error}"
        )

    def review_files(self, changes: list[FileChange]) -> str:
        """Review each changed file and return one combined Markdown report."""
        if not changes:
            return "No Python file changes found in this pull request."

        sections = ["## AI Code Review\n"]
        for change in changes:
            try:
                review = self._review_one_patch(change.filename, change.patch)
            except ReviewError as exc:
                review = f"_Could not complete review: {exc}_"
            sections.append(f"### `{change.filename}`\n\n{review}\n\n---\n")

        return "\n".join(sections)