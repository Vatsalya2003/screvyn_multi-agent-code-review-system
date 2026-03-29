"""
GitHub API client — authenticates as a GitHub App and interacts with PRs.

Auth flow (this is how ALL GitHub Apps work):
    1. Read your private key (.pem file downloaded when you created the app)
    2. Sign a JWT with that key (RS256, expires in 10 min)
    3. Exchange the JWT for an installation access token (expires in 1 hour)
    4. Use that token for all API calls (fetch files, post comments)

Why a GitHub App instead of a personal access token?
    - Apps have their own identity (comments show as "screvyn-bot")
    - Apps can be installed on any org (not tied to your account)
    - Installation tokens are short-lived (1 hour vs PATs that last forever)
    - Required for any real product
"""

import logging
import time
from pathlib import Path

import httpx
import jwt

from core.config import settings

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"

# Cache the installation token so we don't re-create it on every call
_cached_token: str | None = None
_token_expires_at: float = 0


def _read_private_key() -> str:
    """Read the GitHub App private key from the .pem file."""
    key_path = Path(settings.github_private_key_path)
    if not key_path.exists():
        raise FileNotFoundError(
            f"GitHub private key not found at {key_path}. "
            f"Download it from your GitHub App settings."
        )
    return key_path.read_text()


def _create_jwt() -> str:
    """
    Create a JWT signed with the GitHub App's private key.

    This JWT is NOT used for API calls directly — it's exchanged
    for an installation token in the next step. Think of it as
    "proving you own the app."
    """
    now = int(time.time())
    payload = {
        "iat": now - 60,           # issued at (60s in the past for clock skew)
        "exp": now + (10 * 60),    # expires in 10 minutes (GitHub maximum)
        "iss": settings.github_app_id,
    }
    private_key = _read_private_key()
    return jwt.encode(payload, private_key, algorithm="RS256")


def _get_installation_token() -> str:
    """
    Exchange the JWT for an installation access token.

    This is the token you use for actual API calls.
    It's scoped to the specific installation (your repo)
    and expires in 1 hour.
    """
    global _cached_token, _token_expires_at

    # Reuse cached token if it's still valid (with 5 min buffer)
    if _cached_token and time.time() < _token_expires_at - 300:
        return _cached_token

    app_jwt = _create_jwt()

    with httpx.Client(timeout=10) as client:
        resp = client.post(
            f"{GITHUB_API}/app/installations/{settings.github_installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        resp.raise_for_status()

    data = resp.json()
    _cached_token = data["token"]
    # GitHub tokens expire in 1 hour; we'll refresh 5 min early
    _token_expires_at = time.time() + 3600

    logger.info("Obtained new GitHub installation token")
    return _cached_token


def _headers() -> dict:
    """Standard headers for GitHub API calls."""
    token = _get_installation_token()
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get_pr_files(owner: str, repo: str, pr_number: int) -> list[dict]:
    """
    Fetch the list of files changed in a PR.

    Returns a list of dicts, each with:
        - filename: "src/auth.py"
        - status: "modified" | "added" | "removed"
        - patch: the unified diff (if available)
        - contents_url: API URL to fetch the full file

    GitHub paginates at 30 files — we follow pagination up to 300.
    """
    files = []
    page = 1

    with httpx.Client(timeout=15) as client:
        while page <= 10:  # safety cap: 10 pages = 300 files
            resp = client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/files",
                headers=_headers(),
                params={"per_page": 30, "page": page},
            )
            resp.raise_for_status()
            batch = resp.json()

            if not batch:
                break

            files.extend(batch)
            page += 1

            if len(batch) < 30:
                break

    logger.info("Fetched %d files from %s/%s#%d", len(files), owner, repo, pr_number)
    return files


def get_file_content(owner: str, repo: str, path: str, ref: str) -> str:
    """
    Fetch the full content of a file at a specific git ref (commit SHA or branch).

    Used to get the complete file for AST parsing — the PR diff alone
    isn't enough for tree-sitter, which needs the full source.
    """
    with httpx.Client(timeout=15) as client:
        resp = client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
            headers=_headers(),
            params={"ref": ref},
        )
        resp.raise_for_status()

    data = resp.json()

    # GitHub returns base64-encoded content for files under 1MB
    if data.get("encoding") == "base64":
        import base64
        return base64.b64decode(data["content"]).decode("utf-8")

    # For larger files, fetch the raw URL
    if data.get("download_url"):
        with httpx.Client(timeout=15) as client:
            resp = client.get(data["download_url"])
            resp.raise_for_status()
            return resp.text

    return ""


def post_pr_comment(owner: str, repo: str, pr_number: int, body: str) -> dict:
    """
    Post a comment on a pull request.

    This shows up as a comment from your GitHub App bot account,
    not from your personal account.
    """
    with httpx.Client(timeout=15) as client:
        resp = client.post(
            f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments",
            headers=_headers(),
            json={"body": body},
        )
        resp.raise_for_status()

    result = resp.json()
    logger.info(
        "Posted review comment on %s/%s#%d (comment id: %s)",
        owner, repo, pr_number, result.get("id"),
    )
    return result


def get_pr_details(owner: str, repo: str, pr_number: int) -> dict:
    """
    Fetch PR metadata — head SHA, base branch, title, author.

    Used by the Celery task to know which commit to fetch files from.
    """
    with httpx.Client(timeout=15) as client:
        resp = client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}",
            headers=_headers(),
        )
        resp.raise_for_status()

    data = resp.json()
    return {
        "head_sha": data["head"]["sha"],
        "base_branch": data["base"]["ref"],
        "title": data["title"],
        "author": data["user"]["login"],
        "head_ref": data["head"]["ref"],
    }


# ─── Language detection from file extension ───────────────────


EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "javascript",
    ".tsx": "javascript",
    ".java": "java",
}


def detect_language(filename: str) -> str | None:
    """Map a filename to its tree-sitter language, or None if unsupported."""
    for ext, lang in EXTENSION_TO_LANGUAGE.items():
        if filename.endswith(ext):
            return lang
    return None
