"""
Tests for the GitHub webhook receiver.

ALL tests are fast — no API calls, no Redis. We mock everything external.
Run: pytest tests/test_webhook.py -v
"""

import hashlib
import hmac
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

TEST_SECRET = "test-secret-12345"


def _sign(payload: bytes, secret: str = TEST_SECRET) -> str:
    """Compute HMAC-SHA256 signature like GitHub does."""
    return "sha256=" + hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


def _pr_payload(
    action: str = "opened",
    pr_number: int = 42,
    repo: str = "testuser/testrepo",
    installation_id: int = 99999,
) -> bytes:
    """Build a realistic GitHub PR webhook payload."""
    return json.dumps({
        "action": action,
        "pull_request": {
            "number": pr_number,
            "title": "Add user auth",
            "head": {"sha": "abc123", "ref": "feature-branch"},
            "base": {"ref": "main"},
            "user": {"login": "testuser"},
        },
        "repository": {
            "full_name": repo,
            "name": repo.split("/")[-1],
        },
        "installation": {"id": installation_id},
    }).encode("utf-8")


def _mock_settings(webhook_secret: str = TEST_SECRET):
    """Create a mock settings object with the test webhook secret."""
    mock = MagicMock()
    mock.github_webhook_secret = webhook_secret
    return mock


# ─── Signature verification ──────────────────────────────────


class TestSignatureVerification:

    def test_valid_signature_accepted(self):
        """A correctly signed payload should not return 403."""
        payload = _pr_payload()
        sig = _sign(payload)
        with patch("routers.webhook.settings", _mock_settings()), \
             patch("routers.webhook.check_rate_limit", return_value=(True, 5, 50)), \
             patch("routers.webhook.increment_rate_limit", return_value=6), \
             patch("tasks.review_task.review_pr.delay") as mock_task:
            mock_task.return_value = MagicMock(id="task-123")
            resp = client.post(
                "/api/webhook",
                content=payload,
                headers={
                    "X-Hub-Signature-256": sig,
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json",
                },
            )
        assert resp.status_code == 202

    def test_invalid_signature_rejected(self):
        """A wrong signature should return 403."""
        payload = _pr_payload()
        with patch("routers.webhook.settings", _mock_settings()):
            resp = client.post(
                "/api/webhook",
                content=payload,
                headers={
                    "X-Hub-Signature-256": "sha256=wrong",
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json",
                },
            )
        assert resp.status_code == 403

    def test_missing_signature_rejected(self):
        """No signature header should return 403."""
        payload = _pr_payload()
        with patch("routers.webhook.settings", _mock_settings()):
            resp = client.post(
                "/api/webhook",
                content=payload,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json",
                },
            )
        assert resp.status_code == 403

    def test_empty_secret_skips_verification(self):
        """If webhook secret is not configured, skip verification (dev mode)."""
        payload = _pr_payload()
        with patch("routers.webhook.settings", _mock_settings(webhook_secret="")), \
             patch("routers.webhook.check_rate_limit", return_value=(True, 5, 50)), \
             patch("routers.webhook.increment_rate_limit", return_value=6), \
             patch("tasks.review_task.review_pr.delay") as mock_task:
            mock_task.return_value = MagicMock(id="task-123")
            resp = client.post(
                "/api/webhook",
                content=payload,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json",
                },
            )
        # Should succeed because verification is skipped
        assert resp.status_code == 202


# ─── Event handling ──────────────────────────────────────────


class TestEventHandling:

    def _post_signed(self, payload: bytes, event: str = "pull_request"):
        """Helper: send a properly signed webhook with all mocks."""
        sig = _sign(payload)
        with patch("routers.webhook.settings", _mock_settings()), \
             patch("routers.webhook.check_rate_limit", return_value=(True, 5, 50)), \
             patch("routers.webhook.increment_rate_limit", return_value=6), \
             patch("tasks.review_task.review_pr.delay") as mock_task:
            mock_task.return_value = MagicMock(id="task-123")
            resp = client.post(
                "/api/webhook",
                content=payload,
                headers={
                    "X-Hub-Signature-256": sig,
                    "X-GitHub-Event": event,
                    "Content-Type": "application/json",
                },
            )
        return resp

    def test_ping_event_returns_pong(self):
        """GitHub sends a ping when you first set up the webhook."""
        payload = json.dumps({"zen": "test"}).encode()
        sig = _sign(payload)
        with patch("routers.webhook.settings", _mock_settings()):
            resp = client.post(
                "/api/webhook",
                content=payload,
                headers={
                    "X-Hub-Signature-256": sig,
                    "X-GitHub-Event": "ping",
                    "Content-Type": "application/json",
                },
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "pong"

    def test_pr_opened_returns_202(self):
        """Opening a PR should enqueue a review and return 202."""
        resp = self._post_signed(_pr_payload(action="opened"))
        assert resp.status_code == 202
        assert resp.json()["status"] == "accepted"
        assert resp.json()["task_id"] == "task-123"

    def test_pr_synchronize_returns_202(self):
        """Pushing to a PR branch triggers 'synchronize' — should review."""
        resp = self._post_signed(_pr_payload(action="synchronize"))
        assert resp.status_code == 202

    def test_pr_reopened_returns_202(self):
        """Reopening a PR should trigger a review."""
        resp = self._post_signed(_pr_payload(action="reopened"))
        assert resp.status_code == 202

    def test_pr_closed_is_ignored(self):
        """Closing a PR should NOT trigger a review."""
        resp = self._post_signed(_pr_payload(action="closed"))
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_pr_labeled_is_ignored(self):
        """Adding a label should NOT trigger a review."""
        resp = self._post_signed(_pr_payload(action="labeled"))
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_push_event_is_ignored(self):
        """Push events (not PRs) should be ignored."""
        payload = json.dumps({"ref": "refs/heads/main"}).encode()
        sig = _sign(payload)
        with patch("routers.webhook.settings", _mock_settings()):
            resp = client.post(
                "/api/webhook",
                content=payload,
                headers={
                    "X-Hub-Signature-256": sig,
                    "X-GitHub-Event": "push",
                    "Content-Type": "application/json",
                },
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_response_includes_task_id(self):
        """The 202 response should include the Celery task ID."""
        resp = self._post_signed(_pr_payload())
        body = resp.json()
        assert "task_id" in body
        assert body["repo"] == "testuser/testrepo"
        assert body["pr_number"] == 42


# ─── Rate limiting ───────────────────────────────────────────


class TestWebhookRateLimiting:

    def test_rate_limited_returns_429(self):
        """When rate limit is exceeded, return 429."""
        payload = _pr_payload()
        sig = _sign(payload)
        with patch("routers.webhook.settings", _mock_settings()), \
             patch("routers.webhook.check_rate_limit", return_value=(False, 50, 50)):
            resp = client.post(
                "/api/webhook",
                content=payload,
                headers={
                    "X-Hub-Signature-256": sig,
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json",
                },
            )
        assert resp.status_code == 429
        assert "limit" in resp.json()["detail"].lower()

    def test_under_limit_passes(self):
        """When under rate limit, the request should go through."""
        resp_data = self._post_with_rate_limit(allowed=True, count=10)
        assert resp_data.status_code == 202

    def _post_with_rate_limit(self, allowed: bool, count: int):
        payload = _pr_payload()
        sig = _sign(payload)
        with patch("routers.webhook.settings", _mock_settings()), \
             patch("routers.webhook.check_rate_limit", return_value=(allowed, count, 50)), \
             patch("routers.webhook.increment_rate_limit", return_value=count + 1), \
             patch("tasks.review_task.review_pr.delay") as mock_task:
            mock_task.return_value = MagicMock(id="task-123")
            return client.post(
                "/api/webhook",
                content=payload,
                headers={
                    "X-Hub-Signature-256": sig,
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json",
                },
            )
