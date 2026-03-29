"""
Tests for the Redis-based rate limiter.

Uses a mock Redis client — no real Redis needed.
Run: pytest tests/test_rate_limiter.py -v
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch, MagicMock


# ─── Mock Redis for all tests ────────────────────────────────


class FakeRedis:
    """In-memory Redis mock for testing."""

    def __init__(self):
        self._store: dict[str, str] = {}
        self._expiry: dict[str, int] = {}

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(self, key: str, value: str) -> None:
        self._store[key] = str(value)

    def incr(self, key: str) -> int:
        current = int(self._store.get(key, 0))
        new_val = current + 1
        self._store[key] = str(new_val)
        return new_val

    def expire(self, key: str, seconds: int) -> None:
        self._expiry[key] = seconds

    def delete(self, key: str) -> None:
        self._store.pop(key, None)
        self._expiry.pop(key, None)


@pytest.fixture(autouse=True)
def mock_redis():
    """Replace the real Redis connection with FakeRedis for every test."""
    fake = FakeRedis()
    with patch("core.rate_limiter._get_redis", return_value=fake):
        # Also reset the cached client
        import core.rate_limiter as rl
        rl._redis_client = None
        yield fake


# ─── check_rate_limit ─────────────────────────────────────────


class TestCheckRateLimit:

    def test_first_request_is_allowed(self, mock_redis):
        from core.rate_limiter import check_rate_limit
        allowed, count, limit = check_rate_limit("owner/repo")
        assert allowed is True
        assert count == 0
        assert limit == 50

    def test_under_limit_is_allowed(self, mock_redis):
        from core.rate_limiter import check_rate_limit, _make_key
        # Simulate 49 previous reviews
        key = _make_key("owner/repo")
        mock_redis.set(key, "49")
        allowed, count, limit = check_rate_limit("owner/repo")
        assert allowed is True
        assert count == 49

    def test_at_limit_is_blocked(self, mock_redis):
        from core.rate_limiter import check_rate_limit, _make_key
        key = _make_key("owner/repo")
        mock_redis.set(key, "50")
        allowed, count, limit = check_rate_limit("owner/repo")
        assert allowed is False
        assert count == 50

    def test_over_limit_is_blocked(self, mock_redis):
        from core.rate_limiter import check_rate_limit, _make_key
        key = _make_key("owner/repo")
        mock_redis.set(key, "100")
        allowed, count, limit = check_rate_limit("owner/repo")
        assert allowed is False

    def test_different_repos_have_separate_limits(self, mock_redis):
        from core.rate_limiter import check_rate_limit, _make_key
        key_a = _make_key("owner/repo-a")
        mock_redis.set(key_a, "50")
        # repo-a is blocked
        allowed_a, _, _ = check_rate_limit("owner/repo-a")
        assert allowed_a is False
        # repo-b is still fine
        allowed_b, _, _ = check_rate_limit("owner/repo-b")
        assert allowed_b is True


# ─── increment_rate_limit ─────────────────────────────────────


class TestIncrementRateLimit:

    def test_first_increment_returns_1(self, mock_redis):
        from core.rate_limiter import increment_rate_limit
        count = increment_rate_limit("owner/repo")
        assert count == 1

    def test_second_increment_returns_2(self, mock_redis):
        from core.rate_limiter import increment_rate_limit
        increment_rate_limit("owner/repo")
        count = increment_rate_limit("owner/repo")
        assert count == 2

    def test_sets_expiry_on_first_increment(self, mock_redis):
        from core.rate_limiter import increment_rate_limit, _make_key
        increment_rate_limit("owner/repo")
        key = _make_key("owner/repo")
        # 35 days in seconds
        assert mock_redis._expiry.get(key) == 35 * 24 * 60 * 60

    def test_increment_then_check_shows_correct_count(self, mock_redis):
        from core.rate_limiter import increment_rate_limit, check_rate_limit
        for _ in range(10):
            increment_rate_limit("owner/repo")
        allowed, count, limit = check_rate_limit("owner/repo")
        assert allowed is True
        assert count == 10


# ─── get_usage ────────────────────────────────────────────────


class TestGetUsage:

    def test_fresh_repo_shows_zero(self, mock_redis):
        from core.rate_limiter import get_usage
        usage = get_usage("owner/repo")
        assert usage["used"] == 0
        assert usage["remaining"] == 50
        assert usage["limit"] == 50

    def test_after_increments_shows_correct_usage(self, mock_redis):
        from core.rate_limiter import increment_rate_limit, get_usage
        for _ in range(15):
            increment_rate_limit("owner/repo")
        usage = get_usage("owner/repo")
        assert usage["used"] == 15
        assert usage["remaining"] == 35


# ─── Edge cases ───────────────────────────────────────────────


class TestEdgeCases:

    def test_redis_error_in_check_allows_request(self):
        """If Redis is down, fail open — don't block reviews."""
        from core.rate_limiter import check_rate_limit
        import redis as redis_lib
        with patch("core.rate_limiter._get_redis", side_effect=redis_lib.RedisError("down")):
            allowed, count, limit = check_rate_limit("owner/repo")
        assert allowed is True

    def test_key_format_includes_month(self, mock_redis):
        from core.rate_limiter import _make_key
        from datetime import datetime
        key = _make_key("owner/repo")
        month = datetime.utcnow().strftime("%Y-%m")
        assert f"ratelimit:owner/repo:{month}" == key
