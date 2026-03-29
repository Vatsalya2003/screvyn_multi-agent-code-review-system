"""
GitHub webhook receiver — handles push and pull_request events.

Security:
    Every webhook from GitHub includes an X-Hub-Signature-256 header.
    That's an HMAC-SHA256 hash of the payload using your webhook secret.
    We recompute the hash and compare — if they don't match, someone
    is sending fake webhooks and we reject with 403.

Flow:
    GitHub POST → verify signature → check rate limit → enqueue Celery task → 202

Why 202 not 200?
    202 means "accepted for processing." The review takes ~30s but
    GitHub expects a response within 10s. We respond instantly and
    process in the background via Celery.
"""

import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from typing import Optional

from core.config import settings
from core.rate_limiter import check_rate_limit, increment_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()

# PR actions we care about — ignore the rest
REVIEWABLE_ACTIONS = {"opened", "synchronize", "reopened"}


def _verify_signature(payload: bytes, signature: str) -> bool:
    """
    Verify the GitHub webhook HMAC-SHA256 signature.

    GitHub sends: X-Hub-Signature-256: sha256=abc123...
    We compute:   HMAC-SHA256(secret, payload) and compare.

    Uses hmac.compare_digest to prevent timing attacks.
    """
    if not settings.github_webhook_secret:
        logger.warning("GITHUB_WEBHOOK_SECRET not set — skipping verification")
        return True

    if not signature or not signature.startswith("sha256="):
        return False

    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


@router.post("/api/webhook")
async def github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
):
    """
    Receive GitHub webhook events.

    Handles:
      - pull_request (opened, synchronize, reopened) → run review
      - ping → respond OK (GitHub sends this when you set up the webhook)
    """
    # Read raw body for signature verification
    body = await request.body()

    # Step 1: Verify the signature
    if not _verify_signature(body, x_hub_signature_256 or ""):
        logger.warning("Invalid webhook signature — rejecting")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Step 2: Handle ping events (GitHub sends on webhook setup)
    if x_github_event == "ping":
        logger.info("Received ping event from GitHub")
        return {"status": "pong"}

    # Step 3: Only process pull_request events
    if x_github_event != "pull_request":
        logger.info("Ignoring event type: %s", x_github_event)
        return {"status": "ignored", "reason": f"event type '{x_github_event}' not handled"}

    # Step 4: Parse the payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    action = payload.get("action", "")
    if action not in REVIEWABLE_ACTIONS:
        logger.info("Ignoring PR action: %s", action)
        return {"status": "ignored", "reason": f"action '{action}' not reviewable"}

    # Extract PR info
    pr = payload.get("pull_request", {})
    pr_number = pr.get("number")
    repo_full = payload.get("repository", {}).get("full_name", "")
    installation_id = str(payload.get("installation", {}).get("id", ""))

    if not pr_number or not repo_full:
        raise HTTPException(status_code=400, detail="Missing PR number or repo")

    owner, repo = repo_full.split("/", 1)

    logger.info(
        "Received PR event: %s#%d (action: %s)",
        repo_full, pr_number, action,
    )

    # Step 5: Check rate limit
    allowed, count, limit = check_rate_limit(repo_full)
    if not allowed:
        logger.warning("Rate limited: %s at %d/%d", repo_full, count, limit)
        raise HTTPException(
            status_code=429,
            detail=f"Monthly review limit reached ({count}/{limit}). "
                   f"Upgrade to Pro for unlimited reviews.",
        )

    # Step 6: Enqueue the review task
    import celery_app  # noqa: F401 — ensures Celery uses Redis, not default AMQP
    from tasks.review_task import review_pr

    task = review_pr.delay(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        installation_id=installation_id,
    )

    # Step 7: Increment rate limit AFTER successful enqueue
    increment_rate_limit(repo_full)

    logger.info(
        "Enqueued review task %s for %s#%d",
        task.id, repo_full, pr_number,
    )

    # Return 202 immediately — review happens in background
    # return {
    #     "status": "accepted",
    #     "task_id": task.id,
    #     "repo": repo_full,
    #     "pr_number": pr_number,
    # }
    # Return 202 immediately — review happens in background
    return JSONResponse(
        status_code=202,
        content={
            "status": "accepted",
            "task_id": task.id,
            "repo": repo_full,
            "pr_number": pr_number,
        },
    )
