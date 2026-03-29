"""
Tests for Teams, Email, and dispatcher notifications.

ALL tests are fast — external services are mocked.
Run: pytest tests/test_notifications.py -v
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch, MagicMock
from models.finding import Finding, FindingType, Severity
from models.review import Review


def _make_review(p0=1, p1=1, p2=1) -> Review:
    """Helper: create a review with specified severity counts."""
    findings = []
    for i in range(p0):
        findings.append(Finding(
            type=FindingType.SECURITY, severity=Severity.P0,
            title=f"SQL Injection {i}", line_range=f"{10+i}",
            explanation="User input in query.", flagged_code="bad",
            fixed_code="good",
        ))
    for i in range(p1):
        findings.append(Finding(
            type=FindingType.ARCHITECTURE, severity=Severity.P1,
            title=f"SOLID violation {i}", line_range=f"{30+i}",
            explanation="Violates SRP.", flagged_code="coupled",
            fixed_code="decoupled",
        ))
    for i in range(p2):
        findings.append(Finding(
            type=FindingType.SMELL, severity=Severity.P2,
            title=f"Magic number {i}", line_range=f"{50+i}",
            explanation="Use a constant.", flagged_code="0.15",
            fixed_code="DISCOUNT = 0.15",
        ))
    return Review(
        repo="test/repo",
        findings=findings,
        agents_completed=["security", "architecture", "smell"],
        review_duration_seconds=20.0,
    )


# ─── Teams notifications ─────────────────────────────────────


class TestTeamsNotification:

    def test_builds_adaptive_card(self):
        from notifications.teams import _build_card
        review = _make_review()
        card = _build_card(review, pr_url="https://github.com/test/repo/pull/1")

        content = card["attachments"][0]["content"]
        assert content["type"] == "AdaptiveCard"
        assert len(content["body"]) > 3
        assert content["actions"][0]["url"] == "https://github.com/test/repo/pull/1"

    def test_card_has_summary(self):
        from notifications.teams import _build_card
        review = _make_review(p0=2, p1=3, p2=0)
        card = _build_card(review)
        body_texts = [b.get("text", "") for b in card["attachments"][0]["content"]["body"]]
        summary = body_texts[1]
        assert "2 blocking" in summary
        assert "3 important" in summary

    def test_card_shows_warning_for_p0(self):
        from notifications.teams import _build_card
        review = _make_review(p0=1)
        card = _build_card(review)
        body_texts = [b.get("text", "") for b in card["attachments"][0]["content"]["body"]]
        assert any("Blocking" in t for t in body_texts)

    def test_card_no_warning_without_p0(self):
        from notifications.teams import _build_card
        review = _make_review(p0=0, p1=2, p2=1)
        card = _build_card(review)
        body_texts = [b.get("text", "") for b in card["attachments"][0]["content"]["body"]]
        assert not any("Blocking" in t for t in body_texts)

    def test_send_skips_if_not_configured(self):
        from notifications.teams import send_teams_notification
        review = _make_review()
        mock_settings = MagicMock()
        mock_settings.teams_webhook_url = ""
        with patch("notifications.teams.settings", mock_settings):
            result = send_teams_notification(review)
        assert result is False

    def test_send_succeeds_with_200(self):
        from notifications.teams import send_teams_notification
        review = _make_review()
        mock_settings = MagicMock()
        mock_settings.teams_webhook_url = "https://fake.webhook.url"

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("notifications.teams.settings", mock_settings), \
             patch("notifications.teams.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = lambda s: s
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.post.return_value = mock_response
            result = send_teams_notification(review)
        assert result is True

    def test_send_handles_error_gracefully(self):
        from notifications.teams import send_teams_notification
        review = _make_review()
        mock_settings = MagicMock()
        mock_settings.teams_webhook_url = "https://fake.webhook.url"

        with patch("notifications.teams.settings", mock_settings), \
             patch("notifications.teams.httpx.Client", side_effect=Exception("network")):
            result = send_teams_notification(review)
        assert result is False


# ─── Email notifications ──────────────────────────────────────


class TestEmailNotification:

    def test_html_includes_p0_findings(self):
        from notifications.email_notify import _build_html
        review = _make_review(p0=2, p1=1, p2=3)
        html = _build_html(review)
        assert "SQL Injection 0" in html
        assert "SQL Injection 1" in html
        assert "SOLID violation" in html
        # P2 nits should NOT be in email
        assert "Magic number" not in html

    def test_html_has_blocking_banner(self):
        from notifications.email_notify import _build_html
        review = _make_review(p0=1)
        html = _build_html(review)
        assert "Blocking issues" in html

    def test_html_has_pr_link(self):
        from notifications.email_notify import _build_html
        review = _make_review()
        html = _build_html(review, pr_url="https://github.com/test/pull/1")
        assert "https://github.com/test/pull/1" in html

    def test_skips_if_no_api_key(self):
        from notifications.email_notify import send_email_notification
        review = _make_review()
        mock_settings = MagicMock()
        mock_settings.resend_api_key = ""
        with patch("notifications.email_notify.settings", mock_settings):
            result = send_email_notification(review)
        assert result is False

    def test_skips_if_only_nits(self):
        from notifications.email_notify import send_email_notification
        review = _make_review(p0=0, p1=0, p2=5)
        mock_settings = MagicMock()
        mock_settings.resend_api_key = "re_test"
        with patch("notifications.email_notify.settings", mock_settings):
            result = send_email_notification(review)
        assert result is False

    def test_sends_for_p0_findings(self):
        from notifications.email_notify import send_email_notification
        review = _make_review(p0=1, p1=0, p2=0)
        mock_settings = MagicMock()
        mock_settings.resend_api_key = "re_test"
        mock_settings.notification_email_from = "test@screvyn.dev"

        with patch("notifications.email_notify.settings", mock_settings), \
             patch("notifications.email_notify.resend") as mock_resend:
            mock_resend.Emails.send.return_value = {"id": "email-123"}
            result = send_email_notification(review, recipients=["dev@test.com"])
        assert result is True
        mock_resend.Emails.send.assert_called_once()


# ─── Dispatcher ───────────────────────────────────────────────


class TestDispatcher:

    # def test_dispatches_to_all_channels(self):
    #     from notifications.dispatcher import dispatch_notifications
    #     review = _make_review()

    #     with patch("notifications.dispatcher.send_teams_notification", return_value=True) as mock_teams, \
    #          patch("notifications.dispatcher.send_email_notification", return_value=True) as mock_email, \
    #          patch("notifications.dispatcher.save_review", return_value="doc-123") as mock_fire:
    #         # Need to patch the imports inside dispatcher
    #         pass

    #     # Use the lazy import approach — mock at module level
    #     with patch("notifications.teams.send_teams_notification", return_value=True), \
    #          patch("notifications.email_notify.send_email_notification", return_value=True), \
    #          patch("core.firebase_client.save_review", return_value="doc-123"):
    #         results = dispatch_notifications(review, pr_number=1)

    #     assert "teams" in results
    #     assert "email" in results
    #     assert "firestore" in results
    def test_dispatches_to_all_channels(self):
        from notifications.dispatcher import dispatch_notifications
        review = _make_review()

        with patch("notifications.teams.send_teams_notification", return_value=True), \
             patch("notifications.email_notify.send_email_notification", return_value=True), \
             patch("core.firebase_client.save_review", return_value="doc-123"):
            results = dispatch_notifications(review, pr_number=1)

        assert "teams" in results
        assert "email" in results
        assert "firestore" in results

    def test_one_failure_doesnt_block_others(self):
        from notifications.dispatcher import dispatch_notifications
        review = _make_review()

        with patch("notifications.teams.send_teams_notification", side_effect=Exception("boom")), \
             patch("notifications.email_notify.send_email_notification", return_value=True), \
             patch("core.firebase_client.save_review", return_value="doc-456"):
            results = dispatch_notifications(review, pr_number=1)

        # Teams failed but email and firestore should still work
        assert results["teams"] is False
        assert "email" in results
        assert "firestore" in results

    def test_clean_review_skips_email(self):
        from notifications.dispatcher import dispatch_notifications
        review = _make_review(p0=0, p1=0, p2=3)

        with patch("notifications.teams.send_teams_notification", return_value=True), \
             patch("notifications.email_notify.send_email_notification", return_value=False), \
             patch("core.firebase_client.save_review", return_value="doc-789"):
            results = dispatch_notifications(review, pr_number=1)

        # Email should be False (skipped — no P0/P1)
        assert results["email"] is False
