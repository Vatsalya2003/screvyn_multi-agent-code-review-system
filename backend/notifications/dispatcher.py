"""
Notification dispatcher — sends review results to all configured channels.

Each channel is independent — if Teams fails, email still sends.
All channels fire sequentially (fast enough for 2-3 channels).
Add new channels by adding a function here — no other files change.

Channel list:
  - Teams (Adaptive Card via webhook)
  - Email (HTML via Resend, P0/P1 only)
  - Firestore (save for dashboard)
  - Slack (ready to add later)
"""

import logging

from models.review import Review
from core.firebase_client import save_review

logger = logging.getLogger(__name__)


def dispatch_notifications(
    review: Review,
    pr_number: int = 0,
    pr_title: str = "",
    pr_author: str = "",
    pr_url: str = "",
    email_recipients: list[str] | None = None,
) -> dict:
    """
    Send review results to all configured notification channels.

    Returns a dict showing which channels succeeded/failed:
        {
            "teams": True,
            "email": True,
            "firestore": "doc_id_123",
        }

    Never raises — every channel is wrapped in its own try/except.
    """
    results = {}

    # ── Teams ─────────────────────────────────────────────
    try:
        from notifications.teams import send_teams_notification
        results["teams"] = send_teams_notification(review, pr_url=pr_url)
    except Exception as e:
        logger.error("Teams dispatch failed: %s", e)
        results["teams"] = False

    # ── Email (P0/P1 only) ────────────────────────────────
    try:
        from notifications.email_notify import send_email_notification
        results["email"] = send_email_notification(
            review,
            pr_url=pr_url,
            recipients=email_recipients,
        )
    except Exception as e:
        logger.error("Email dispatch failed: %s", e)
        results["email"] = False

    # ── Firestore (save for dashboard) ────────────────────
    try:
        doc_id = save_review(
            review,
            pr_number=pr_number,
            pr_title=pr_title,
            pr_author=pr_author,
            pr_url=pr_url,
        )
        results["firestore"] = doc_id or False
    except Exception as e:
        logger.error("Firestore dispatch failed: %s", e)
        results["firestore"] = False

    # ── Slack (placeholder — add later) ───────────────────
    # try:
    #     from notifications.slack import send_slack_notification
    #     results["slack"] = send_slack_notification(review, pr_url=pr_url)
    # except Exception as e:
    #     logger.error("Slack dispatch failed: %s", e)
    #     results["slack"] = False

    # Summary log
    succeeded = [k for k, v in results.items() if v]
    failed = [k for k, v in results.items() if not v]
    logger.info(
        "Notifications for %s: sent=%s, skipped/failed=%s",
        review.repo, succeeded or "none", failed or "none",
    )

    return results
