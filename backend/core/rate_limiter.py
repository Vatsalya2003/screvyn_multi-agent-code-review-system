"""
Rate limiter — Redis-based counter per repo per month.

How it works:
    Each repo gets a key like "ratelimit:owner/repo:2026-03".
    Every review increments it. When it hits the limit, we reject.
    The key expires after 35 days so old months clean themselves up.

Why Redis INCR?
    INCR is atomic — even if two webhooks arrive at the exact same
    millisecond, Redis guarantees they get sequential counts.
    No race conditions, no double-counting.
"""

import logging
from datetime import datetime

import redis

from core.config import settings

logger = logging.getLogger(__name__)

# Lazy connection — only created when first needed
_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    """Get or create the Redis connection (singleton)."""
    global _redis_client
    if _redis_client is None:
        if not settings.redis_url:
            raise RuntimeError("REDIS_URL not configured")
        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _redis_client


def _make_key(repo: str) -> str:
    """Build the rate limit key for this repo + month."""
    month = datetime.utcnow().strftime("%Y-%m")
    return f"ratelimit:{repo}:{month}"


def check_rate_limit(repo: str) -> tuple[bool, int, int]:
    """
    Check if this repo is under its monthly limit.

    Returns:
        (allowed, current_count, limit)

    Example:
        allowed, count, limit = check_rate_limit("owner/repo")
        if not allowed:
            return 429, f"Rate limited: {count}/{limit}"
    """
    limit = settings.rate_limit_monthly
    try:
        r = _get_redis()
        key = _make_key(repo)
        current = r.get(key)
        count = int(current) if current else 0
        return count < limit, count, limit
    except redis.RedisError as e:
        # If Redis is down, allow the request (fail open)
        logger.error("Redis error in rate limit check: %s", e)
        return True, 0, limit


def increment_rate_limit(repo: str) -> int:
    """
    Increment the counter for this repo. Returns new count.

    Called AFTER successfully enqueuing a review task,
    not before — so failed reviews don't burn the quota.
    """
    try:
        r = _get_redis()
        key = _make_key(repo)

        # INCR is atomic — safe under concurrent access
        new_count = r.incr(key)

        # Set expiry on first increment (35 days covers any month)
        if new_count == 1:
            r.expire(key, 35 * 24 * 60 * 60)

        logger.info("Rate limit for %s: %d/%d", repo, new_count, settings.rate_limit_monthly)
        return new_count
    except redis.RedisError as e:
        logger.error("Redis error incrementing rate limit: %s", e)
        return 0


def get_usage(repo: str) -> dict:
    """Get current usage stats for a repo (used by dashboard)."""
    limit = settings.rate_limit_monthly
    try:
        r = _get_redis()
        key = _make_key(repo)
        current = r.get(key)
        count = int(current) if current else 0
        return {
            "repo": repo,
            "month": datetime.utcnow().strftime("%Y-%m"),
            "used": count,
            "limit": limit,
            "remaining": max(0, limit - count),
        }
    except redis.RedisError as e:
        logger.error("Redis error getting usage: %s", e)
        return {
            "repo": repo,
            "month": datetime.utcnow().strftime("%Y-%m"),
            "used": 0,
            "limit": limit,
            "remaining": limit,
        }


def reset_for_testing(repo: str) -> None:
    """Delete the rate limit key — only for tests."""
    try:
        r = _get_redis()
        key = _make_key(repo)
        r.delete(key)
    except redis.RedisError:
        pass
