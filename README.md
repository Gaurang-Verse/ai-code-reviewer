# AI Code Reviewer

An automated code review bot for GitHub pull requests. It fetches the
changed Python files in a PR, sends each diff to Google's Gemini model for
review, and posts the findings back as a PR comment.

It focuses on three things per file: security risks (e.g. SQL injection,
hardcoded secrets), performance issues (e.g. inefficient loops), and code
quality (naming, missing type hints, dead code).

## How it works

```
GitHub PR opened/updated
        |
        v
GitHub Action triggers  ->  fetch changed .py files (PyGithub)
        |
        v
Each file's diff sent to Gemini  ->  Markdown review generated
        |
        v
Review posted as a PR comment
```

## Project layout

```
src/ai_code_reviewer/
  config.py          # environment variable loading + validation
  github_client.py   # PyGithub wrapper: read PR diffs, post comments
  reviewer.py         # prompt building, Gemini calls, retry/fallback logic
  cli.py               # command-line entry point / GitHub Actions entry point
tests/                 # unit tests (mocked, no network or API key needed)
.github/workflows/     # the GitHub Action that runs this on every PR
```

## Setup

1. Clone the repo and install dependencies:

   ```bash
   git clone https://github.com/YOUR-USERNAME/ai-code-reviewer.git
   cd ai-code-reviewer
   python -m venv venv && source venv/bin/activate
   pip install -r requirements-dev.txt
   ```

2. Copy `.env.example` to `.env` and fill in your own values:

   ```bash
   cp .env.example .env
   ```

   You'll need:
   - `GITHUB_TOKEN` — a GitHub personal access token with `repo` scope.
   - `GOOGLE_API_KEY` — a Gemini API key from [Google AI Studio](https://aistudio.google.com/).

## Running locally

Review a specific PR and print the result instead of posting it:

```bash
python -m ai_code_reviewer.cli --repo owner/name --pr 12 --dry-run
```

Drop `--dry-run` to actually post the review as a comment on the PR.

## Running automatically on every PR (GitHub Action)

The workflow at `.github/workflows/pr-review.yml` runs this tool
automatically whenever a pull request is opened or updated. To enable it
on your repository:

1. Push this project to your repository.
2. In the repo's **Settings → Secrets and variables → Actions**, add a
   secret named `GOOGLE_API_KEY` with your Gemini API key.
   (`GITHUB_TOKEN` is provided automatically by GitHub Actions — you do
   not need to add it yourself.)
3. Open a pull request. The bot will comment with its review within a
   couple of minutes.

## Running tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests mock both the GitHub API and the Gemini API, so they run offline
and don't require any real credentials.

## Known limitations

- **`google-generativeai` is deprecated.** Google has stopped updating this
  SDK in favor of the newer `google-genai` package. This project still
  uses `google-generativeai` because it's simpler and was sufficient to
  get a clean, working, tested version out quickly — but migrating to
  `google-genai` should be the next thing done here, not indefinitely
  deferred.
- Reviews only `.py` files in a PR; other languages are ignored.
- Relies on Gemini's output being sensible Markdown — there is no
  structured/JSON output or automated validation of review quality yet.
- No persistence or history: each run is independent, and repeated runs
  on the same PR will post duplicate comments rather than updating one.
- No caching, so re-running on an unchanged PR re-spends API quota.

These are reasonable next steps if this tool keeps getting used, not
implemented here.

## License

Apache 2.0 — see [LICENSE](LICENSE).
