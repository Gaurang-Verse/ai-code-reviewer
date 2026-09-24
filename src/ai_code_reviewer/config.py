"""Configuration loading and validation.

All secrets and tunables come from environment variables (loaded from a
local .env file in development, or from GitHub Actions secrets in CI).
Nothing is hardcoded here, and nothing is committed to source control.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    github_token: str
    google_api_key: str
    gemini_model: str = "gemini-2.0-flash"
    max_retries: int = 3
    base_retry_wait_seconds: int = 30


def load_settings() -> Settings:
    """Read and validate required settings from the environment.

    Raises:
        ConfigError: if a required environment variable is missing.
    """
    github_token = os.getenv("GITHUB_TOKEN")
    google_api_key = os.getenv("GOOGLE_API_KEY")

    missing = [
        name
        for name, value in (
            ("GITHUB_TOKEN", github_token),
            ("GOOGLE_API_KEY", google_api_key),
        )
        if not value
    ]
    if missing:
        raise ConfigError(
            "Missing required environment variable(s): "
            + ", ".join(missing)
            + ". Set them in a .env file locally, or as repository "
            "secrets when running in GitHub Actions."
        )

    return Settings(
        github_token=github_token,
        google_api_key=google_api_key,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
        base_retry_wait_seconds=int(os.getenv("BASE_RETRY_WAIT_SECONDS", "30")),
    )
