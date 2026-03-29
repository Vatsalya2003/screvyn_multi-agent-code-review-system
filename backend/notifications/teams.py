"""
Microsoft Teams notifications — sends Adaptive Cards via incoming webhook.

Adaptive Cards are Teams' structured message format. They support:
  - Text blocks with weight/size/color
  - Fact sets (key-value pairs)
  - Action buttons (link to PR)
  - Container layouts

The card shows: summary counts, top 3 findings, and a "View PR" button.
"""

import logging

import httpx

from core.config import settings
from models.review import Review
from core.review_style import SEVERITY_PREFIX, CATEGORY_LABEL

logger = logging.getLogger(__name__)


def _severity_color(severity: str) -> str:
    """Map severity to Adaptive Card color."""
    return {
        "P0": "attention",   # red
        "P1": "warning",     # yellow
        "P2": "default",     # gray
    }.get(severity, "default")


def _build_card(review: Review, pr_url: str = "") -> dict:
    """
    Build a Teams Adaptive Card for a code review.

    Structure:
      - Header: repo name + summary counts
      - Top 3 findings with severity + title + explanation
      - "View PR" button
    """
    # Summary text
    parts = []
    if review.p0_count > 0:
        parts.append(f"**{review.p0_count} blocking**")
    if review.p1_count > 0:
        parts.append(f"{review.p1_count} important")
    if review.p2_count > 0:
        parts.append(f"{review.p2_count} nit{'s' if review.p2_count > 1 else ''}")
    summary = ", ".join(parts) if parts else "No issues"

    # Card body
    body = [
        {
            "type": "TextBlock",
            "text": f"Screvyn Review: {review.repo}",
            "weight": "bolder",
            "size": "medium",
        },
        {
            "type": "TextBlock",
            "text": summary,
            "wrap": True,
        },
    ]

    # Warning banner for P0s
    if review.has_critical:
        body.append({
            "type": "TextBlock",
            "text": "⚠ Blocking issues must be fixed before merge.",
            "weight": "bolder",
            "color": "attention",
        })

    # Top 3 findings
    top = review.findings[:3]
    if top:
        body.append({"type": "TextBlock", "text": "---"})

    for f in top:
        prefix = SEVERITY_PREFIX.get(f.severity.value, "note")
        category = CATEGORY_LABEL.get(f.type.value, f.type.value)
        loc = f"line {f.line_range}" if f.line_range else ""

        body.append({
            "type": "TextBlock",
            "text": f"**{prefix}** | {category}: {f.title} ({loc})",
            "wrap": True,
            "weight": "bolder",
            "color": _severity_color(f.severity.value),
        })

        explanation = f.explanation.strip()
        if len(explanation) > 150:
            explanation = explanation[:150].rstrip() + "..."
        body.append({
            "type": "TextBlock",
            "text": explanation,
            "wrap": True,
            "isSubtle": True,
        })

    remaining = len(review.findings) - 3
    if remaining > 0:
        body.append({
            "type": "TextBlock",
            "text": f"+{remaining} more findings on the PR.",
            "isSubtle": True,
        })

    # Footer
    body.append({
        "type": "TextBlock",
        "text": f"Reviewed in {review.review_duration_seconds:.0f}s by Screvyn",
        "isSubtle": True,
        "size": "small",
    })

    # Build the card
    card = {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "type": "AdaptiveCard",
                "version": "1.2",
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "body": body,
            },
        }],
    }

    # Add "View PR" button if URL provided
    if pr_url:
        card["attachments"][0]["content"]["actions"] = [{
            "type": "Action.OpenUrl",
            "title": "View PR",
            "url": pr_url,
        }]

    return card


def send_teams_notification(review: Review, pr_url: str = "") -> bool:
    """
    Send a review notification to Microsoft Teams.

    Returns True if sent successfully, False otherwise.
    Never raises — failures are logged and swallowed.
    """
    if not settings.teams_webhook_url:
        logger.debug("Teams webhook URL not configured — skipping")
        return False

    try:
        card = _build_card(review, pr_url)

        with httpx.Client(timeout=10) as client:
            resp = client.post(settings.teams_webhook_url, json=card)

        if resp.status_code == 200:
            logger.info("Teams notification sent for %s", review.repo)
            return True
        else:
            logger.warning(
                "Teams notification failed: %d %s",
                resp.status_code, resp.text[:200],
            )
            return False

    except Exception as e:
        logger.error("Teams notification error: %s", e)
        return False
