"""
Email notifications via Resend — sends HTML emails for P0/P1 findings.

Only sends for reviews that have blocking or important findings.
Nobody wants an email for nits.

Resend free tier: 3,000 emails/month — more than enough for a student MVP.
"""

import logging

import resend

from core.config import settings
from models.review import Review
from core.review_style import SEVERITY_PREFIX, CATEGORY_LABEL

logger = logging.getLogger(__name__)

# Default recipient — in production this would come from user settings
DEFAULT_RECIPIENT = "reviews@screvyn.dev"


def _build_html(review: Review, pr_url: str = "") -> str:
    """
    Build a clean HTML email with P0 + P1 findings.

    Style: minimal, no images, fast to scan on mobile.
    Only includes blocking + important findings — nits go to PR only.
    """
    # Summary
    parts = []
    if review.p0_count > 0:
        parts.append(f"<strong>{review.p0_count} blocking</strong>")
    if review.p1_count > 0:
        parts.append(f"{review.p1_count} important")
    if review.p2_count > 0:
        parts.append(f"{review.p2_count} nits")
    summary = ", ".join(parts)

    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="margin-bottom: 4px;">Screvyn Review</h2>
        <p style="color: #666; margin-top: 0;">{review.repo}</p>

        <p>Found {summary}.</p>
    """

    if review.has_critical:
        html += """
        <div style="background: #fee; border-left: 4px solid #c00; padding: 10px 14px; margin: 16px 0;">
            <strong>Blocking issues must be fixed before merge.</strong>
        </div>
        """

    # Only P0 + P1 findings in email
    critical_findings = [
        f for f in review.findings
        if f.severity.value in ("P0", "P1")
    ]

    for f in critical_findings:
        prefix = SEVERITY_PREFIX.get(f.severity.value, "note")
        category = CATEGORY_LABEL.get(f.type.value, f.type.value)
        loc = f"line {f.line_range}" if f.line_range else ""

        color = "#c00" if f.severity.value == "P0" else "#e90"

        explanation = f.explanation.strip()
        if len(explanation) > 200:
            explanation = explanation[:200].rstrip() + "..."

        html += f"""
        <div style="border-left: 3px solid {color}; padding: 8px 14px; margin: 12px 0;">
            <strong>{prefix} | {category}: {f.title}</strong>
            <span style="color: #888;">({loc})</span>
            <p style="margin: 6px 0; color: #333;">{explanation}</p>
        """

        if f.flagged_code and f.flagged_code != "N/A":
            code = f.flagged_code.strip().replace("<", "&lt;").replace(">", "&gt;")
            html += f"""
            <pre style="background: #f5f5f5; padding: 8px; border-radius: 4px; font-size: 13px; overflow-x: auto;">{code}</pre>
            """

        html += "</div>"

    # Footer
    pr_link = f'<a href="{pr_url}" style="color: #0366d6;">View PR on GitHub</a>' if pr_url else ""

    html += f"""
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #888; font-size: 12px;">
            Reviewed by {', '.join(review.agents_completed)} agents in {review.review_duration_seconds:.0f}s
            {' · ' + pr_link if pr_link else ''}
            · Screvyn Code Review
        </p>
    </div>
    """

    return html


def send_email_notification(
    review: Review,
    pr_url: str = "",
    recipients: list[str] | None = None,
) -> bool:
    """
    Send an email notification for reviews with P0 or P1 findings.

    Returns True if sent successfully, False otherwise.
    Skips sending if no P0/P1 findings — nits don't deserve an email.
    Never raises — failures are logged and swallowed.
    """
    if not settings.resend_api_key:
        logger.debug("Resend API key not configured — skipping email")
        return False

    # Only send emails for blocking/important issues
    if review.p0_count == 0 and review.p1_count == 0:
        logger.debug("No P0/P1 findings — skipping email for %s", review.repo)
        return False

    to_addrs = recipients or [DEFAULT_RECIPIENT]

    try:
        resend.api_key = settings.resend_api_key

        severity_tag = "BLOCKING" if review.p0_count > 0 else "Important"
        subject = f"[{severity_tag}] Screvyn Review: {review.repo}"

        html = _build_html(review, pr_url)

        result = resend.Emails.send({
            "from": settings.notification_email_from,
            "to": to_addrs,
            "subject": subject,
            "html": html,
        })

        logger.info("Email sent for %s: %s", review.repo, result.get("id", "ok"))
        return True

    except Exception as e:
        logger.error("Email notification error: %s", e)
        return False
