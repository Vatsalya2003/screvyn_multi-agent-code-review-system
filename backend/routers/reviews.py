"""
Reviews router — handles code review API endpoints.

This file defines the HTTP interface for code reviews. It receives
requests, validates input, calls the right agent(s), and returns
structured responses.

Why a separate router instead of putting everything in main.py?
  - Organization: as you add more endpoints (webhook, auth, dashboard),
    each gets its own router file. main.py stays clean.
  - Readability: someone looking at your code can see all review-related
    endpoints in one file.
  - Team collaboration: two people can work on different routers without
    merge conflicts.

Current endpoints:
  POST /api/review  →  Submit code for security review

Future endpoints (later phases):
  POST /api/webhook         →  GitHub webhook receiver (Phase 6)
  GET  /api/reviews         →  List past reviews (Phase 7)
  GET  /api/reviews/{id}    →  Get a specific review (Phase 7)
"""

import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.security_agent import analyze_security
from models.review import Review

logger = logging.getLogger(__name__)


# ─── Request/Response Models ─────────────────────────────────
#
# These Pydantic models define the SHAPE of the data going in
# and out of your API. FastAPI uses them for:
#   1. Input validation (reject bad requests with clear errors)
#   2. Documentation (Swagger docs show the expected format)
#   3. Type hints (your IDE can autocomplete fields)
#
# Why separate models instead of reusing Finding/Review?
#   - The API request is different from internal models.
#     The user sends "code" and "language", not a Finding.
#   - This decouples your API contract from your internal models.
#     You can change internal models without breaking the API.
#

class ReviewRequest(BaseModel):
    """What the user sends to POST /api/review."""

    code: str = Field(
        description="Source code to review",
        min_length=1,
        max_length=50000,  # ~50KB max, prevents abuse
        examples=["def get_user(id):\n    return db.execute(f'SELECT * FROM users WHERE id={id}')"],
    )
    language: str = Field(
        default="python",
        description="Programming language of the code",
        examples=["python", "javascript", "java", "swift", "go"],
    )


class ReviewResponse(BaseModel):
    """What the API returns after a review."""

    repo: str
    language: str
    findings: list  # List of Finding dicts
    p0_count: int
    p1_count: int
    p2_count: int
    total_findings: int
    has_critical: bool
    review_duration_seconds: float
    agents_completed: list[str]
    agents_failed: list[str]


# ─── Router ──────────────────────────────────────────────────
#
# APIRouter() groups related endpoints together. It's like a
# mini-app that gets plugged into the main app in main.py.
#
router = APIRouter()


@router.post(
    "/review",
    response_model=ReviewResponse,
    summary="Review code for security issues",
    description=(
        "Submit source code and receive a security review with "
        "findings ranked by severity (P0 critical, P1 high, P2 medium). "
        "Each finding includes the vulnerable code, explanation, and fix."
    ),
)
async def create_review(request: ReviewRequest):
    """
    The main review endpoint.

    Flow:
    1. User sends POST /api/review with {code, language}
    2. FastAPI validates the input (Pydantic checks min_length, etc.)
    3. We call the security agent with the code
    4. Agent calls Gemini, parses JSON, returns Finding objects
    5. We wrap findings in a Review object
    6. FastAPI serializes the Review to JSON and returns it

    Why 'async def' instead of 'def'?
      - FastAPI can handle this endpoint concurrently with others.
      - While Gemini is thinking (~10s), other requests can be served.
      - In Phase 4 with parallel agents, this becomes essential.
      - For now, the actual Gemini call is synchronous (the google
        SDK isn't async), but the endpoint wrapper is ready.

    Why no authentication yet?
      - Phase 1-5 focus on getting the core review working.
      - Firebase Auth gets added in Phase 6/7.
      - For now, the API is open — fine for local development.
    """
    logger.info(
        "Review requested: language=%s, code_length=%d chars",
        request.language,
        len(request.code),
    )

    start_time = time.time()
    agents_completed = []
    agents_failed = []

    # ── Run the security agent ───────────────────────────────
    #
    # In Phase 4, this section will run 4 agents in parallel
    # using LangGraph. For now, we just run security.
    #
    try:
        findings = analyze_security(
            code=request.code,
            language=request.language,
        )
        agents_completed.append("security")
    except Exception as e:
        logger.error("Security agent error: %s", str(e)[:200])
        findings = []
        agents_failed.append("security")

    elapsed = time.time() - start_time

    # ── Build the Review object ──────────────────────────────
    review = Review(
        repo="paste/anonymous",  # No repo for paste reviews
        language=request.language,
        findings=findings,
        review_duration_seconds=round(elapsed, 2),
        agents_completed=agents_completed,
        agents_failed=agents_failed,
    )
    review.sort_findings()

    logger.info(
        "Review complete in %.1fs: %d findings (P0=%d, P1=%d, P2=%d)",
        elapsed,
        review.total_findings,
        review.p0_count,
        review.p1_count,
        review.p2_count,
    )

    return review