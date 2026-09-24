"""AI-powered GitHub pull request code reviewer.

Fetches the diff of a pull request, sends the changed Python files to a
Gemini model for review, and posts the result back as a PR comment.
"""

__version__ = "0.1.0"
